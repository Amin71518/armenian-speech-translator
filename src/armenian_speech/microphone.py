"""Microphone capture, VAD phrases, or opt-in local live Armenian -> English."""

import argparse
import json
import math
import signal
import sys
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from time import perf_counter

import sounddevice as sd


@dataclass(frozen=True)
class AudioBlock:
    pcm: bytes
    frames: int
    start_frame: int
    adc_time: float
    callback_time: float
    received_monotonic: float = 0.0
    capture_epoch: int = 0


@dataclass
class CaptureStats:
    blocks: int = 0
    frames: int = 0
    input_overflow_events: int = 0
    input_underflow_events: int = 0
    status_events: int = 0
    queue_dropped_blocks: int = 0
    queue_dropped_frames: int = 0
    adc_zero_blocks: int = 0
    adc_nonmonotonic_events: int = 0
    adc_after_callback_events: int = 0
    timestamp_nonfinite_blocks: int = 0


class MicrophoneCapture:
    """A bounded raw-block buffer; on full, discard the incoming block and count it.

    PortAudio's input buffer is only valid during its callback, so copy it before
    returning. No printing, file access, model work or waiting for queue space.
    Only the callback writes counters; read final counters after closing the stream.
    """

    def __init__(self, buffer_blocks: int = 32) -> None:
        if buffer_blocks < 1:
            raise ValueError("buffer_blocks must be positive")
        self.blocks: Queue[AudioBlock] = Queue(maxsize=buffer_blocks)
        self.stats = CaptureStats()
        self.error: Exception | None = None
        self._previous_adc_time: float | None = None
        self.capture_epoch = 0

    def callback(self, indata, frames: int, time, status) -> None:
        try:
            start_frame = self.stats.frames
            self.stats.frames += frames
            self.stats.blocks += 1
            self.stats.input_overflow_events += bool(status.input_overflow)
            self.stats.input_underflow_events += bool(status.input_underflow)
            self.stats.status_events += bool(status)
            if status.input_overflow or status.input_underflow:
                self.capture_epoch += 1
            block = AudioBlock(
                bytes(indata), frames, start_frame,
                float(time.inputBufferAdcTime), float(time.currentTime),
                perf_counter(), self.capture_epoch,
            )
            self.stats.adc_zero_blocks += block.adc_time == 0.0
            self.stats.timestamp_nonfinite_blocks += not (
                math.isfinite(block.adc_time) and math.isfinite(block.callback_time)
            )
            self.stats.adc_after_callback_events += block.adc_time > block.callback_time + 0.001
            if self._previous_adc_time is not None:
                self.stats.adc_nonmonotonic_events += block.adc_time <= self._previous_adc_time
            self._previous_adc_time = block.adc_time
            try:
                self.blocks.put_nowait(block)
            except Full:
                self.stats.queue_dropped_blocks += 1
                self.stats.queue_dropped_frames += frames
        except Exception as error:
            # PortAudio does not propagate callback exceptions to the main thread.
            self.error = error
            raise sd.CallbackAbort from error


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return seconds


def probability(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0 < number < 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1, exclusive")
    return number


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--list-devices", action="store_true", help="List input devices and exit")
    cli.add_argument("--device", type=int, help="Explicit input device index from --list-devices")
    cli.add_argument("--sample-rate", type=positive_int, default=16000)
    cli.add_argument("--channels", type=positive_int, default=1)
    cli.add_argument("--duration", type=positive_seconds, help="Seconds; default: until Ctrl+C")
    mode = cli.add_mutually_exclusive_group()
    mode.add_argument("--vad", action="store_true", help="Detect speech phrases; no transcription")
    mode.add_argument("--live", action="store_true", help="VAD -> FastConformer -> NLLB -> HY/EN")
    cli.add_argument("--vad-model", type=Path, default=Path(".cache/models/silero"))
    cli.add_argument("--cache-dir", type=Path, default=Path(".cache/models"))
    cli.add_argument("--asr-model", type=Path, help="Prepared FastConformer directory")
    cli.add_argument("--threads", type=positive_int, default=4)
    cli.add_argument("--queue-size", type=positive_int, default=2,
                     help="Waiting phrases; drop incoming on full")
    cli.add_argument("--shutdown-timeout", type=positive_seconds, default=15.0)
    cli.add_argument("--diagnostics", action="store_true",
                     help="Show live status/timings and JSON summary")
    cli.add_argument("--allow-asr-fragments", action="store_true",
                     help="Allow isolated letters/punctuation in live ASR output and translation")
    cli.add_argument("--vad-threshold", type=probability, default=0.65)
    cli.add_argument("--vad-continue-threshold", type=probability, default=0.50)
    cli.add_argument("--min-speech-ms", type=positive_int, default=300)
    cli.add_argument("--vad-confirm-ms", type=positive_int, default=160)
    cli.add_argument("--segment-target-s", type=positive_seconds, default=3.5,
                     help="Start preferring short pauses after this much phrase audio")
    cli.add_argument("--segment-max-s", type=positive_seconds, default=6.0,
                     help="Hard audio limit including padding; live supports at most 12 s")
    cli.add_argument("--segment-pause-ms", type=positive_int, default=256,
                     help="Pause to end a phrase after the target duration")
    cli.add_argument("--min-rms-db", type=float,
                     help="Optional minimum RMS in dBFS; higher values reject quieter sound")
    return cli


def list_devices() -> None:
    hostapis = sd.query_hostapis()
    default_input = sd.default.device[0]
    count = 0
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] < 1:
            continue
        count += 1
        marker = " (default input)" if index == default_input else ""
        print(
            f"{index}: {device['name']} | {hostapis[device['hostapi']]['name']} | "
            f"max_channels={device['max_input_channels']} "
            f"default_rate={device['default_samplerate']:g} Hz{marker}",
            flush=True,
        )
    if not count:
        raise RuntimeError("No input devices available. Check Windows microphone access.")


def validate_input(args: argparse.Namespace) -> dict:
    devices = sd.query_devices()
    if args.device < 0 or args.device >= len(devices):
        raise ValueError("Invalid device index. Run with --list-devices.")
    device = devices[args.device]
    if not 1 <= args.channels <= device["max_input_channels"]:
        raise ValueError("Selected device does not support the requested input channel count.")
    sd.check_input_settings(
        device=args.device, samplerate=args.sample_rate, channels=args.channels, dtype="int16",
    )
    return device


def vad_settings(args: argparse.Namespace):
    from armenian_speech.vad import VADConfig

    if args.live and args.segment_max_s > 12:
        raise ValueError("VAD live segment maximum must be <= 12 seconds.")
    return VADConfig(
        start_threshold=args.vad_threshold, continue_threshold=args.vad_continue_threshold,
        min_speech_ms=args.min_speech_ms, confirmation_ms=args.vad_confirm_ms,
        min_rms_db=args.min_rms_db,
        target_segment_s=args.segment_target_s, max_segment_s=args.segment_max_s,
        split_silence_ms=args.segment_pause_ms,
    )


def capture(args: argparse.Namespace, inference=None, stop_requested=None) -> int:
    device = validate_input(args)
    diagnostics = args.diagnostics or not args.live
    vad = None
    if args.vad or args.live:
        from armenian_speech.live_vad import LiveVAD
        from armenian_speech.vad import SileroVAD

        print("Loading prepared Silero VAD on CPU...", flush=True)
        config = vad_settings(args)
        vad = LiveVAD(SileroVAD(args.vad_model), args.sample_rate, args.channels, config)
    audio = MicrophoneCapture()
    stream = sd.RawInputStream(
        device=args.device, samplerate=args.sample_rate, channels=args.channels,
        dtype="int16", blocksize=0, callback=audio.callback,
    )
    started = perf_counter()
    interrupted = False
    stopped_by = "error"
    processed_frames = 0
    peak = 0.0
    interval_peak = 0.0
    last_adc_time = None
    last_callback_time = None
    first_adc_time = None
    try:
        with stream:
            hostapi = sd.query_hostapis(device["hostapi"])["name"]
            status = (
                "Live Armenian -> English enabled."
                if inference is not None else "Audio monitoring; no files or transcripts saved."
            )
            print(
                f"Input {args.device}: {device['name']} | {hostapi}\n"
                f"Stream: {stream.samplerate:g} Hz, channels={stream.channels}, "
                f"dtype={stream.dtype}, input_latency={stream.latency:.4f}s, blocksize=auto\n"
                f"Microphone active. {status}\n"
                "Press Ctrl+C to stop.",
                flush=True,
            )
            if vad is not None:
                if stream.samplerate != args.sample_rate or stream.channels != args.channels:
                    raise RuntimeError("Opened stream settings differ from VAD input settings.")
                if diagnostics:
                    print("VAD enabled: " + json.dumps(asdict(vad.config)), flush=True)
                if inference is None:
                    print("Phrase times are VAD estimates; use --live for HY/EN.", flush=True)
            started = perf_counter()
            next_status = started + 1.0
            last_received = started
            while args.duration is None or perf_counter() - started < args.duration:
                if stop_requested is not None and stop_requested():
                    interrupted = True
                    stopped_by = "ctrl_c"
                    break
                if inference is not None:
                    inference.poll()
                if audio.error is not None:
                    raise RuntimeError(f"Audio callback failed: {audio.error}") from audio.error
                if not stream.active:
                    raise RuntimeError("Input stream stopped unexpectedly.")
                timeout = 0.1
                if args.duration is not None:
                    timeout = min(timeout, max(0.0, args.duration - (perf_counter() - started)))
                try:
                    block = audio.blocks.get(timeout=timeout)
                except Empty:
                    if perf_counter() - last_received > max(2.0, 2 * stream.latency):
                        raise RuntimeError(
                            "No audio blocks received for over two seconds."
                        ) from None
                else:
                    last_received = perf_counter()
                    processed_frames += block.frames
                    samples = array("h", block.pcm)
                    if samples:
                        block_peak = max(abs(sample) for sample in samples) / 32768
                        peak = max(peak, block_peak)
                        interval_peak = max(interval_peak, block_peak)
                    if first_adc_time is None:
                        first_adc_time = block.adc_time
                    last_adc_time = block.adc_time
                    last_callback_time = block.callback_time
                    if vad is not None:
                        print_vad_segments(vad.push(block), inference)
                if diagnostics and perf_counter() >= next_status:
                    vad_status = (
                        f" p_speech={vad.last_probability:.3f} "
                        f"rms_dbfs={vad.last_rms_db:.1f} energy_pass={vad.last_energy_pass} "
                        f"speech_candidate={vad.segmenter.start is not None}"
                        if vad is not None else ""
                    )
                    if inference is not None:
                        stats = inference.stats
                        vad_status += (
                            f" unfinished_phrases={stats['accepted'] - stats['completed']} "
                            f"dropped_phrases={stats['dropped_full']}"
                        )
                    print(
                        f"audio={audio.stats.frames / stream.samplerate:.2f}s "
                        f"blocks={audio.stats.blocks} "
                        f"peak_1s={interval_peak:.3f} peak_max={peak:.3f} "
                        f"overflows={audio.stats.input_overflow_events} "
                        f"queue_dropped_frames={audio.stats.queue_dropped_frames}{vad_status}",
                        flush=True,
                    )
                    interval_peak = 0.0
                    next_status = perf_counter() + 1.0
            if audio.stats.frames == 0:
                raise RuntimeError("Capture finished without receiving audio frames.")
            if not interrupted:
                stopped_by = "duration"
    except KeyboardInterrupt:
        interrupted = True
        stopped_by = "ctrl_c"
    finally:
        # close() is idempotent and also covers failure while entering the context.
        stream.close()
        finalization_error = None
        if vad is not None and stopped_by != "error":
            try:
                while not audio.blocks.empty():
                    block = audio.blocks.get_nowait()
                    processed_frames += block.frames
                    if first_adc_time is None:
                        first_adc_time = block.adc_time
                    last_adc_time = block.adc_time
                    last_callback_time = block.callback_time
                    print_vad_segments(vad.push(block), inference)
                print_vad_segments(vad.finish(
                    "shutdown" if interrupted else "duration",
                    final_input_frame=audio.stats.frames, final_capture_epoch=audio.capture_epoch,
                ), inference)
            except Exception as error:
                finalization_error = error
                stopped_by = "error"
        if inference is not None:
            print("Microphone closed; finishing accepted phrases...", flush=True)
            try:
                inference.close(drain=stopped_by != "error")
            except (Exception, KeyboardInterrupt) as error:
                finalization_error = error
                stopped_by = "error"
        if stop_requested is not None and stop_requested() and stopped_by != "error":
            interrupted = True
            stopped_by = "ctrl_c"
        summary = {
            **asdict(audio.stats),
            "processed_frames": processed_frames,
            "pending_blocks": audio.blocks.qsize(),
            "pending_frames": (
                audio.stats.frames - processed_frames - audio.stats.queue_dropped_frames
            ),
            "sample_rate": stream.samplerate,
            "channels": stream.channels,
            "dtype": str(stream.dtype),
            "audio_s": audio.stats.frames / stream.samplerate,
            "wall_s": perf_counter() - started,
            "peak": peak,
            "first_adc_time": first_adc_time,
            "last_adc_time": last_adc_time,
            "last_callback_time": last_callback_time,
            "timestamp_clock": "PortAudio stream clock; not perf_counter or speech boundaries",
            "driver_lost_frames": None,
            "stopped_by": stopped_by,
            "stream_closed": stream.closed,
        }
        if vad is not None:
            summary["vad"] = vad.stats
            summary["vad_audio_discarded_on_error"] = stopped_by == "error"
        if inference is not None:
            summary["inference"] = inference.summary()
        if diagnostics or stopped_by == "error":
            print("Capture summary: " + json.dumps(summary), flush=True)
        if finalization_error is not None:
            detail = str(finalization_error) or type(finalization_error).__name__
            raise RuntimeError(
                f"Live finalization failed: {detail}"
            ) from finalization_error
    return 130 if interrupted else 0


def print_vad_segments(segments, inference=None) -> None:
    for segment in segments:
        if inference is None:
            print("VAD phrase: " + json.dumps(segment.metadata()), flush=True)
        else:
            inference.submit(segment)


def run_live(args: argparse.Namespace) -> int:
    from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig

    validate_input(args)
    vad_settings(args)  # Reject contradictory VAD options before loading ASR/MT.
    worker = InferenceWorker(
        WorkerConfig(
            args.cache_dir, args.asr_model, args.threads,
            filter_asr_fragments=not args.allow_asr_fragments,
        ),
        capacity=args.queue_size, shutdown_timeout=args.shutdown_timeout,
        diagnostics=args.diagnostics,
    )
    stop = {"requested": False, "count": 0, "ready": False}

    def request_stop(signum, frame):
        stop["count"] += 1
        if not stop["ready"] or stop["count"] > 1:
            raise KeyboardInterrupt
        stop["requested"] = True

    previous_handler = signal.signal(signal.SIGINT, request_stop)
    try:
        print("Loading local FastConformer INT8 and NLLB greedy in inference worker...", flush=True)
        worker.start()
        stop["ready"] = True
        status = "Inference worker ready"
        if args.diagnostics:
            status += ": " + json.dumps(worker.metadata)
        print(status, flush=True)
        return capture(args, worker, stop_requested=lambda: stop["requested"])
    finally:
        try:
            worker.close(drain=False)
        finally:
            signal.signal(signal.SIGINT, previous_handler)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    cli = parser()
    args = cli.parse_args(argv)
    if not args.list_devices and args.device is None:
        cli.error("capture requires --device INDEX; use --list-devices first")
    try:
        if args.list_devices:
            list_devices()
            return 0
        if args.live:
            return run_live(args)
        return capture(args)
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr, flush=True)
        return 130
    except (OSError, ValueError, RuntimeError, sd.PortAudioError) as error:
        print(f"Error: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

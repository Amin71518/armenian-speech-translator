"""Windows WASAPI loopback monitoring or local live Armenian -> English."""

import argparse
import json
import signal
import sys
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from time import perf_counter

from armenian_speech.microphone import (
    AudioBlock,
    positive_int,
    positive_seconds,
    probability,
    vad_settings,
)


@dataclass
class LoopbackStats:
    blocks: int = 0
    frames: int = 0
    status_events: int = 0
    input_overflows: int = 0
    queue_dropped_blocks: int = 0
    queue_dropped_frames: int = 0


class LoopbackCapture:
    """Copy callback PCM into a bounded queue; no model work, printing or file I/O."""

    def __init__(self, backend, channels: int, capacity: int = 32):
        self.backend = backend
        self.channels = channels
        self.blocks: Queue[AudioBlock] = Queue(maxsize=capacity)
        self.stats = LoopbackStats()
        self.epoch = 0
        self.error = None

    def callback(self, data, frames, timing, status):
        try:
            if data is None or len(data) != frames * self.channels * 2:
                raise ValueError("Loopback PCM length does not match frame count.")
            start = self.stats.frames
            self.stats.frames += frames
            self.stats.blocks += 1
            self.stats.status_events += bool(status)
            self.stats.input_overflows += bool(status & self.backend.paInputOverflow)
            self.epoch += bool(status)
            block = AudioBlock(bytes(data), frames, start, timing["input_buffer_adc_time"],
                               timing["current_time"], perf_counter(), self.epoch)
            try:
                self.blocks.put_nowait(block)
            except Full:
                self.stats.queue_dropped_blocks += 1
                self.stats.queue_dropped_frames += frames
            return None, self.backend.paContinue
        except Exception as error:
            self.error = error
            return None, self.backend.paAbort


def select_device(manager, index):
    device = manager.get_device_info_by_index(index)
    if not device.get("isLoopbackDevice") or device["maxInputChannels"] < 1:
        raise ValueError("Choose a loopback ID from --list-devices, not a microphone/output ID.")
    return device


def capture(manager, backend, args, stopped, inference=None):
    device = select_device(manager, args.device)
    rate, channels = int(device["defaultSampleRate"]), int(device["maxInputChannels"])
    source = LoopbackCapture(backend, channels)
    stream = None
    processed = 0
    peak = interval_peak = 0.0
    started = perf_counter()
    outcome = "error"
    live = inference is not None
    diagnostics = not live or args.diagnostics
    vad = None
    if live:
        from armenian_speech.loopback_vad import LoopbackVAD
        from armenian_speech.vad import SileroVAD

        vad = LoopbackVAD(SileroVAD(args.vad_model), rate, channels, started, vad_settings(args))

    def submit(segments):
        for segment in segments:
            inference.submit(segment)

    def consume(block):
        nonlocal processed, peak, interval_peak
        samples = array("h", block.pcm)
        value = max((abs(x) for x in samples), default=0) / 32768
        processed += block.frames
        peak = max(peak, value)
        interval_peak = max(interval_peak, value)
        if vad is not None:
            submit(vad.push(block))

    try:
        stream = manager.open(
            format=backend.paInt16, channels=channels, rate=rate, input=True,
            input_device_index=args.device, frames_per_buffer=args.block_frames,
            stream_callback=source.callback, start=False,
        )
        started = perf_counter()
        if vad is not None:
            vad.started = started
        stream.start_stream()
        next_status = started + 1
        print(f"System Audio {args.device}: {device['name']}\n"
              f"Stream: PCM16 {rate} Hz, channels={channels}, "
              f"input_latency={stream.get_input_latency():.4f}s\n"
              + ("System Audio live active. HY/EN will appear together. Press Ctrl+C to stop."
                 if live else "Monitoring only; no files, VAD or models. Press Ctrl+C to stop."),
              flush=True)
        while args.duration is None or perf_counter() - started < args.duration:
            if stopped():
                outcome = "ctrl_c"
                break
            if inference is not None:
                inference.poll()
            if source.error:
                raise RuntimeError(f"Loopback callback failed: {source.error}")
            if not stream.is_active():
                raise RuntimeError("Loopback stream stopped unexpectedly; check the output device.")
            try:
                consume(source.blocks.get(timeout=0.05))
            except Empty:
                if vad is not None:
                    final_frame, epoch = source.stats.frames, source.epoch
                    if final_frame == processed + source.stats.queue_dropped_frames:
                        submit(vad.idle(perf_counter(), final_frame, epoch))
            if diagnostics and perf_counter() >= next_status:
                state = "receiving" if source.stats.blocks else "waiting for playback"
                print(f"audio={source.stats.frames / rate:.2f}s peak_1s={interval_peak:.3f} "
                      f"status_events={source.stats.status_events} "
                      f"queue_dropped_frames={source.stats.queue_dropped_frames} {state}",
                      flush=True)
                interval_peak = 0.0
                next_status = perf_counter() + 1
        else:
            outcome = "duration"
        if source.error:
            raise RuntimeError(f"Loopback callback failed: {source.error}")
    except BaseException:
        outcome = "error"
        raise
    finally:
        if stream is not None:
            stream.close()
        final_error = None
        try:
            if outcome != "error":
                while not source.blocks.empty():
                    consume(source.blocks.get_nowait())
                if vad is not None:
                    submit(vad.finish("shutdown" if outcome == "ctrl_c" else "duration",
                                      source.stats.frames, source.epoch))
            if inference is not None:
                print("System Audio closed; finishing accepted phrases...", flush=True)
                inference.close(drain=outcome != "error")
        except (Exception, KeyboardInterrupt) as error:
            final_error = error
            outcome = "error"
        if stopped() and outcome != "error":
            outcome = "ctrl_c"
        summary = {
            **asdict(source.stats), "processed_frames": processed,
            "pending_frames": source.stats.frames - processed - source.stats.queue_dropped_frames,
            "sample_rate": rate, "channels": channels, "dtype": "int16",
            "audio_s": source.stats.frames / rate, "wall_s": perf_counter() - started,
            "peak": peak, "stopped_by": outcome, "stream_closed": True,
            "driver_lost_frames": None, "clock_accuracy": "unvalidated",
        }
        if vad is not None:
            summary["vad"] = vad.stats
            summary["inference"] = inference.summary()
        if diagnostics or getattr(args, "speaker_diagnostics", False) or outcome == "error":
            print("Capture summary: " + json.dumps(summary), flush=True)
        if final_error is not None:
            raise RuntimeError(f"System Audio finalization failed: {final_error}") from final_error
    return 130 if outcome == "ctrl_c" else 0


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--list-devices", action="store_true")
    cli.add_argument("--device", type=int, help="Loopback ID from this module's device list")
    cli.add_argument("--duration", type=positive_seconds)
    cli.add_argument("--block-frames", type=positive_int, default=1024)
    cli.add_argument("--live", action="store_true",
                     help="VAD -> FastConformer -> NLLB -> System HY/EN")
    cli.add_argument("--diagnostics", action="store_true")
    cli.add_argument("--diarize", action="store_true",
                     help="Experimental session speaker IDs for System audio (requires --live)")
    cli.add_argument("--speaker-diagnostics", action="store_true",
                     help="Per-cell speaker decisions and final health summary; requires --diarize")
    cli.add_argument("--experimental-speaker-matching", action="store_true",
                     help="Trial short enrollment/anchored halves; known false-ID/overlap risks")
    cli.add_argument("--speaker-threshold", type=probability, default=0.47)
    cli.add_argument("--speaker-margin", type=probability, default=0.08)
    cli.add_argument("--max-speakers", type=positive_int, default=8)
    cli.add_argument("--cache-dir", type=Path, default=Path(".cache/models"))
    cli.add_argument("--asr-model", type=Path)
    cli.add_argument("--vad-model", type=Path, default=Path(".cache/models/silero"))
    cli.add_argument("--threads", type=positive_int, default=4)
    cli.add_argument("--queue-size", type=positive_int, default=2)
    cli.add_argument("--shutdown-timeout", type=positive_seconds, default=15.0)
    cli.add_argument("--allow-asr-fragments", action="store_true")
    cli.add_argument("--vad-threshold", type=probability, default=0.65)
    cli.add_argument("--vad-continue-threshold", type=probability, default=0.50)
    cli.add_argument("--min-speech-ms", type=positive_int, default=300)
    cli.add_argument("--vad-confirm-ms", type=positive_int, default=160)
    cli.add_argument("--min-rms-db", type=float)
    cli.add_argument("--segment-target-s", type=positive_seconds, default=3.5)
    cli.add_argument("--segment-max-s", type=positive_seconds, default=6.0)
    cli.add_argument("--segment-pause-ms", type=positive_int, default=256)
    return cli


def main(argv=None):
    for target in (sys.stdout, sys.stderr):
        if hasattr(target, "reconfigure"):
            target.reconfigure(encoding="utf-8")
    cli = parser()
    args = cli.parse_args(argv)
    if args.speaker_diagnostics and not args.diarize:
        cli.error("--speaker-diagnostics requires --diarize")
    if args.experimental_speaker_matching and not args.diarize:
        cli.error("--experimental-speaker-matching requires --diarize")
    if args.diarize and not args.live:
        cli.error("--diarize requires --live")
    if not args.list_devices and args.device is None:
        cli.error("Use --device LOOPBACK_ID or --list-devices")
    requested = {"stop": False, "ready": not args.live}
    worker = None

    def stop(signum, frame):
        if requested["stop"] or not requested["ready"]:
            raise KeyboardInterrupt
        requested["stop"] = True

    previous = signal.signal(signal.SIGINT, stop)
    try:
        import pyaudiowpatch as backend

        with backend.PyAudio() as manager:
            if args.list_devices:
                devices = list(manager.get_loopback_device_info_generator())
                for device in devices:
                    print(f"{device['index']}: {device['name']} | "
                          f"channels={device['maxInputChannels']} "
                          f"default_rate={device['defaultSampleRate']:g} Hz", flush=True)
                if not devices:
                    raise RuntimeError("No WASAPI loopback endpoints available.")
                return 0
            if args.live:
                from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig

                device = select_device(manager, args.device)
                if device["maxInputChannels"] not in (1, 2):
                    raise ValueError("Live System Audio supports mono/stereo endpoints only.")
                vad_settings(args)
                worker = InferenceWorker(WorkerConfig(
                    args.cache_dir, args.asr_model, args.threads,
                    filter_asr_fragments=not args.allow_asr_fragments,
                    diarize_system=args.diarize, speaker_threshold=args.speaker_threshold,
                    speaker_margin=args.speaker_margin, max_speakers=args.max_speakers,
                    speaker_diagnostics=args.speaker_diagnostics,
                    experimental_speaker_matching=args.experimental_speaker_matching,
                ), capacity=args.queue_size, shutdown_timeout=args.shutdown_timeout,
                    diagnostics=args.diagnostics, speaker="System")
                print("Loading local FastConformer INT8 and NLLB greedy...", flush=True)
                worker.start()
                requested["ready"] = True
                print("Inference worker ready", flush=True)
            return capture(manager, backend, args, lambda: requested["stop"], worker)
    except KeyboardInterrupt:
        return 130
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        try:
            if worker is not None:
                worker.close(drain=False)
        finally:
            signal.signal(signal.SIGINT, previous)


if __name__ == "__main__":
    raise SystemExit(main())

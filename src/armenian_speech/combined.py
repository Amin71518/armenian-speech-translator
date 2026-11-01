"""Concurrent microphone and WASAPI loopback, independent VADs, one fair ASR/MT worker."""

import json
import signal
import sys
from dataclasses import asdict, replace
from queue import Empty
from time import perf_counter, sleep
from types import SimpleNamespace

import sounddevice as sd

from armenian_speech.fair_queue import FairQueue
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.live_vad import LiveVAD
from armenian_speech.loopback_vad import LoopbackVAD
from armenian_speech.microphone import (
    MicrophoneCapture,
    list_devices,
    positive_int,
    vad_settings,
    validate_input,
)
from armenian_speech.system_audio import LoopbackCapture, parser, select_device
from armenian_speech.vad import SileroVAD


def run(manager, backend, args, worker, stopped):
    device = select_device(manager, args.device)
    rate, channels = int(device["defaultSampleRate"]), int(device["maxInputChannels"])
    captures = {"Me": MicrophoneCapture(), "System": LoopbackCapture(backend, channels)}
    config = vad_settings(args)
    mic_vad = LiveVAD(SileroVAD(args.vad_model), args.microphone_rate,
                      args.microphone_channels, config)
    system_vad = LoopbackVAD(SileroVAD(args.vad_model), rate, channels, 0, config)
    scheduler = FairQueue(worker, args.pending_per_source)
    processed = {"Me": 0, "System": 0}
    streams = {}
    closed = {"Me": True, "System": True}
    started = perf_counter()
    mic_offset = None
    last_mic = started
    outcome, failure = "error", None

    def offer(label, segments):
        for segment in segments:
            scheduler.offer(label, segment)

    def consume(label, block):
        nonlocal mic_offset, last_mic
        processed[label] += block.frames
        if label == "Me":
            last_mic = perf_counter()
            if mic_offset is None:
                mic_offset = max(0, block.received_monotonic - block.frames / args.microphone_rate
                                 - started) - block.start_frame / args.microphone_rate
            offer(label, [replace(s, timeline_origin_s=s.origin_s + mic_offset)
                          for s in mic_vad.push(block)])
        else:
            offer(label, system_vad.push(block))

    def take_round():
        any_data = False
        for label, source in captures.items():
            try:
                block = source.blocks.get_nowait()
            except Empty:
                continue
            consume(label, block)
            any_data = True
        scheduler.dispatch()
        return any_data

    try:
        streams["Me"] = sd.RawInputStream(
            device=args.microphone_device, samplerate=args.microphone_rate,
            channels=args.microphone_channels, dtype="int16", blocksize=0,
            callback=captures["Me"].callback,
        )
        closed["Me"] = False
        streams["System"] = manager.open(
            format=backend.paInt16, channels=channels, rate=rate, input=True,
            input_device_index=args.device, frames_per_buffer=args.block_frames,
            stream_callback=captures["System"].callback, start=False,
        )
        closed["System"] = False
        started = last_mic = perf_counter()
        system_vad.started = started
        streams["Me"].start()
        streams["System"].start_stream()
        print("Combined live active. Sources: Me + System. Press Ctrl+C to stop.", flush=True)
        next_status = started + 1
        while args.duration is None or perf_counter() - started < args.duration:
            if stopped():
                outcome = "ctrl_c"
                break
            for label, source in captures.items():
                if source.error is not None:
                    raise RuntimeError(f"{label} callback failed: {source.error}")
            if not streams["Me"].active or not streams["System"].is_active():
                raise RuntimeError("An input stream stopped; both sources will close.")
            data = take_round()
            source = captures["System"]
            frame, epoch = source.stats.frames, source.epoch
            if frame == processed["System"] + source.stats.queue_dropped_frames:
                offer("System", system_vad.idle(perf_counter(), frame, epoch))
            if perf_counter() - last_mic > max(2.0, 2 * streams["Me"].latency):
                raise RuntimeError("Microphone delivered no audio for over two seconds.")
            if args.diagnostics and perf_counter() >= next_status:
                print("Sources: " + json.dumps({label: {
                    "frames": source.stats.frames,
                    "raw_dropped_frames": source.stats.queue_dropped_frames,
                    "pending_phrases": len(scheduler.queues[label]),
                } for label, source in captures.items()}), flush=True)
                next_status = perf_counter() + 1
            if not data:
                sleep(0.005)
        else:
            outcome = "duration"
    except BaseException as error:
        failure = error
    finally:
        for label, stream in streams.items():
            try:
                stream.close()
                closed[label] = True
            except BaseException as error:
                failure = failure or error
        for label, source in captures.items():
            if source.error is not None:
                failure = failure or RuntimeError(f"{label} callback failed: {source.error}")
        deadline = perf_counter() + args.shutdown_timeout
        try:
            if failure is None:
                while take_round():
                    if perf_counter() >= deadline:
                        raise RuntimeError("Combined shutdown timed out while draining raw audio.")
                mic = captures["Me"]
                offer("Me", [replace(s, timeline_origin_s=s.origin_s + (mic_offset or 0))
                             for s in mic_vad.finish(
                                 "shutdown" if outcome == "ctrl_c" else "duration",
                                 final_input_frame=mic.stats.frames,
                                 final_capture_epoch=mic.capture_epoch,
                             )])
                source = captures["System"]
                offer("System", system_vad.finish(
                    "shutdown" if outcome == "ctrl_c" else "duration",
                    source.stats.frames, source.epoch,
                ))
                while scheduler.pending:
                    scheduler.dispatch()
                    if perf_counter() >= deadline:
                        raise RuntimeError("Combined shutdown timed out with pending phrases.")
                    sleep(0.005)
                worker.shutdown_timeout = max(0.001, deadline - perf_counter())
                print("Both sources closed; finishing accepted phrases...", flush=True)
                worker.close()
        except BaseException as error:
            failure = failure or error
        finally:
            scheduler.cancel()
            try:
                worker.close(drain=False)
            except BaseException as error:
                failure = failure or error
        if stopped() and failure is None:
            outcome = "ctrl_c"
        if failure is not None:
            outcome = "error"
        if args.diagnostics or getattr(args, "speaker_diagnostics", False) or failure is not None:
            print("Capture summary: " + json.dumps({
                "stopped_by": outcome, "stream_closed": all(closed.values()),
                "sources": {label: {**asdict(source.stats), "processed_frames": processed[label],
                                    "pending_frames": source.stats.frames - processed[label]
                                    - source.stats.queue_dropped_frames,
                                    "stream_closed": closed[label]}
                            for label, source in captures.items()},
                "scheduler": scheduler.summary(), "inference": worker.summary(),
                "vad": {"Me": mic_vad.stats, "System": system_vad.stats},
                "wall_s": perf_counter() - started, "clock_accuracy": "unvalidated",
            }), flush=True)
    if failure is not None:
        raise RuntimeError(f"Combined capture failed: {failure}") from failure
    return 130 if outcome == "ctrl_c" else 0


def argument_parser():
    cli = parser()
    cli.description = __doc__
    cli.add_argument("--microphone-device", type=int, help="sounddevice input ID")
    cli.add_argument("--microphone-rate", type=positive_int, default=48000)
    cli.add_argument("--microphone-channels", type=positive_int, default=1)
    cli.add_argument("--pending-per-source", type=positive_int, default=2)
    cli.set_defaults(live=True)
    return cli


def main(argv=None):
    cli = argument_parser()
    args = cli.parse_args(argv)
    if args.speaker_diagnostics and not args.diarize:
        cli.error("--speaker-diagnostics requires --diarize")
    if args.experimental_speaker_matching and not args.diarize:
        cli.error("--experimental-speaker-matching requires --diarize")
    if not args.list_devices and (args.device is None or args.microphone_device is None):
        cli.error("Use --microphone-device INPUT_ID and --device LOOPBACK_ID")
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8")
    state = {"stop": False, "ready": False}
    worker = None

    def stop(signum, frame):
        if state["stop"] or not state["ready"]:
            raise KeyboardInterrupt
        state["stop"] = True

    previous = signal.signal(signal.SIGINT, stop)
    try:
        import pyaudiowpatch as backend

        with backend.PyAudio() as manager:
            if args.list_devices:
                print("Microphone IDs (sounddevice):", flush=True)
                list_devices()
                print("System loopback IDs (PyAudioWPatch):", flush=True)
                for device in manager.get_loopback_device_info_generator():
                    print(f"{device['index']}: {device['name']}", flush=True)
                return 0
            validate_input(SimpleNamespace(device=args.microphone_device,
                                            sample_rate=args.microphone_rate,
                                            channels=args.microphone_channels))
            device = select_device(manager, args.device)
            if args.microphone_channels not in (1, 2) or device["maxInputChannels"] not in (1, 2):
                raise ValueError("Combined VAD supports mono/stereo inputs only.")
            vad_settings(args)
            worker = InferenceWorker(WorkerConfig(
                args.cache_dir, args.asr_model, args.threads,
                filter_asr_fragments=not args.allow_asr_fragments,
                diarize_system=args.diarize, speaker_threshold=args.speaker_threshold,
                speaker_margin=args.speaker_margin, max_speakers=args.max_speakers,
                speaker_diagnostics=args.speaker_diagnostics,
                experimental_speaker_matching=args.experimental_speaker_matching,
            ), capacity=args.queue_size, shutdown_timeout=args.shutdown_timeout,
                diagnostics=args.diagnostics)
            print("Loading one local FastConformer/NLLB worker for both sources...", flush=True)
            worker.start()
            state["ready"] = True
            return run(manager, backend, args, worker, lambda: state["stop"])
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

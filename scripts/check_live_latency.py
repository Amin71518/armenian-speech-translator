"""Annotated nominal-rate replay with optional concurrent physical mic health check.

This does not turn file delivery into a physical microphone speech-end measurement.
No new audio/transcript is persisted. Unreviewed annotations cannot certify latency.
"""

import argparse
import hashlib
import json
import platform
import sys
import wave
from dataclasses import asdict
from pathlib import Path
from queue import Empty
from time import perf_counter, sleep

import psutil
import sounddevice as sd

from armenian_speech.cli import positive_int, read_manifest
from armenian_speech.latency import clock_sample, evaluate_cases, numeric_result
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.live_vad import LiveVAD
from armenian_speech.microphone import AudioBlock, MicrophoneCapture
from armenian_speech.vad import SileroVAD, VADConfig


def load_fixture(manifest: Path, annotations: Path, repeat: int):
    annotation = json.loads(annotations.read_text(encoding="utf-8"))
    labels = {row["sample"]: row for row in annotation["recordings"]}
    rows = read_manifest(manifest)
    pieces, references = [b"\x00\x00" * 16000], []
    cursor = 16000
    for pass_index in range(repeat):
        for row in rows:
            name = row["path"].name
            if name not in labels:
                continue
            label = labels[name]
            digest = hashlib.sha256(row["path"].read_bytes()).hexdigest()
            if digest != row["sha256"] or digest != label["sha256"]:
                raise ValueError(f"Annotation/WAV checksum mismatch: {name}")
            with wave.open(str(row["path"]), "rb") as audio:
                if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (
                    16000, 1, 2,
                ):
                    raise ValueError("Fixture requires mono PCM16 16 kHz.")
                pcm = audio.readframes(audio.getnframes())
            low, high = label["speech_end_interval_s"]
            if not 0 < low <= high <= len(pcm) / 32000:
                raise ValueError(f"Invalid annotation interval: {name}")
            references.append({
                "id": f"{pass_index + 1}:{name}",
                "end_interval_s": [cursor / 16000 + low, cursor / 16000 + high],
            })
            pieces.extend((pcm, b"\x00\x00" * 32000))
            cursor += len(pcm) // 2 + 32000
    if not references:
        raise ValueError("No recordings matched the annotation set.")
    return b"".join(pieces), references, annotation


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, default=Path("data/local/fleurs/manifest.jsonl"))
    cli.add_argument("--annotations", type=Path, default=Path("data/latency_endpoints.json"))
    cli.add_argument("--repeat", type=positive_int, default=1)
    cli.add_argument("--capture-device", type=int,
                     help="Concurrently monitor real input; replay still supplies model audio")
    cli.add_argument("--report", type=Path, required=True)
    args = cli.parse_args()
    pcm, references, annotations = load_fixture(args.manifest, args.annotations, args.repeat)
    power_start = psutil.sensors_battery()
    offers, results, calibrations, health = [], [], [], []
    vad = LiveVAD(SileroVAD(Path(".cache/models/silero")), 16000, 1)
    worker = InferenceWorker(
        WorkerConfig(Path(".cache/models")), on_result=lambda event: results.append(
            numeric_result(event)
        ),
    )
    capture = MicrophoneCapture() if args.capture_device is not None else None
    stream = None
    failure = None
    processed_frames = 0
    max_delivery_lateness = 0.0
    started = None

    def drain_capture():
        nonlocal processed_frames
        if capture is not None:
            while True:
                try:
                    block = capture.blocks.get_nowait()
                except Empty:
                    break
                processed_frames += block.frames
            if capture.error is not None:
                raise RuntimeError(f"Capture callback failed: {capture.error}")

    def submit(segments):
        for segment in segments:
            accepted = worker.submit(segment)
            offers.append({
                "sequence": worker.stats["offered"], "accepted": accepted,
                "source": segment.metadata(),
            })

    try:
        worker.start()
        if capture is not None:
            stream = sd.RawInputStream(
                device=args.capture_device, samplerate=48000, channels=1,
                dtype="int16", blocksize=0, callback=capture.callback,
            )
            stream.start()
        started = perf_counter() + 0.1
        for reference in references:
            reference["end_monotonic_interval"] = [
                started + end for end in reference["end_interval_s"]
            ]
        next_health, next_progress = started, started + 30
        for offset in range(0, len(pcm) // 2, 320):
            data = pcm[offset * 2:(offset + 320) * 2]
            count = len(data) // 2
            due = started + (offset + count) / 16000
            while perf_counter() < due:
                worker.poll()
                drain_capture()
                sleep(min(0.01, max(0.0, due - perf_counter())))
            now = perf_counter()
            max_delivery_lateness = max(max_delivery_lateness, now - due)
            submit(vad.push(AudioBlock(data, count, offset, offset / 16000, offset / 16000)))
            worker.poll()
            drain_capture()
            if now >= next_health:
                if stream is not None:
                    if not stream.active:
                        raise RuntimeError("Physical microphone stopped unexpectedly.")
                    calibrations.append(clock_sample(lambda: stream.time))
                health.append({
                    "elapsed_s": now - started,
                    "parent_rss_mib": psutil.Process().memory_info().rss / 1024**2,
                    "worker_rss_mib": (
                        psutil.Process(worker.process.pid).memory_info().rss / 1024**2
                    ),
                })
                next_health = now + 1
            if now >= next_progress:
                print(f"Replay {offset / 16000:.1f}s: completed={worker.stats['completed']} "
                      f"dropped={worker.stats['dropped_full']}", flush=True)
                next_progress = now + 30
        submit(vad.finish("eof"))
        if stream is not None:
            stream.close()
            drain_capture()
        worker.close()
    except (Exception, KeyboardInterrupt) as error:
        failure = error
    finally:
        if stream is not None:
            try:
                stream.close()
                drain_capture()
            except Exception as error:
                failure = failure or error
        try:
            worker.close(drain=False)
        except Exception as error:
            failure = failure or error
    if started is None:
        for reference in references:
            reference["end_monotonic_interval"] = reference["end_interval_s"]
    evaluation = evaluate_cases(references, offers, results)
    power_end = psutil.sensors_battery()
    report = {
        "scope": "Annotated file replay at nominal rate; not physical mic speech-end latency",
        "physical_latency_certified": False,
        "annotation_reviewed": annotations.get("human_verified", False),
        "annotation_method": annotations["method"],
        "annotation_sha256": hashlib.sha256(args.annotations.read_bytes()).hexdigest(),
        "python": platform.python_version(), "config": asdict(VADConfig()),
        "input_s": len(pcm) / 32000, "max_delivery_lateness_s": max_delivery_lateness,
        "replay_started_monotonic": started, "references": references,
        "evaluation": evaluation, "offers": offers, "results": results,
        "inference": worker.summary(), "health_samples": health,
        "power_start": power_start._asdict() if power_start else None,
        "power_end": power_end._asdict() if power_end else None,
        "capture": None if capture is None else {
            **asdict(capture.stats), "processed_frames": processed_frames,
            "stream_closed": stream.closed, "sample_rate": 48000,
            "source_supplied_to_models": False,
        },
        "clock_calibrations": calibrations,
        "error": None if failure is None else f"{type(failure).__name__}: {failure}",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in evaluation.items() if key != "cases"}, indent=2))
    if failure is not None:
        raise failure


if __name__ == "__main__":
    main()

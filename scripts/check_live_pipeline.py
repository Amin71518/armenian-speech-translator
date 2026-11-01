"""Real VAD -> spawned ASR/MT file replay; not physical speech-end latency evidence."""

import argparse
import hashlib
import json
import sys
import wave
from dataclasses import asdict
from pathlib import Path
from time import perf_counter, sleep

import psutil

from armenian_speech.cli import positive_int, read_manifest
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.live_vad import LiveVAD
from armenian_speech.microphone import AudioBlock, capture
from armenian_speech.microphone import parser as microphone_parser
from armenian_speech.vad import SileroVAD, VADConfig
from scripts.check_vad import replay


def replay_realtime(model, pcm: bytes, worker) -> dict:
    """Deliver file samples at their nominal rate; never pace on worker completion."""
    model.reset()
    processor = LiveVAD(model, 16000, 1)
    started = perf_counter()
    for offset in range(0, len(pcm) // 2, 320):
        data = pcm[offset * 2:(offset + 320) * 2]
        frames = len(data) // 2
        due = started + (offset + frames) / 16000
        while perf_counter() < due:
            worker.poll()
            sleep(min(0.01, max(0.0, due - perf_counter())))
        block = AudioBlock(data, frames, offset, offset / 16000, offset / 16000)
        for segment in processor.push(block):
            worker.submit(segment)
        worker.poll()
    for segment in processor.finish("eof"):
        worker.submit(segment)
    return processor.stats


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, default=Path("data/local/fleurs/manifest.jsonl"))
    cli.add_argument("--limit", type=positive_int, default=3)
    cli.add_argument("--threads", type=positive_int, default=4)
    cli.add_argument("--realtime", action="store_true",
                     help="Deliver file audio at nominal rate; observe the live queue policy")
    cli.add_argument("--microphone-device", type=int,
                     help="Also capture this real input during replay")
    cli.add_argument("--report", type=Path, required=True)
    args = cli.parse_args()
    rows = read_manifest(args.manifest)[:args.limit]
    power_start = psutil.sensors_battery()
    vad = SileroVAD(Path(".cache/models/silero"))
    worker = InferenceWorker(
        WorkerConfig(Path(".cache/models"), threads=args.threads), diagnostics=True,
    )
    samples = []
    worker_rss_ready = None
    failure = None
    try:
        worker.start()
        worker_rss_ready = psutil.Process(worker.process.pid).memory_info().rss / 1024**2
        for row in rows:
            if hashlib.sha256(row["path"].read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError(f"WAV checksum mismatch: {row['path']}")
            with wave.open(str(row["path"]), "rb") as audio:
                if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (
                    16000, 1, 2,
                ):
                    raise ValueError("Replay requires mono PCM16 16 kHz WAV.")
                pcm = b"\x00\x00" * 16000 + audio.readframes(audio.getnframes())
                pcm += b"\x00\x00" * 16000
            if args.realtime:
                stats = replay_realtime(vad, pcm, worker)
            else:
                segments, stats = replay(vad, pcm)
                for segment in segments:
                    # This offline producer is deliberately paced; live capture never waits here.
                    while worker.stats["accepted"] - worker.stats["completed"] >= worker.capacity:
                        worker.poll()
                        sleep(0.01)
                    if not worker.submit(segment):
                        raise RuntimeError("Unexpected phrase rejection in paced replay.")
            print(f"Replay: {row['path'].name}, {stats['segments']} VAD phrase(s)", flush=True)
            samples.append({"sample": row["path"].name, "vad": stats})
        if args.microphone_device is not None:
            microphone_args = microphone_parser().parse_args([
                "--device", str(args.microphone_device), "--sample-rate", "48000",
                "--live", "--duration", "5", "--diagnostics",
            ])
            capture(microphone_args, worker)
        else:
            worker.close()
    except Exception as error:
        failure = error
    finally:
        try:
            worker.close(drain=False)
        except Exception as error:
            failure = failure or error
    power_end = psutil.sensors_battery()
    report = {
        "scope": (
            "File audio at nominal rate, live queue policy; not physical speech-end latency"
            if args.realtime else
            "Unpaced file/VAD replay, paced job submission; not live speech-end latency"
        ),
        "concurrent_microphone_device": args.microphone_device,
        "config": asdict(VADConfig()),
        "samples": samples, "inference": worker.summary(),
        "error": f"{type(failure).__name__}: {failure}" if failure is not None else None,
        "worker_rss_after_load_mib": worker_rss_ready,
        "power_start": power_start._asdict() if power_start else None,
        "power_end": power_end._asdict() if power_end else None,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["inference"], indent=2), flush=True)
    if failure is not None:
        raise failure


if __name__ == "__main__":
    main()

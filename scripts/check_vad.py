"""Offline streaming VAD screening/CPU timing; not a live speech-end latency test."""

import argparse
import hashlib
import json
import platform
import sys
import wave
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from time import perf_counter, process_time

import psutil

from armenian_speech.cli import positive_int, read_manifest
from armenian_speech.live_vad import LiveVAD
from armenian_speech.metrics import MemorySampler
from armenian_speech.microphone import AudioBlock
from armenian_speech.vad import MODEL_SHA256, SileroVAD, VADConfig


def replay(
    model, pcm: bytes, rate: int = 16000, config: VADConfig | None = None,
) -> tuple[list, dict]:
    model.reset()
    processor = LiveVAD(model, rate, 1, config)
    result = []
    for offset in range(0, len(pcm) // 2, 511):
        data = pcm[offset * 2:(offset + 511) * 2]
        result.extend(processor.push(AudioBlock(
            data, len(data) // 2, offset, offset / rate, offset / rate, 0.0,
        )))
    result.extend(processor.finish("eof"))
    return result, processor.stats


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, default=Path("data/local/fleurs/manifest.jsonl"))
    cli.add_argument("--model-dir", type=Path, default=Path(".cache/models/silero"))
    cli.add_argument("--passes", type=positive_int, default=2)
    cli.add_argument("--report", type=Path, required=True)
    args = cli.parse_args()
    rows = read_manifest(args.manifest)
    power_start = psutil.sensors_battery()
    with MemorySampler() as memory:
        before = perf_counter()
        model = SileroVAD(args.model_dir)
        load_s = perf_counter() - before
        silence, silence_stats = replay(model, b"\x00\x00" * 80000)
        samples = []
        for pass_index in range(args.passes):
            for row in rows:
                data = row["path"].read_bytes()
                if hashlib.sha256(data).hexdigest() != row["sha256"]:
                    raise ValueError(f"WAV checksum mismatch: {row['path']}")
                with wave.open(str(row["path"]), "rb") as audio:
                    if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (
                        16000, 1, 2,
                    ):
                        raise ValueError("VAD screening requires mono PCM16 16 kHz WAV.")
                    # Known inserted silence is a control, not an annotation of speech edges.
                    pcm = b"\x00\x00" * 16000 + audio.readframes(audio.getnframes())
                    pcm += b"\x00\x00" * 16000
                started, cpu_before = perf_counter(), process_time()
                segments, stats = replay(model, pcm)
                elapsed, cpu = perf_counter() - started, process_time() - cpu_before
                sample = {
                    "sample": row["path"].name, "pass": pass_index + 1,
                    "input_s": len(pcm) / 32000, "wall_s": elapsed, "cpu_s": cpu,
                    "segment_metadata": [segment.metadata() for segment in segments], **stats,
                }
                samples.append(sample)
                print(f"Pass {pass_index + 1} {row['path'].name}: "
                      f"{len(segments)} phrases, VAD={stats['vad_wall_s']:.4f}s", flush=True)
    windows = sum(row["vad_windows"] for row in samples)
    power_end = psutil.sensors_battery()
    report = {
        "scope": "Unpaced WAV replay with inserted silence; no ASR/MT or live latency measurement",
        "python": platform.python_version(),
        "versions": {name: version(name) for name in ("numpy", "av", "onnxruntime")},
        "model_sha256": MODEL_SHA256, "provider": "CPUExecutionProvider", "vad_threads": 1,
        "config": asdict(VADConfig()), "model_load_s": load_s,
        "power_start": power_start._asdict() if power_start else None,
        "power_end": power_end._asdict() if power_end else None,
        "silence_control": {"segments": len(silence), **silence_stats},
        "summary": {
            "files": len(rows), "passes": args.passes, "windows": windows,
            "mean_vad_window_ms": 1000 * sum(row["vad_wall_s"] for row in samples) / windows,
            "max_vad_window_ms": 1000 * max(row["vad_max_window_s"] for row in samples),
            "streaming_rtf": sum(row["wall_s"] for row in samples)
            / sum(row["input_s"] for row in samples),
            "process_cpu_rtf": sum(row["cpu_s"] for row in samples)
            / sum(row["input_s"] for row in samples),
            "sampled_rss_mib": memory.peak_bytes / 1024**2,
        },
        "samples": samples,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "silence_segments": len(silence)}, indent=2))


if __name__ == "__main__":
    main()

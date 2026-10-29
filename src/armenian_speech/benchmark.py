"""ASR-only evaluation; each backend must be measured in a fresh process."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter

from armenian_speech.cli import positive_int, read_manifest
from armenian_speech.metrics import MemorySampler, error_rates


def evaluate(asr, rows: list[dict]) -> dict:
    samples, references, hypotheses, examples = [], [], [], []
    for row in rows:
        started = perf_counter()
        segments, duration = asr.transcribe(row["path"])
        elapsed = perf_counter() - started
        if duration <= 0:
            raise ValueError("Audio duration must be positive")
        text = " ".join(segment.text for segment in segments)
        references.append(row["reference_hy"])
        hypotheses.append(text)
        sample = {
            "sample": row["path"].name, "asr_s": elapsed, "duration_s": duration,
            "rtf": elapsed / duration,
            **error_rates([row["reference_hy"]], [text]),
        }
        samples.append(sample)
        # A few examples are explicitly requested for the research report, not runtime logging.
        if len(examples) < 3:
            examples.append({"sample": sample["sample"], "reference": references[-1], "text": text})
        print(f"{sample['sample']} ASR={elapsed:.3f}s WER={sample['wer']:.3f} HY: {text}",
              flush=True)
    return {
        "summary": {
            "mean_asr_s": statistics.mean(row["asr_s"] for row in samples),
            "max_asr_s": max(row["asr_s"] for row in samples),
            "rtf": sum(row["asr_s"] for row in samples)
            / sum(row["duration_s"] for row in samples),
            **error_rates(references, hypotheses),
        },
        "samples": samples, "examples": examples,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--backend", choices=["whisper", "onnx"], required=True)
    cli.add_argument("--whisper-decoding", choices=["baseline", "greedy"], default="baseline")
    cli.add_argument("--manifest", type=Path, default=Path("data/local/fleurs/manifest.jsonl"))
    cli.add_argument("--model-dir", type=Path, default=Path(".cache/models/vana"))
    cli.add_argument("--threads", type=positive_int, default=4)
    cli.add_argument("--passes", type=positive_int, default=2)
    cli.add_argument("--limit", type=positive_int)
    cli.add_argument("--report", type=Path, required=True)
    args = cli.parse_args()
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[name] = str(args.threads)
    rows = read_manifest(args.manifest)
    if args.limit:
        rows = rows[:args.limit]
    for row in rows:
        with row["path"].open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != row.get("sha256"):
            raise ValueError(f"WAV checksum mismatch: {row['path']}")
    with MemorySampler() as memory:
        initial_rss = memory.process.memory_info().rss
        started = perf_counter()
        if args.backend == "whisper":
            from armenian_speech.asr import ArmenianASR

            temperature = 0.0 if args.whisper_decoding == "greedy" else (
                0.0, 0.2, 0.4, 0.6, 0.8, 1.0,
            )
            asr = ArmenianASR(
                "base", Path(".cache/models"), args.threads, True, temperature=temperature,
            )
            model = {
                "name": "base", "language": "hy", "task": "transcribe", "beam_size": 1,
                "temperature": temperature,
            }
        else:
            from armenian_speech.asr_onnx import OnnxArmenianASR

            asr = OnnxArmenianASR(args.model_dir, args.threads)
            model = asr.provenance
        load_s = perf_counter() - started
        passes = []
        for index in range(args.passes):
            print(f"Pass {index + 1}/{args.passes} ({args.backend})", flush=True)
            passes.append(evaluate(asr, rows))
    report = {
        "backend": args.backend, "model": model, "threads": args.threads,
        "python": platform.python_version(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("onnx-asr", "onnxruntime", "faster-whisper", "ctranslate2", "jiwer")
        },
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "measurement": "ASR only, including WAV decoding; no translation, no VAD, batch size 1",
        "cpu_policy": "4 by default: ASR intra-op and OMP/MKL/OpenBLAS; ORT inter-op=1",
        "onnx_preprocessor": "onnx-asr 0.12 CPU default: NumPy Nemo preprocessor",
        "pass_policy": "Pass 1 includes first inference; later passes reuse the loaded model",
        "model_load_s": load_s,
        "initial_rss_mib": initial_rss / 1024**2,
        "rss_sampled_peak_mib": memory.peak_bytes / 1024**2,
        "passes": passes,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"memory_mib": report["rss_sampled_peak_mib"], "load_s": load_s,
                      "passes": [p["summary"] for p in passes]}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

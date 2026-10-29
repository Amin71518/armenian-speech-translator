"""WAV transcription and an opt-in numeric benchmark report, without saved transcripts."""

import argparse
import importlib.metadata
import json
import platform
import statistics
import sys
import wave
from pathlib import Path
from time import perf_counter

from armenian_speech.metrics import MemorySampler, error_rates
from armenian_speech.pipeline import process_wav


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def read_manifest(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("reference_hy"), str):
            raise ValueError(f"Manifest line {line_number}: reference_hy must be a string")
        if not row["reference_hy"].strip():
            raise ValueError(f"Manifest line {line_number}: reference_hy is empty")
        if not isinstance(row.get("audio"), str):
            raise ValueError(f"Manifest line {line_number}: audio must be a path")
        row["path"] = (path.parent / row["audio"]).resolve()
        validate_wav(row["path"])
        rows.append(row)
    if not rows:
        raise ValueError("Manifest contains no samples")
    return rows


def validate_wav(path: Path) -> None:
    if path.suffix.lower() != ".wav":
        raise ValueError(f"Expected a WAV file: {path}")
    with wave.open(str(path), "rb") as audio:
        if audio.getnframes() == 0:
            raise ValueError(f"Empty WAV: {path}")


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Local Armenian WAV -> Armenian text -> English")
    source = cli.add_mutually_exclusive_group(required=True)
    source.add_argument("--wav", type=Path, help="One WAV file")
    source.add_argument("--manifest", type=Path, help="JSONL benchmark manifest")
    cli.add_argument("--asr-model", default="base", help="Multilingual Whisper name or local path")
    cli.add_argument("--translation-model", default="Helsinki-NLP/opus-mt-hy-en")
    cli.add_argument("--threads", type=positive_int, default=4)
    cli.add_argument("--cache-dir", type=Path, default=Path(".cache/models"))
    cli.add_argument("--offline", action="store_true", help="Require cached models; no downloads")
    cli.add_argument("--report", type=Path, help="Save numeric metrics only, never transcripts")
    return cli


def run(args: argparse.Namespace) -> None:
    from armenian_speech.asr import ArmenianASR
    from armenian_speech.translation import ArmenianTranslator

    if args.asr_model.endswith(".en"):
        raise ValueError("English-only Whisper cannot transcribe Armenian")
    if args.manifest:
        rows = read_manifest(args.manifest)
    else:
        validate_wav(args.wav)
        rows = [{"path": args.wav}]
    status = "Loading cached CPU models (offline)..." if args.offline else (
        "Loading local CPU models (first run may download weights)..."
    )
    print(status, file=sys.stderr)
    with MemorySampler() as memory:
        started = perf_counter()
        asr = ArmenianASR(args.asr_model, args.cache_dir, args.threads, args.offline)
        asr_load_s = perf_counter() - started
        started = perf_counter()
        translator = ArmenianTranslator(
            args.translation_model, args.cache_dir, args.threads, args.offline,
        )
        translation_load_s = perf_counter() - started
        measurements, references, hypotheses = [], [], []
        for index, row in enumerate(rows, 1):
            print(f"\nFile {index}/{len(rows)}: {row['path'].name}", flush=True)
            result = process_wav(row["path"], asr, translator)
            if row.get("reference_en"):
                print(f"Reference EN (FLEURS): {row['reference_en']}", flush=True)
            if "reference_hy" in row:
                references.append(row["reference_hy"])
                hypotheses.append(result["text"])
                result.update(error_rates([row["reference_hy"]], [result["text"]]))
            result.pop("text")  # Do not save ASR output in reports.
            result["sample"] = row["path"].name
            measurements.append(result)
            print(
                f"ASR={result['asr_s']:.3f}s MT={result['translation_s']:.3f}s "
                f"total={result['elapsed_s']:.3f}s RTF={result['rtf']:.3f}",
                flush=True,
            )
    timings = sorted(row["elapsed_s"] for row in measurements)
    summary = {
        "count": len(measurements),
        "mean_s": statistics.mean(timings),
        "median_s": statistics.median(timings),
        "max_s": max(timings),
        "rtf": sum(row["elapsed_s"] for row in measurements)
        / sum(row["duration_s"] for row in measurements),
        "rss_sampled_peak_mib": memory.peak_bytes / 1024**2,
    }
    if references:
        summary.update(error_rates(references, hypotheses))
    report = {
        "runtime": {
            "python": platform.python_version(),
            "libraries": {
                name: importlib.metadata.version(name)
                for name in (
                    "faster-whisper", "ctranslate2", "av", "transformers", "torch", "jiwer",
                )
            },
        },
        "asr_model": args.asr_model,
        "translation_model": args.translation_model,
        "language": "hy",
        "asr_compute_type": "int8",
        "translation_compute_type": "float32",
        "beam_size": 1,
        "threads": args.threads,
        "asr_load_s": asr_load_s,
        "translation_load_s": translation_load_s,
        "warmup": "No separate warmup; first sample includes cold inference",
        "latency_scope": "Whole WAV processing; not live end-of-phrase latency",
        "summary": summary,
        "samples": measurements,
    }
    print("\nMetrics (not a live latency test):")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        run(args)
    except (OSError, ValueError, RuntimeError, ImportError, wave.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0

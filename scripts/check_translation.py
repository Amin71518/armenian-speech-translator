"""Isolate translation quality by feeding the Armenian references instead of ASR errors."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter

import psutil

from armenian_speech.cli import positive_int, read_manifest
from armenian_speech.metrics import MemorySampler
from armenian_speech.translation import DEFAULT_TRANSLATION_MODEL, ArmenianTranslator


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--threads", type=positive_int, default=4)
    cli.add_argument("--offline", action="store_true")
    cli.add_argument("--passes", type=positive_int, default=2)
    cli.add_argument("--report", type=Path)
    args = cli.parse_args()
    rows = read_manifest(args.manifest)
    from sacrebleu.metrics import CHRF

    metric = CHRF(word_order=2)
    if not all(row.get("reference_en") for row in rows):
        raise ValueError("Translation comparison requires English references for every sample")
    passes = []
    power_start = psutil.sensors_battery()
    with MemorySampler() as memory:
        started = perf_counter()
        translator = ArmenianTranslator(Path(".cache/models"), args.threads, args.offline)
        load_s = perf_counter() - started
        for pass_number in range(args.passes):
            print(f"\nPass {pass_number + 1}/{args.passes}", flush=True)
            timings, predictions, samples, examples = [], [], [], []
            for index, row in enumerate(rows, 1):
                started = perf_counter()
                english = translator.translate(row["reference_hy"])
                elapsed = perf_counter() - started
                timings.append(elapsed)
                predictions.append(english)
                samples.append({"sample": row["audio"], "translation_s": elapsed})
                if len(examples) < 3:
                    examples.append({"sample": row["audio"], "prediction": english,
                                     "reference": row["reference_en"]})
                print(f"\n{index:02d} HY reference: {row['reference_hy']}", flush=True)
                print(f"   EN prediction: {english}", flush=True)
                print(f"   EN reference:  {row['reference_en']}", flush=True)
                print(f"   Translation: {elapsed:.3f}s", flush=True)
            score = metric.corpus_score(predictions, [[row["reference_en"] for row in rows]])
            summary = {"mean_s": statistics.mean(timings), "max_s": max(timings),
                       "chrf_plus_plus": score.score}
            passes.append({"summary": summary, "samples": samples, "examples": examples})
            print(json.dumps(summary), flush=True)
    power_end = psutil.sensors_battery()
    report = {
        "python": platform.python_version(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("torch", "transformers", "tokenizers", "sacrebleu")
        },
        "model": DEFAULT_TRANSLATION_MODEL, "revision": translator.revision,
        "threads": args.threads,
        "precision": "float32", "num_beams": translator.generation_options["num_beams"],
        "decoding": "do_sample=False, max_new_tokens=256",
        "inputs": "Correct normalized Armenian reference text only; no ASR",
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "metric": str(metric.get_signature()),
        "metric_version": importlib.metadata.version("sacrebleu"),
        "model_load_s": load_s, "rss_sampled_peak_mib": memory.peak_bytes / 1024**2,
        "power_start": power_start._asdict() if power_start else None,
        "power_end": power_end._asdict() if power_end else None,
        "passes": passes,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"load_s": load_s, "memory_mib": report["rss_sampled_peak_mib"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

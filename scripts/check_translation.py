"""Isolate translation quality by feeding the Armenian references instead of ASR errors."""

import argparse
import statistics
import sys
from pathlib import Path
from time import perf_counter

from armenian_speech.cli import positive_int, read_manifest
from armenian_speech.translation import ArmenianTranslator


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--model", default="Helsinki-NLP/opus-mt-hy-en")
    cli.add_argument("--threads", type=positive_int, default=4)
    cli.add_argument("--offline", action="store_true")
    args = cli.parse_args()
    rows = read_manifest(args.manifest)
    translator = ArmenianTranslator(args.model, Path(".cache/models"), args.threads, args.offline)
    timings = []
    for index, row in enumerate(rows, 1):
        started = perf_counter()
        english = translator.translate(row["reference_hy"])
        elapsed = perf_counter() - started
        timings.append(elapsed)
        print(f"\n{index:02d} HY reference: {row['reference_hy']}", flush=True)
        print(f"   EN prediction: {english}", flush=True)
        print(f"   EN reference:  {row.get('reference_en') or '(unavailable)'}", flush=True)
        print(f"   Translation: {elapsed:.3f}s", flush=True)
    print(f"\nMean={statistics.mean(timings):.3f}s Max={max(timings):.3f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Stage 4.1 isolated CPU comparison; labelled clips, not full live diarization/DER."""

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import wave
from pathlib import Path
from time import perf_counter

import numpy as np
import psutil

from scripts.prepare_diarization import MODELS
from scripts.speaker_probe import Extractor, Registry, calibrate


def read_rows():
    directory = Path("data/local/diarization")
    rows = [json.loads(line) for line in (directory / "manifest.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        path = directory / row["audio"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Fixture checksum mismatch")
        with wave.open(str(path), "rb") as audio:
            if (audio.getnchannels(), audio.getframerate(), audio.getsampwidth()) != (1, 16000, 2):
                raise ValueError("Expected mono PCM16 16kHz")
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
        # Fixed crop before seeing embeddings/labels; separate utterances for calibration/test.
        row["pcm"] = samples[4000:68000].astype(np.float32) / 32768
        if len(row["pcm"]) != 64000:
            raise ValueError("Fixture too short")
    return rows


def evaluate(extractor, rows, threshold, seconds):
    groups = {speaker: [row for row in rows if row["speaker"] == speaker
                        and row["split"] == "evaluation"]
              for speaker in dict.fromkeys(row["speaker"] for row in rows)}
    speakers = list(groups)
    if len(speakers) != 3 or any(len(group) != 4 for group in groups.values()):
        raise ValueError("Expected three speakers and four held-out utterances each")
    registry, mapping, predictions, times = Registry(threshold), {}, [], []
    # Four alternating A/B turns, then unseen C, then returning A/B/C. No known speaker count.
    sequence = [(s, i) for i in range(4) for s in speakers[:2]]
    sequence += [(speakers[2], 0), (speakers[0], 0), (speakers[1], 0)]
    sequence += [(speakers[2], i) for i in range(1, 4)]
    errors = unknown = 0
    for speaker, index in sequence:
        row = groups[speaker][index]
        before = perf_counter()
        embedding = extractor.embed(row["pcm"][:int(seconds * 16000)])
        event = registry.assign(embedding)
        elapsed = perf_counter() - before
        times.append(elapsed)
        expected = mapping.setdefault(speaker, f"Speaker {len(mapping) + 1}")
        if event["label"] == "Unknown":
            unknown += 1
        if event["label"] != expected:
            errors += 1
        predictions.append({"audio": row["audio"], "speaker_id": speaker,
                            "expected": expected, **event, "elapsed_s": elapsed})
    return {"clip_s": seconds, "count": len(predictions), "errors_including_unknown": errors,
            "unknown": unknown, "clusters": len(registry.centroids),
            "mean_s": float(np.mean(times)), "p95_s": float(np.percentile(times, 95)),
            "max_s": max(times), "rtf": sum(times) / (seconds * len(times)),
            "predictions": predictions}


def benchmark(name, threads, with_pipeline=False):
    rows = read_rows()
    pipeline_models = None
    pipeline_probe = None
    if with_pipeline:
        from armenian_speech.live_pipeline import WorkerConfig, load_models

        pipeline_models = load_models(WorkerConfig(Path(".cache/models")))
        manifest = Path("data/local/fleurs/manifest.jsonl")
        fixture = json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])
        wav = manifest.parent / fixture["audio"]
        if hashlib.sha256(wav.read_bytes()).hexdigest() != fixture["sha256"]:
            raise ValueError("Pipeline probe checksum mismatch")

        def infer():
            before = perf_counter()
            segments, _ = pipeline_models[0].transcribe(wav)
            text = " ".join(segment.text for segment in segments).strip()
            translation = pipeline_models[1].translate(text)
            if not text or not translation:
                raise ValueError("Empty pipeline probe")
            return (text, translation), perf_counter() - before

        first_output, first_s = infer()
        pipeline_probe = {"audio": fixture["audio"], "before_s": first_s}
    process = psutil.Process()
    baseline = process.memory_info().rss
    peak = [baseline]
    stop = threading.Event()

    def sample():
        while not stop.wait(0.02):
            peak[0] = max(peak[0], process.memory_info().rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        before = perf_counter()
        extractor = Extractor(name, threads)
        load_s = perf_counter() - before
        speakers = list(dict.fromkeys(row["speaker"] for row in rows))
        calibration = [row for row in rows if row["split"] == "calibration"
                       and row["speaker"] in speakers[:2]]
        vectors = [extractor.embed(row["pcm"]) for row in calibration]
        if any(vector is None for vector in vectors):
            raise ValueError("Calibration clip rejected")
        fitted = calibrate(vectors, [row["speaker"] for row in calibration])
        results = [evaluate(extractor, rows, fitted["threshold"], seconds)
                   for seconds in (0.4, 1.0, 2.0, 4.0)]
        # Probe overlap and within-chunk speaker changes without pretending to detect them.
        a, b = [next(row["pcm"] for row in rows if row["speaker"] == speaker
                     and row["split"] == "evaluation") for speaker in speakers[:2]]
        stress = {}
        for kind, pcm in {"silence": np.zeros(64000, dtype=np.float32),
                          "overlap": (a + b) / 2,
                          "speaker_change": np.concatenate((a[:32000], b[:32000]))}.items():
            vector = extractor.embed(pcm)
            stress[kind] = {"rejected": vector is None, "cosine_to_calibration":
                            [] if vector is None else [float(vector @ v) for v in vectors],
                            "automatic_overlap_detection": False}
        if with_pipeline:
            second_output, second_s = infer()
            pipeline_probe.update(after_s=second_s, output_unchanged=first_output == second_output)
            if first_output != second_output:
                raise ValueError("Pipeline probe output changed")
        peak[0] = max(peak[0], process.memory_info().rss)
        return {"candidate": name, "sha256": MODELS[name][1], "threads": threads,
                "load_s": load_s, "rss_baseline_mib": baseline / 2 ** 20,
                "rss_sampled_peak_mib": peak[0] / 2 ** 20,
                "rss_sampled_increment_mib": (peak[0] - baseline) / 2 ** 20,
                "calibration": fitted, "results": results, "stress": stress,
                "scope": "Clean English clips with oracle boundaries; not DER or live E2E",
                "runtime": "sherpa-onnx==2.0.1, CPU", "margin": 0.08,
                "pipeline_models_resident": pipeline_models is not None,
                "pipeline_metadata": pipeline_models[2] if pipeline_models else None,
                "pipeline_probe": pipeline_probe}
    finally:
        stop.set()
        sampler.join()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--candidate", choices=["all", *MODELS], default="all")
    cli.add_argument("--threads", type=int, choices=[1, 2, 4], default=1)
    cli.add_argument("--report", type=Path)
    cli.add_argument("--with-pipeline", action="store_true")
    args = cli.parse_args()
    Path("reports").mkdir(exist_ok=True)
    if args.candidate == "all":
        for name in MODELS:
            command = [sys.executable, "-m", "scripts.check_speakers", "--candidate", name,
                       "--threads", str(args.threads)]
            if args.with_pipeline:
                command.append("--with-pipeline")
            subprocess.run(command, check=True)
        return
    report = benchmark(args.candidate, args.threads, args.with_pipeline)
    suffix = "_resident" if args.with_pipeline else ""
    path = args.report or Path(f"reports/stage41_{args.candidate}_{args.threads}t{suffix}.json")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"results", "stress"}}, indent=2))
    for row in report["results"]:
        print(json.dumps({k: v for k, v in row.items() if k != "predictions"}))


if __name__ == "__main__":
    main()

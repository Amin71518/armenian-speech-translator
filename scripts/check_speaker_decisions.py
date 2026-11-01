"""Public-fixture diagnosis of first42 tracking; no capture, ASR, tuning or call-quality claim."""

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from time import perf_counter

import numpy as np

from armenian_speech.speakers import Extractor, Registry, SpeakerTracker
from armenian_speech.vad import SileroVAD, SpeechSegment
from scripts.check_speakers import read_rows
from scripts.check_vad import replay


class CachedExtractor:
    """Reuse identical native results across comparison arms; timings are not benchmarks."""

    def __init__(self):
        self.native = Extractor()
        self.cache = {}
        self.calls = []

    def embed(self, pcm):
        key = hashlib.sha256(pcm.tobytes()).hexdigest()
        self.calls.append(key)
        if key not in self.cache:
            self.cache[key] = self.native.embed(pcm)
        return self.cache[key]


class FrozenRegistry(Registry):
    """Offline causal control: retain new identities, undo only matched updates."""

    def assign(self, embedding, *, learn=True):
        centers, counts = list(self.centroids), list(self.counts)
        event = super().assign(embedding, learn=learn)
        if learn and event["reason"] == "match":
            self.centroids, self.counts = centers, counts
        return event


class FrozenTracker(SpeakerTracker):
    """Never selected by a live command; diagnostic experiment only."""

    def __init__(self, extractor):
        super().__init__(extractor)
        self.registry = FrozenRegistry(self.registry.threshold, self.registry.margin,
                                       self.registry.capacity)


def segment(pcm, start=0):
    data = (pcm * 32768).astype("<i2").tobytes()
    return SpeechSegment(data, start, start + len(pcm), start, start + len(pcm),
                         perf_counter(), "silence")


def transform(pcm, kind):
    if kind == "gain":
        return pcm * 0.1
    if kind == "band":
        spectrum = np.fft.rfft(pcm)
        frequency = np.fft.rfftfreq(len(pcm), 1 / 16000)
        spectrum[(frequency < 300) | (frequency > 3400)] = 0
        return np.fft.irfft(spectrum, n=len(pcm)).astype(np.float32)
    if kind == "preroll":
        return np.concatenate((np.zeros(4000, dtype=np.float32), pcm[:-4000]))
    return pcm


def describe(parts):
    return [(part.start_sample, part.end_sample, label, hashlib.sha256(part.pcm).hexdigest())
            for part, label in parts]


def measure(jobs, extractor, baseline_class, *, tracker_class=SpeakerTracker):
    traces = []
    observed = tracker_class(extractor)
    quiet = tracker_class(extractor)
    baseline = baseline_class(extractor)
    owners, first_ids, reasons = {}, {}, Counter()
    total_s = unknown_s = cross_s = duplicate_s = 0.0
    false_new = set()
    seed_centers = []
    seed_cosines = []
    output = []
    for index, (speaker, phrase) in enumerate(jobs):
        calls = []
        arms = []
        decisions = []
        for tracker in (baseline, quiet, observed):
            extractor.calls = []
            parts = (tracker.split(phrase, on_decision=decisions.append)
                     if tracker is observed else tracker.split(phrase))
            arms.append(describe(parts))
            calls.append(list(extractor.calls))
        if not arms[0] == arms[1] == arms[2] or not calls[0] == calls[1] == calls[2]:
            raise AssertionError("Baseline/quiet/diagnostic decisions or model inputs differ")
        for tracker in (baseline, quiet):
            if tracker.registry.counts != observed.registry.counts:
                raise AssertionError("Registry counts differ")
            for a, b in zip(tracker.registry.centroids, observed.registry.centroids, strict=True):
                np.testing.assert_array_equal(a, b)
        if b"".join(part.pcm for part, _ in parts) != phrase.pcm:
            raise AssertionError("PCM conservation failed")
        for i, center in enumerate(observed.registry.centroids):
            if i == len(seed_centers):
                seed_centers.append(center.copy())
            seed_cosines.append(float(seed_centers[i] @ center))
        for decision in decisions:
            reasons[decision["reason"]] += 1
            label, seconds = decision["label"], decision["duration_s"]
            total_s += seconds
            if label == "Unknown":
                unknown_s += seconds
            elif speaker is not None:
                if label not in owners:
                    owners[label] = speaker
                    if speaker in first_ids:
                        false_new.add(label)
                    first_ids.setdefault(speaker, label)
                if owners[label] != speaker:
                    cross_s += seconds
                elif first_ids[speaker] != label:
                    duplicate_s += seconds
        traces.extend({"job_index": index, "fixture_speaker": speaker, **d} for d in decisions)
        output.append({"job_index": index, "fixture_speaker": speaker,
                       "parts": [{"start_sample": a, "end_sample": b, "label": label}
                                 for a, b, label, _ in arms[2]]})
    labelled = any(speaker is not None for speaker, _ in jobs)
    return {
        "reference_quiet_diagnostic_identical": True,
        "jobs": len(jobs), "cells": len(traces), "clusters": len(observed.registry.centroids),
        "unknown_s": unknown_s, "total_s": total_s,
        "false_new_ids": sorted(false_new) if labelled else None,
        "cross_speaker_assigned_s": cross_s if labelled else None,
        "duplicate_identity_assigned_s": duplicate_s if labelled else None,
        "min_cosine_to_initial_centroid": min(seed_cosines) if seed_cosines else None,
        "reasons": dict(reasons), "output": output, "decisions": traces,
    }


def vad_jobs(clips):
    # Source ownership includes any original silence; these are not speech annotations.
    pcm = np.concatenate(clips)
    data = (pcm * 32768).astype("<i2").tobytes()
    phrases, stats = replay(SileroVAD(Path(".cache/models/silero")), data)
    return [(None, phrase) for phrase in phrases], {
        "source_change_samples": [int(v) for v in np.cumsum([len(c) for c in clips])[:-1]],
        "vad": stats,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--baseline", type=Path, required=True,
                     help="Exact first42 speakers.py copy; verified before importing")
    cli.add_argument("--report", type=Path, default=Path("reports/speaker_decisions_initial.json"))
    args = cli.parse_args()
    expected = "d58270b7e2829417bc5babea15933390c17b13bdad26410c572e203fef25c4eb"
    if hashlib.sha256(args.baseline.read_bytes()).hexdigest() != expected:
        raise ValueError("Expected exact first Stage4.2 speakers.py SHA-256")
    spec = importlib.util.spec_from_file_location("first42_speakers", args.baseline)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    rows = read_rows()
    groups = {s: [r for r in rows if r["speaker"] == s and r["split"] == "evaluation"]
              for s in dict.fromkeys(r["speaker"] for r in rows)}
    speakers = list(groups)
    sequence = [(s, i) for i in range(4) for s in speakers[:2]]
    sequence += [(speakers[2], 0), (speakers[0], 0), (speakers[1], 0)]
    sequence += [(speakers[2], i) for i in range(1, 4)]
    extractor, results, controls = CachedExtractor(), {}, {}
    scenarios = [
        ("clean_2s", 2, "clean", False), ("clean_4s", 4, "clean", False),
        ("short_1s_unenrolled", 1, "clean", False),
        ("short_1s_enrolled", 1, "clean", True),
        ("short_400ms_enrolled", 0.4, "clean", True),
        ("gain_0.1_enrolled", 2, "gain", True),
        ("synthetic_band_300_3400_enrolled", 2, "band", True),
        ("preroll_250ms_enrolled", 2, "preroll", True),
    ]
    for name, seconds, kind, enroll in scenarios:
        # Enrollment uses different utterances, also from the evaluation split.
        # This is diagnosis, not a fresh held-out accuracy estimate or calibration.
        jobs = ([(s, segment(groups[s][0]["pcm"][:32000])) for s in speakers]
                if enroll else [])
        jobs += [(s, segment(transform(groups[s][i]["pcm"][:int(seconds * 16000)], kind)))
                 for s, i in sequence]
        results[name] = measure(jobs, extractor, baseline.SpeakerTracker)
        results[name]["enrollment_jobs_included_in_totals"] = len(speakers) if enroll else 0
        controls[name] = measure(jobs, extractor, FrozenTracker, tracker_class=FrozenTracker)
        controls[name]["enrollment_jobs_included_in_totals"] = len(speakers) if enroll else 0
    # Return to the original channel after the bandwidth change, without resetting IDs.
    jobs = [(s, segment(groups[s][0]["pcm"][:32000])) for s in speakers]
    jobs += [(s, segment(transform(groups[s][i]["pcm"][:32000], "band"))) for s, i in sequence]
    jobs += [(s, segment(groups[s][0]["pcm"][:32000])) for s in speakers]
    results["band_then_original_return"] = measure(jobs, extractor, baseline.SpeakerTracker)
    controls["band_then_original_return"] = measure(
        jobs, extractor, FrozenTracker, tracker_class=FrozenTracker,
    )
    clips = [groups[s][1]["pcm"] for s in [speakers[0], speakers[1], speakers[0], speakers[2]]]
    jobs, boundaries = vad_jobs(clips)
    results["continuous_vad_ABAC"] = {**measure(jobs, extractor, baseline.SpeakerTracker),
                                       **boundaries, "identity_metrics_available": False}
    report = {
        "scope": "Existing public English read clips; oracle ownership, not call DER or acceptance",
        "baseline_sha256": expected,
        "current_sha256": hashlib.sha256(Path("src/armenian_speech/speakers.py").read_bytes())
        .hexdigest(),
        "settings": {"threshold": 0.47, "margin": 0.08, "capacity": 8},
        "independent_recordings": 12, "native_unique_inputs": len(extractor.cache),
        "limitations": ["Repeated crops/returns are not independent samples",
                        "Gain/filter/pre-roll are synthetic, not actual call channels",
                        "No thresholds fitted; frozen update is an offline causal control only",
                        "Cached embeddings invalidate compute/latency benchmarking",
                        "Continuous VAD ownership is not labelled speech activity"],
        "scenarios": results,
        "offline_frozen_update_controls": controls,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    for name, result in results.items():
        print(name, json.dumps({k: v for k, v in result.items()
                               if k not in {"decisions", "output", "vad"}}))
    print("Frozen control:", json.dumps({name: {
        k: result[k] for k in ("clusters", "unknown_s", "false_new_ids",
                               "cross_speaker_assigned_s", "duplicate_identity_assigned_s")
    } for name, result in controls.items()}))


if __name__ == "__main__":
    main()

"""Numeric measurement helpers; reference endpoints must be independent of VAD."""

import math
import statistics
from collections.abc import Callable
from time import perf_counter

import numpy as np


def clock_sample(read_clock: Callable[[], float]) -> dict:
    before = perf_counter()
    stream_time = read_clock()
    after = perf_counter()
    if not math.isfinite(stream_time) or stream_time <= 0:
        raise ValueError("Stream clock is missing or non-finite.")
    return {
        "stream_s": stream_time, "monotonic_s": (before + after) / 2,
        "offset_s": (before + after) / 2 - stream_time,
        "bracket_s": after - before,
    }


def align_reference(
    captured: np.ndarray, reference: np.ndarray, expected: int, radius: int,
) -> dict:
    """Normalized waveform correlation in a bounded search window, independent of VAD."""
    low = max(0, expected - radius)
    high = min(len(captured) - len(reference), expected + radius)
    if high < low or len(reference) < 2:
        raise ValueError("Not enough captured audio for reference alignment.")
    target = reference.astype(np.float64)
    target -= target.mean()
    window = captured[low:high + len(target)].astype(np.float64)
    window -= window.mean()
    size = 1 << (len(window) + len(target) - 1).bit_length()
    correlation = np.fft.irfft(
        np.fft.rfft(window, size) * np.conj(np.fft.rfft(target, size)), size,
    )[:high - low + 1]
    energy = np.concatenate(([0.0], np.cumsum(window * window)))
    local_energy = energy[len(target):] - energy[:-len(target)]
    denominator = np.sqrt(np.maximum(local_energy * np.sum(target * target), 1e-30))
    scores = np.abs(correlation) / denominator
    best = int(np.argmax(scores))
    peak, background = float(scores[best]), float(np.quantile(scores, 0.95))
    return {
        "start_sample": low + best, "correlation": peak,
        "peak_over_background": peak / max(background, 1e-12),
        "minimum_correlation": 0.20,
        "reliable": peak >= 0.20 and peak >= 1.5 * background,
    }


def numeric_result(event: dict) -> dict:
    """Drop transient transcripts; output time was sampled after flush in the parent."""
    keys = (
        "sequence", "printed", "skip_reason", "source", "enqueued_monotonic",
        "dequeued_monotonic", "asr_started_monotonic", "asr_finished_monotonic",
        "translation_started_monotonic", "worker_finished_monotonic",
        "output_finished_monotonic", "completion_monotonic", "translation_parts",
    )
    return {**{key: event[key] for key in keys}, "speaker": event.get("speaker"),
            **{key: event[key] for key in ("source_label", "part_index", "last_part", "diarization")
               if key in event}}


def distribution(values: list[float]) -> dict | None:
    if not values:
        return None
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Timing distribution contains non-finite data.")
    ordered = sorted(values)

    def percentile(fraction):
        index = (len(ordered) - 1) * fraction
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)

    return {
        "count": len(values), "mean_s": statistics.mean(values),
        "p50_s": percentile(0.5), "p95_s": percentile(0.95),
        "p99_s": percentile(0.99), "max_s": max(values),
    }


def phase_times(result: dict, speech_end: float) -> dict:
    output = result["output_finished_monotonic"]
    if output is None:
        raise ValueError("A suppressed result has no output latency.")
    stamps = [
        speech_end, result["source"]["decision_monotonic"],
        result["enqueued_monotonic"], result["dequeued_monotonic"],
        result["asr_started_monotonic"], result["asr_finished_monotonic"],
        result["translation_started_monotonic"], result["worker_finished_monotonic"], output,
    ]
    if not all(math.isfinite(stamp) for stamp in stamps):
        raise ValueError("Non-finite latency timestamp.")
    names = (
        "speech_end_to_vad_s", "vad_to_enqueue_s", "queue_wait_s", "wav_preparation_s",
        "asr_s", "translation_preparation_s", "translation_s", "handoff_and_print_s",
    )
    parts = dict(zip(
        names, (b - a for a, b in zip(stamps, stamps[1:], strict=False)), strict=True,
    ))
    if any(value < 0 for value in parts.values()):
        raise ValueError("Latency timeline went backwards; do not clamp invalid measurements.")
    return {**parts, "e2e_s": output - speech_end}


def evaluate_cases(
    references: list[dict], offers: list[dict], results: list[dict],
    *, limit_s: float = 5.0,
) -> dict:
    """Count missing/filtered/truncated output, not just successful latency samples.

    A reference end is an interval. Only output after coverage of the full interval
    is eligible. Earlier forced fragments stay in results but are not natural ends.
    """
    by_sequence = {result["sequence"]: result for result in results}
    cases = []
    for reference in references:
        if reference.get("unavailable_reason"):
            cases.append({"id": reference["id"], "status": "reference_unavailable",
                          "reason": reference["unavailable_reason"]})
            continue
        low, high = reference["end_interval_s"]
        end_low, end_high = reference["end_monotonic_interval"]
        if not (
            all(math.isfinite(value) for value in (low, high, end_low, end_high))
            and low <= high and end_low <= end_high
        ):
            raise ValueError("Invalid reference speech-end interval.")
        covering = [offer for offer in offers if (
            offer["source"]["start_s"] <= low
            and offer["source"]["end_s"] >= high
        )]
        case = {"id": reference["id"], "reference_end_interval_s": [low, high]}
        if len(covering) != 1:
            case["status"] = "uncovered_or_ambiguous"
        else:
            offer = covering[0]
            case["sequence"] = offer["sequence"]
            result = by_sequence.get(offer["sequence"])
            if not offer["accepted"]:
                case["status"] = "queue_rejected"
            elif result is None:
                case["status"] = "unfinished"
            elif not result["printed"]:
                case["status"] = "filtered" if result["skip_reason"] else "empty_asr"
            else:
                output = result["output_finished_monotonic"]
                interval = [output - end_high, output - end_low]
                case["e2e_interval_s"] = interval
                try:
                    case["phases"] = phase_times(result, (end_low + end_high) / 2)
                    case["status"] = (
                        "within_limit" if interval[1] <= limit_s else
                        "over_limit" if interval[0] > limit_s else "boundary_uncertain"
                    )
                except ValueError as error:
                    case["status"] = "invalid_timing"
                    case["error"] = str(error)
        cases.append(case)
    valid = [case for case in cases if case["status"] in (
        "within_limit", "over_limit", "boundary_uncertain",
    )]
    return {
        "expected": len(cases), "measured_outputs": len(valid), "limit_s": limit_s,
        "statuses": {status: sum(case["status"] == status for case in cases)
                     for status in sorted({case["status"] for case in cases})},
        "latency_midpoint": distribution([case["phases"]["e2e_s"] for case in valid]),
        "latency_upper_bound": distribution([case["e2e_interval_s"][1] for case in valid]),
        "violations_or_missing": [case for case in cases if case["status"] != "within_limit"],
        "all_cases_within_limit": bool(cases) and all(
            case["status"] == "within_limit" for case in cases
        ),
        "cases": cases,
    }

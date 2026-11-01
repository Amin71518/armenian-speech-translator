from copy import deepcopy

import numpy as np
import pytest

from armenian_speech.latency import (
    align_reference,
    clock_sample,
    distribution,
    evaluate_cases,
    numeric_result,
    phase_times,
)


def result(output=103.1):
    return {
        "sequence": 1, "printed": True, "skip_reason": None, "translation_parts": 1,
        "source": {"start_s": 5, "end_s": 11, "decision_monotonic": 100.7},
        "enqueued_monotonic": 100.71, "dequeued_monotonic": 101,
        "asr_started_monotonic": 101.1, "asr_finished_monotonic": 101.2,
        "translation_started_monotonic": 101.21, "worker_finished_monotonic": 103,
        "output_finished_monotonic": output, "completion_monotonic": output,
    }


def reference():
    return [{"id": "test", "end_interval_s": [10, 10.1],
             "end_monotonic_interval": [100, 100.1]}]


def offer():
    return [{"sequence": 1, "accepted": True, "source": result()["source"]}]


def test_latency_contains_hangover_queue_inference_and_print():
    parts = phase_times(result(), 100)
    assert parts["e2e_s"] == pytest.approx(3.1)
    assert parts["speech_end_to_vad_s"] == pytest.approx(0.7)
    assert parts["queue_wait_s"] == pytest.approx(0.29)
    assert sum(v for k, v in parts.items() if k != "e2e_s") == pytest.approx(parts["e2e_s"])
    assert parts["e2e_s"] > result()["output_finished_monotonic"] - 100.7


@pytest.mark.parametrize("output,status", [
    (103.1, "within_limit"), (105.05, "boundary_uncertain"), (105.2, "over_limit"),
])
def test_reference_uncertainty_is_included_in_threshold_decision(output, status):
    evaluation = evaluate_cases(reference(), offer(), [result(output)])
    assert evaluation["cases"][0]["status"] == status
    assert evaluation["all_cases_within_limit"] == (status == "within_limit")
    assert len(evaluation["violations_or_missing"]) == (status != "within_limit")


@pytest.mark.parametrize("mode,status", [
    ("filtered", "filtered"), ("empty", "empty_asr"), ("dropped", "queue_rejected"),
    ("unfinished", "unfinished"), ("truncated", "uncovered_or_ambiguous"),
])
def test_missing_output_is_counted_and_never_becomes_a_fast_latency_sample(mode, status):
    offers, results = offer(), [result()]
    if mode in {"filtered", "empty"}:
        results[0].update(printed=False, output_finished_monotonic=None)
        results[0]["skip_reason"] = "single_letter" if mode == "filtered" else None
    elif mode == "dropped":
        offers[0]["accepted"] = False
    elif mode == "unfinished":
        results = []
    else:
        offers[0]["source"]["end_s"] = 10.05
    evaluation = evaluate_cases(reference(), offers, results)
    assert evaluation["expected"] == 1 and evaluation["measured_outputs"] == 0
    assert evaluation["latency_midpoint"] is None
    assert evaluation["cases"][0]["status"] == status
    assert not evaluation["all_cases_within_limit"]


def test_invalid_clock_order_is_reported_without_clamping():
    event = result()
    event["asr_finished_monotonic"] = 99
    evaluation = evaluate_cases(reference(), offer(), [event])
    assert evaluation["cases"][0]["status"] == "invalid_timing"
    assert evaluation["latency_midpoint"] is None


def test_failed_reference_alignment_stays_in_the_expected_denominator():
    evaluation = evaluate_cases([
        {"id": "unmatched", "unavailable_reason": "alignment_failed"},
    ], [], [])
    assert evaluation["expected"] == 1
    assert evaluation["statuses"] == {"reference_unavailable": 1}
    assert len(evaluation["violations_or_missing"]) == 1
    assert not evaluation["all_cases_within_limit"]


def test_summary_lists_every_exceedance_and_includes_tail_percentiles():
    assert distribution([]) is None
    summary = distribution([1, 2, 3, 4, 10])
    assert summary["count"] == 5 and summary["max_s"] == 10
    assert summary["p95_s"] == pytest.approx(8.8)
    refs = reference() + [deepcopy(reference()[0])]
    refs[1]["id"] = "second"
    evaluation = evaluate_cases(refs, offer(), [result(106)])
    assert len(evaluation["violations_or_missing"]) == 2


def test_numeric_result_does_not_persist_transcripts():
    event = {**result(), "armenian": "private text", "english": "private translation"}
    numeric = numeric_result(event)
    assert "armenian" not in numeric and "english" not in numeric
    assert numeric["output_finished_monotonic"] == 103.1


def test_clock_calibration_keeps_call_bracket_as_uncertainty(monkeypatch):
    ticks = iter((100, 100.002))
    monkeypatch.setattr("armenian_speech.latency.perf_counter", lambda: next(ticks))
    sample = clock_sample(lambda: 10)
    assert sample["offset_s"] == pytest.approx(90.001)
    assert sample["bracket_s"] == pytest.approx(0.002)
    with pytest.raises(ValueError, match="missing"):
        monkeypatch.setattr("armenian_speech.latency.perf_counter", lambda: 100)
        clock_sample(lambda: 0)


def test_acoustic_alignment_finds_delay_with_amplitude_change_and_noise():
    rng = np.random.default_rng(42)
    reference = rng.normal(size=800)
    captured = rng.normal(scale=0.03, size=3000)
    captured[527:1327] += reference * 2.7
    aligned = align_reference(captured, reference, expected=500, radius=200)
    assert aligned["start_sample"] == 527
    assert aligned["reliable"] and aligned["correlation"] > 0.99


def test_unrelated_audio_does_not_validate_reference_alignment():
    rng = np.random.default_rng(42)
    aligned = align_reference(rng.normal(size=5000), rng.normal(size=1000), 1000, 500)
    assert not aligned["reliable"]
    with pytest.raises(ValueError, match="Not enough"):
        align_reference(np.zeros(10), np.ones(20), 0, 2)

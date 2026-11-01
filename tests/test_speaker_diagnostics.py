import json
from dataclasses import replace

import numpy as np
import pytest

from armenian_speech import combined, system_audio
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.speakers import SpeakerTracker, unit
from tests.test_live_pipeline import fake_models, phrase, wait_for
from tests.test_speakers import SignExtractor, audio, fake_tracker


class FixedExtractor:
    def __init__(self, values):
        self.values = iter(values)

    def embed(self, pcm):
        value = next(self.values)
        return None if value is None else unit(value)


@pytest.mark.parametrize("centers,vector,halves,seconds,reason", [
    ([], [1, 0, 0], [[1, 0, 0], [1, 0, 0]], 2, "new"),
    ([[1, 0, 0]], [1, 0.1, 0], [[1, 0, 0], [1, 0, 0]], 2, "match"),
    ([[1, 0, 0], [0, 1, 0]], [1, 1, 0], [[1, 1, 0], [1, 1, 0]], 2, "ambiguous"),
    ([[1, 0, 0], [0, 1, 0]], [0, 0, 1], [[0, 0, 1], [0, 0, 1]], 2, "capacity"),
    ([], [1, 0, 0], [], 1, "insufficient_evidence"),
    ([], None, [], 0.5, "embedding_unavailable"),
    ([], [1, 0, 0], [None, [1, 0, 0]], 2, "half_embedding_unavailable"),
    ([], [1, 0, 0], [[1, 0, 0], [0, 1, 0]], 2, "half_disagreement"),
])
def test_trace_explains_abstention_and_never_changes_pcm_or_centroids(
    centers, vector, halves, seconds, reason,
):
    traces, results, registries = [], [], []
    original = audio([1, 1])
    original = replace(original, pcm=original.pcm[:int(seconds * 32000)],
                       end_sample=original.start_sample + int(seconds * 16000))
    for enabled in (False, True):
        tracker = SpeakerTracker(FixedExtractor([vector, *halves]), capacity=2)
        tracker.registry.centroids = [unit(center) for center in centers]
        tracker.registry.counts = [1] * len(centers)
        results.append(tracker.split(original, on_decision=traces.append if enabled else None))
        registries.append(tracker.registry)
    assert results[0] == results[1]
    assert b"".join(part.pcm for part, _ in results[1]) == original.pcm
    assert registries[0].counts == registries[1].counts
    for a, b in zip(registries[0].centroids, registries[1].centroids, strict=True):
        np.testing.assert_array_equal(a, b)
    trace, = traces
    assert trace["reason"] == reason
    assert trace["duration_s"] == seconds
    assert trace["counts_before"] == [1] * len(centers)
    assert trace["counts_after"] == registries[1].counts
    if reason == "new":
        assert all(m["reason"] == "insufficient_evidence" for m in trace["half_matches"])
    if reason == "match":
        assert all(m["label"] == "Speaker 1" for m in trace["half_matches"])
    if centers and vector is not None:
        assert trace["best"]["score"] == pytest.approx(max(unit(vector) @ unit(c) for c in centers))
    if reason == "match":
        assert trace["centroid_step_cosine"] < 1
    if reason.startswith("half_"):
        assert trace["registry_consulted"] is False
        assert trace["counts_before"] == trace["counts_after"]
    json.dumps(trace, allow_nan=False)


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("value", [0, 5])
def test_spawn_reports_decisions_even_without_text_and_leaves_me_alone(
    tmp_path, capsys, enabled, value,
):
    decisions = []
    worker = InferenceWorker(
        WorkerConfig(tmp_path, diarize_system=True, speaker_diagnostics=enabled),
        model_factory=fake_models, speaker_factory=fake_tracker,
        on_speaker_decision=decisions.append,
    )
    try:
        worker.start()
        assert worker.submit(audio([value, value]), speaker="System")
        wait_for(worker, lambda: worker.stats["completed"] == 1)
        assert worker.submit(phrase(), speaker="Me")
        worker.close()
    finally:
        worker.close(drain=False)
    output = capsys.readouterr().out
    assert ("Speaker decision: " in output) == enabled
    assert "Inference 1:" not in output
    assert "Me  HY:" in output
    assert "Speaker 1  HY:" not in output
    assert worker.stats["accepted"] == worker.stats["completed"] == 2
    assert not worker.session_dir.exists()
    if enabled:
        printed_line = next(line for line in output.splitlines()
                            if line.startswith("Speaker decision: "))
        compact = json.loads(printed_line.removeprefix("Speaker decision: "))
        assert "source" not in compact and "half_matches" in compact
        decision, = decisions
        assert decision["sequence"] == 1 and decision["source_label"] == "System"
        assert decision["reason"] == "new"
        assert decision["source"]["samples"] == 32000
        assert not ({"pcm", "armenian", "english", "embedding", "centroids"} & decision.keys())
    else:
        assert decisions == []


@pytest.mark.parametrize("main", [combined.main, system_audio.main])
def test_cli_rejects_speaker_diagnostics_without_diarization_before_opening_devices(main, capsys):
    with pytest.raises(SystemExit, match="2"):
        main(["--speaker-diagnostics"])
    assert "--speaker-diagnostics requires --diarize" in capsys.readouterr().err


def test_probe_counts_duplicate_ids_and_wrong_merges_separately_from_unknown():
    from scripts.check_speaker_decisions import measure

    class ExtractorWithCalls(SignExtractor):
        def embed(self, pcm):
            self.calls.append(pcm.tobytes())
            return super().embed(pcm)

    result = measure([("A", audio([1, 1])), ("A", audio([-2, -2])),
                      ("B", audio([1, 1]))], ExtractorWithCalls(), SpeakerTracker)
    assert result["unknown_s"] == 0
    assert result["false_new_ids"] == ["Speaker 2"]
    assert result["duplicate_identity_assigned_s"] == 2
    assert result["cross_speaker_assigned_s"] == 2


def test_offline_frozen_control_preserves_new_ids_but_undoes_only_match_updates():
    from scripts.check_speaker_decisions import FrozenRegistry

    registry = FrozenRegistry(0.47)
    assert registry.assign([1, 0, 0])["reason"] == "new"
    first = registry.centroids[0].copy()
    assert registry.assign([1, 0.5, 0])["reason"] == "match"
    np.testing.assert_array_equal(first, registry.centroids[0])
    assert registry.counts == [1]
    assert registry.assign([0, 0, 1])["label"] == "Speaker 2"
    assert registry.counts == [1, 1]


@pytest.mark.parametrize("experimental", [False, True])
def test_trial_short_new_voice_uses_only_current_utterance(experimental):
    tracker = SpeakerTracker(FixedExtractor([[0, 1], [0, 1], [0, 1]]),
                             experimental=experimental)
    tracker.registry.assign([1, 0])
    original = audio([1, 1])
    original = replace(original, pcm=original.pcm[:48640], end_sample=16000 + 24320)
    decisions = []
    parts = tracker.split(original, on_decision=decisions.append)
    assert parts[0][1] == ("Speaker 2" if experimental else "Unknown")
    assert tracker.registry.counts == ([1, 1] if experimental else [1])
    assert decisions[0]["probe_kind"] == ("overlapping_short_views" if experimental else None)


@pytest.mark.parametrize("mixed", [False, True])
def test_trial_anchor_requires_both_halves_to_match_full_identity_without_learning(mixed):
    halves = [[1, 0], [0, 1]] if mixed else [[0.64, 0.77], [0.64, -0.77]]
    tracker = SpeakerTracker(FixedExtractor([[1, 0], *halves]), experimental=True)
    tracker.registry.assign([1, 0])
    if mixed:
        tracker.registry.assign([0, 1])
    counts = list(tracker.registry.counts)
    centers = [c.copy() for c in tracker.registry.centroids]
    events = []
    parts = tracker.split(audio([1, 1]), on_decision=events.append)
    assert parts[0][1] == ("Unknown" if mixed else "Speaker 1")
    assert events[0]["reason"] == ("half_disagreement" if mixed else "anchored_match")
    assert tracker.registry.counts == counts
    for a, b in zip(centers, tracker.registry.centroids, strict=True):
        np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("main", [combined.main, system_audio.main])
def test_trial_flag_requires_diarization_before_capture(main, capsys):
    with pytest.raises(SystemExit, match="2"):
        main(["--experimental-speaker-matching"])
    assert "--experimental-speaker-matching requires --diarize" in capsys.readouterr().err


@pytest.mark.parametrize("samples,expected", [(23999, "Unknown"), (24000, "Speaker 1")])
def test_trial_enrollment_duration_boundary_and_pcm_preservation(samples, expected):
    tracker = SpeakerTracker(FixedExtractor([[1, 0], [1, 0], [1, 0]]), experimental=True)
    original = audio([1, 1])
    original = replace(original, pcm=original.pcm[:samples * 2], end_sample=16000 + samples)
    parts = tracker.split(original)
    assert parts[0][1] == expected
    assert b"".join(p.pcm for p, _ in parts) == original.pcm

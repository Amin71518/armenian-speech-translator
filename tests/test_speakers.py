import struct
from dataclasses import replace

import numpy as np

from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.speakers import Registry, SpeakerTracker
from tests.test_live_pipeline import fake_models, phrase


class SignExtractor:
    def embed(self, pcm):
        if len(pcm) < 16000:
            return None
        return np.array([1, 0] if pcm.mean() > 0 else [0, 1], dtype=np.float32)


def fake_tracker(config):
    return SpeakerTracker(SignExtractor())


def audio(values):
    pcm = b"".join(struct.pack("<h", value) * 16000 for value in values)
    return replace(phrase(), pcm=pcm, end_sample=16000 + len(pcm) // 2,
                   vad_end_sample=16000 + len(pcm) // 2, timeline_origin_s=9.5)


def test_split_before_asr_preserves_pcm_time_and_session_ids():
    tracker = fake_tracker(None)
    original = audio([1, 1, -2, -2, 1, 1])
    parts = tracker.split(original)
    assert [label for _, label in parts] == ["Speaker 1", "Speaker 2", "Speaker 1"]
    assert b"".join(part.pcm for part, _ in parts) == original.pcm
    assert [(p.start_sample, p.end_sample) for p, _ in parts] == [
        (16000, 48000), (48000, 80000), (80000, 112000)]
    assert all(p.origin_s == 9.5 and p.decision_monotonic == original.decision_monotonic
               for p, _ in parts)
    assert tracker.split(audio([-2, -2]))[0][1] == "Speaker 2"


def test_short_text_survives_and_mixed_cells_do_not_train():
    tracker = fake_tracker(None)
    assert tracker.split(audio([1]))[0][1] == "Unknown"
    assert tracker.registry.counts == []
    assert tracker.split(audio([1, -2]))[0][1] == "Unknown"
    assert tracker.registry.counts == []
    tracker.split(audio([1, 1]))
    assert tracker.split(audio([1]))[0][1] == "Speaker 1"
    assert tracker.registry.counts == [1]


def test_spawn_split_results_complete_one_job_and_do_not_rename_me(tmp_path, capsys):
    events = []
    worker = InferenceWorker(WorkerConfig(tmp_path, diarize_system=True),
                             model_factory=fake_models, speaker_factory=fake_tracker,
                             on_result=events.append)
    try:
        worker.start()
        assert worker.submit(audio([1, 1, -2, -2]), speaker="System")
        assert worker.submit(phrase(), speaker="Me")
        worker.close()
    finally:
        worker.close(drain=False)
    assert worker.stats["accepted"] == worker.stats["completed"] == 2
    assert worker.stats["result_parts"] == 3
    assert [e["speaker"] for e in events] == ["Speaker 1", "Speaker 2", "Me"]
    assert [e["last_part"] for e in events] == [False, True, True]
    assert worker.source_stats["System"]["completed"] == 1
    assert (tmp_path / "loads.txt").read_text().count("loaded") == 1
    output = capsys.readouterr().out
    assert "Speaker 1  HY:" in output and "Speaker 2  HY:" in output and "Me  HY:" in output


def test_missing_speaker_model_fails_startup_without_capture(tmp_path):
    import pytest

    worker = InferenceWorker(WorkerConfig(tmp_path, diarize_system=True),
                             model_factory=fake_models)
    with pytest.raises(RuntimeError, match="PROVENANCE"):
        worker.start()
    assert worker.closed


def test_unknown_does_not_mutate_registry_and_capacity_does_not_recycle_ids():
    registry = Registry(0.6, capacity=2)
    registry.assign([1, 0, 0])
    registry.assign([0, 1, 0])
    assert registry.assign([1, 1, 0])["reason"] == "ambiguous"
    assert registry.assign([0, 0, 1])["reason"] == "capacity"
    assert registry.assign([1, 0, 0], learn=False)["label"] == "Speaker 1"
    assert registry.counts == [1, 1]


class SlowExtractor:
    def embed(self, pcm):
        import time

        time.sleep(30)


def slow_tracker(config):
    return SpeakerTracker(SlowExtractor())


def test_shutdown_bounds_a_stalled_speaker_model(tmp_path):
    import time

    import pytest

    from tests.test_live_pipeline import wait_for

    worker = InferenceWorker(WorkerConfig(tmp_path, diarize_system=True), shutdown_timeout=0.2,
                             model_factory=fake_models, speaker_factory=slow_tracker)
    worker.start()
    try:
        worker.submit(audio([1, 1]), speaker="System")
        wait_for(worker, lambda: worker.stats["started"] == 1)
        before = time.perf_counter()
        with pytest.raises(RuntimeError, match="timed out"):
            worker.close()
        assert time.perf_counter() - before < 5
    finally:
        worker.close(drain=False)
    assert worker.stats["forced_termination"]
    assert worker.stats["discarded_on_shutdown"] == 1
    assert not worker.session_dir.exists()

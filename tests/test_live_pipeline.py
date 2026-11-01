import os
import struct
import time
import wave
from dataclasses import replace
from types import SimpleNamespace

import pytest

from armenian_speech.asr import Segment
from armenian_speech.live_pipeline import (
    InferenceJob,
    InferenceWorker,
    WorkerConfig,
    asr_fragment_reason,
    process_segment,
)
from armenian_speech.translation import ArmenianTranslator
from armenian_speech.vad import SpeechSegment


class FakeASR:
    def transcribe(self, path):
        with wave.open(str(path), "rb") as audio:
            assert (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) == (
                16000, 1, 2,
            )
            duration = audio.getnframes() / 16000
            mode = struct.unpack("<h", audio.readframes(1))[0]
        if mode == -1:
            raise RuntimeError("deliberate ASR failure")
        if mode == 2:
            time.sleep(30)
        if mode == 3:
            os._exit(7)
        text = {4: "bad", 5: "Հ։", 6: "…?!", 7: "ոչ"}.get(mode, "բարեւ")
        return ([] if mode == 0 else [Segment(0, duration, text)]), duration


class FakeTranslator:
    def __init__(self):
        self.count = 0

    def split_text(self, text):
        return [text]

    def translate(self, text):
        if text == "bad":
            raise ValueError("deliberate translation failure")
        self.count += 1
        return f"Hello {self.count}"


def fake_models(config):
    # Top-level factory/classes are intentionally pickled through real Windows spawn.
    with (config.cache_dir / "loads.txt").open("a") as stream:
        stream.write("loaded\n")
    return FakeASR(), FakeTranslator(), {"test_models": True}


class PausedTranslator(FakeTranslator):
    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def translate(self, text):
        (self.directory / "translating").touch()
        deadline = time.perf_counter() + 10
        while not (self.directory / "release").exists():
            if time.perf_counter() >= deadline:
                raise RuntimeError("Test translation was not released")
            time.sleep(0.01)
        return super().translate(text)


def paused_translation_models(config):
    return FakeASR(), PausedTranslator(config.cache_dir), {"test_models": True}


def failed_models(config):
    raise RuntimeError("deliberate startup failure")


def phrase(value=1, *, reason="silence"):
    return SpeechSegment(
        struct.pack("<h", value) * 160, 16000, 16160, 16000, 16160,
        time.perf_counter(), reason,
    )


def wait_for(worker, predicate, timeout=5):
    deadline = time.perf_counter() + timeout
    while not predicate():
        worker.poll()
        if time.perf_counter() >= deadline:
            raise AssertionError("Worker condition timed out")
        time.sleep(0.01)


@pytest.mark.parametrize("diagnostics", [False, True])
def test_spawned_worker_reuses_models_prints_me_and_cleans_wav(tmp_path, capsys, diagnostics):
    worker = InferenceWorker(
        WorkerConfig(tmp_path), model_factory=fake_models, diagnostics=diagnostics,
    )
    try:
        worker.start()
        assert worker.submit(phrase())
        wait_for(worker, lambda: worker.stats["completed"] == 1)
        assert worker.submit(phrase())
        worker.close()
        assert (tmp_path / "loads.txt").read_text() == "loaded\n"
        output = capsys.readouterr().out
        assert "[00:00:01] Me  HY: բարեւ  EN: Hello 1" in output
        assert "[00:00:01] Me  HY: բարեւ  EN: Hello 2" in output
        assert ("Inference 1:" in output) == diagnostics
        assert worker.stats["completed"] == worker.stats["accepted"] == 2
        assert worker.stats["discarded_on_shutdown"] == 0
        assert worker.stats["worker_exitcode"] == 0
        assert not worker.stats["forced_termination"]
        assert not worker.session_dir.exists()
    finally:
        worker.close(drain=False)


def test_hy_is_not_printed_until_translation_is_complete(tmp_path, capsys):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=paused_translation_models)
    try:
        worker.start()
        assert worker.submit(phrase())
        wait_for(worker, lambda: (tmp_path / "translating").exists())
        worker.poll()
        assert worker.stats["completed"] == 0
        assert "Me  HY:" not in capsys.readouterr().out
        (tmp_path / "release").touch()
        worker.close()
        lines = capsys.readouterr().out.splitlines()
        assert lines == ["[00:00:01] Me  HY: բարեւ  EN: Hello 1"]
    finally:
        (tmp_path / "release").touch()
        worker.close(drain=False)


def test_measurement_observer_runs_after_paired_print_and_marks_suppressed_results(
    tmp_path, capsys, monkeypatch,
):
    from armenian_speech import live_pipeline

    printed_at, events = [], []
    original = live_pipeline.print_segment

    def measured_print(*args):
        original(*args)
        time.sleep(0.02)  # Include terminal/flush delay in the observed endpoint.
        printed_at.append(time.perf_counter())

    monkeypatch.setattr(live_pipeline, "print_segment", measured_print)
    worker = InferenceWorker(
        WorkerConfig(tmp_path), model_factory=fake_models, on_result=events.append,
    )
    try:
        worker.start()
        worker.submit(phrase())
        wait_for(worker, lambda: worker.stats["completed"] == 1)
        worker.submit(phrase(value=5))
        worker.close()
        assert len(events) == 2 and len(printed_at) == 1
        assert events[0]["output_finished_monotonic"] >= printed_at[0]
        assert events[0]["printed"]
        assert events[1]["output_finished_monotonic"] is None
        assert not events[1]["printed"]
        assert "Me  HY: բարեւ  EN: Hello 1" in capsys.readouterr().out
    finally:
        worker.close(drain=False)


@pytest.mark.parametrize("text,reason", [
    ("Հ։", "single_letter"), ("Հ.", "single_letter"), ("հ", "single_letter"),
    ("  Հ՞!  ", "single_letter"), ("Հ\u200b", "single_letter"),
    ("…?!", "no_alphanumeric"), ("—", "no_alphanumeric"),
    ("այո", None), ("ոչ", None), ("ես", None), ("Գոռ", None),
    ("7", None), ("0", None), ("12.5", None),
    ("է", None), ("Է։", None), ("ա", None), ("և", None),
    ("Հ. Մարգարյան", None),
])
def test_fragment_guard_preserves_short_words_numbers_and_name_initials(text, reason):
    assert asr_fragment_reason(text) == reason


@pytest.mark.parametrize("text", ["Հ։", "Հ.", "…?!"])
def test_filtered_asr_never_calls_translator_and_removes_temporary_wav(tmp_path, text):
    class ASR:
        def transcribe(self, path):
            assert path.is_file()
            return [Segment(0, 0.01, text)], 0.01

    class Translator:
        def split_text(self, text):
            raise AssertionError("Filtered input must not reach the translation tokenizer")

        def translate(self, text):
            raise AssertionError("Filtered input must not reach translation")

    path = tmp_path / "segment.wav"
    result = process_segment(InferenceJob(1, phrase(), 1), ASR(), Translator(), path, 2)
    assert result["skip_reason"] is not None
    assert result["armenian"] == result["english"] == ""
    assert result["translation_parts"] == 0
    assert not path.exists()


@pytest.mark.parametrize("diagnostics", [False, True])
def test_spawned_worker_skips_fragments_counts_completion_and_keeps_short_reply(
    tmp_path, capsys, diagnostics,
):
    worker = InferenceWorker(
        WorkerConfig(tmp_path), model_factory=fake_models, diagnostics=diagnostics,
    )
    try:
        worker.start()
        for completed, value in enumerate((5, 6, 7), start=1):
            assert worker.submit(phrase(value=value))
            wait_for(worker, lambda expected=completed: worker.stats["completed"] == expected)
            if value in (5, 6):
                assert worker.stats["max_decision_to_output_s"] == 0
        worker.close()
        assert worker.stats["filtered_asr_fragments"] == 2
        assert worker.stats["empty_asr"] == 0
        assert worker.stats["accepted"] == worker.stats["completed"] == 3
        assert worker.stats["translation_parts"] == 1
        assert worker.stats["discarded_on_shutdown"] == 0
        assert worker.stats["worker_exitcode"] == 0
        assert not worker.session_dir.exists()
        output = capsys.readouterr().out
        assert [line for line in output.splitlines() if "Me  HY:" in line] == [
            "[00:00:01] Me  HY: ոչ  EN: Hello 1",
        ]
        assert ("skipped ASR fragment" in output) == diagnostics
    finally:
        worker.close(drain=False)


def test_fragment_guard_can_be_disabled_in_spawned_worker(tmp_path, capsys):
    worker = InferenceWorker(
        WorkerConfig(tmp_path, filter_asr_fragments=False), model_factory=fake_models,
    )
    try:
        worker.start()
        assert worker.submit(phrase(value=5))
        worker.close()
        assert worker.stats["filtered_asr_fragments"] == 0
        assert worker.stats["translation_parts"] == 1
        assert "Me  HY: Հ։  EN: Hello 1" in capsys.readouterr().out
    finally:
        worker.close(drain=False)


def test_system_label_does_not_change_default_microphone_output(tmp_path, capsys):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=fake_models, speaker="System")
    try:
        worker.start()
        worker.submit(phrase())
        worker.close()
        output = capsys.readouterr().out
        assert "System  HY: բարեւ  EN: Hello 1" in output
        assert "Me  HY:" not in output
    finally:
        worker.close(drain=False)


def test_one_spawned_worker_retains_source_per_job(tmp_path, capsys):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=fake_models)
    try:
        worker.start()
        worker.submit(phrase(), speaker="System")
        wait_for(worker, lambda: worker.stats["completed"] == 1)
        worker.submit(phrase(), speaker="Me")
        worker.close()
        output = capsys.readouterr().out
        assert "System  HY: բարեւ  EN: Hello 1" in output
        assert "Me  HY: բարեւ  EN: Hello 2" in output
        assert (tmp_path / "loads.txt").read_text() == "loaded\n"
        assert worker.summary()["sources"]["System"]["completed"] == 1
        assert worker.summary()["sources"]["Me"]["completed"] == 1
    finally:
        worker.close(drain=False)


def test_empty_asr_and_gap_phrases_have_explicit_counters(tmp_path, capsys):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=fake_models)
    try:
        worker.start()
        assert not worker.submit(phrase(reason="gap"))
        assert worker.submit(phrase(value=0))
        worker.close()
        assert worker.stats["empty_asr"] == worker.stats["skipped_gap"] == 1
        assert worker.stats["translation_parts"] == 0
        output = capsys.readouterr()
        assert "skipped incomplete gap" in output.err
        assert "Me  HY:" not in output.out
    finally:
        worker.close(drain=False)


@pytest.mark.parametrize("capacity", [1, 2])
def test_slow_consumer_queue_full_does_not_wait_and_shutdown_is_bounded(
    tmp_path, capsys, capacity,
):
    worker = InferenceWorker(
        WorkerConfig(tmp_path), capacity=capacity, shutdown_timeout=0.2, model_factory=fake_models,
    )
    try:
        worker.start()
        assert worker.submit(phrase(value=2))
        wait_for(worker, lambda: worker.stats["started"] == 1)
        for _ in range(capacity):
            assert worker.submit(phrase())
        before = time.perf_counter()
        assert not worker.submit(phrase(value=0))
        assert time.perf_counter() - before < 0.2
        assert worker.stats["peak_queue_depth"] <= capacity
        assert worker.stats["dropped_full"] == 1
        before = time.perf_counter()
        with pytest.raises(RuntimeError, match="shutdown timed out"):
            worker.close()
        assert time.perf_counter() - before < 5
        assert worker.closed and worker.stats["forced_termination"]
        assert worker.stats["discarded_on_shutdown"] == capacity + 1
        assert not worker.session_dir.exists()
        assert "queue full" in capsys.readouterr().err
    finally:
        worker.close(drain=False)


@pytest.mark.parametrize("mode, message", [(-1, "deliberate ASR failure"),
                                          (4, "deliberate translation failure")])
def test_worker_failure_is_propagated_and_temp_audio_removed(tmp_path, mode, message):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=fake_models)
    try:
        worker.start()
        worker.submit(phrase(value=mode))
        with pytest.raises(RuntimeError, match=message):
            worker.close()
        assert worker.closed
        assert worker.stats["discarded_on_shutdown"] == 1
        assert not worker.session_dir.exists()
    finally:
        worker.close(drain=False)


def test_native_process_exit_is_detected_without_waiting_for_a_result(tmp_path):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=fake_models)
    try:
        worker.start()
        worker.submit(phrase(value=3))
        with pytest.raises(RuntimeError, match="exited unexpectedly: 7"):
            worker.close()
        assert worker.closed and worker.stats["worker_exitcode"] == 7
        assert not worker.session_dir.exists()
    finally:
        worker.close(drain=False)


def test_startup_failure_is_propagated_before_capture(tmp_path):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=failed_models)
    with pytest.raises(RuntimeError, match="deliberate startup failure"):
        worker.start()
    assert worker.closed and not worker.session_dir.exists()


def test_invalid_pcm_is_not_enqueued(tmp_path):
    worker = InferenceWorker(WorkerConfig(tmp_path), model_factory=fake_models)
    try:
        worker.start()
        with pytest.raises(ValueError, match="PCM length"):
            worker.submit(replace(phrase(), end_sample=99999))
        with pytest.raises(ValueError, match="192000"):
            worker.submit(replace(phrase(), pcm=b"\x00"))
        assert worker.stats["accepted"] == 0
    finally:
        worker.close()


class WordTokenizer:
    model_max_length = 1024

    def __call__(self, text, **kwargs):
        assert kwargs["truncation"] is False
        return {"input_ids": [0] * (2 + sum(len(word) for word in text.split()))}


def translator_without_loading():
    translator = ArmenianTranslator.__new__(ArmenianTranslator)
    translator.tokenizer = WordTokenizer()
    translator.model = SimpleNamespace(config=SimpleNamespace(max_position_embeddings=1024))
    return translator


def test_token_splitting_accounts_for_special_tokens_and_loses_no_words():
    translator = translator_without_loading()
    text = " ".join(["բարեւ," * 2] * 200)
    parts = translator.split_text(text)
    assert len(parts) > 1
    assert " ".join(parts).split() == text.split()
    assert all(
        len(translator.tokenizer(part, truncation=False)["input_ids"]) <= 512 for part in parts
    )
    assert translator.split_text("ա" * 510) == ["ա" * 510]
    assert translator.split_text("   ") == []


def test_single_oversized_word_fails_without_truncation():
    with pytest.raises(ValueError, match="single word"):
        translator_without_loading().split_text("ա" * 511)

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from armenian_speech.asr import ArmenianASR, Segment
from armenian_speech.asr_onnx import OnnxArmenianASR
from armenian_speech.benchmark import evaluate
from tests.test_experiment import make_wav


def test_onnx_adapter_cpu_configuration_and_file_bounds(tmp_path, monkeypatch):
    calls = {}

    def load_model(*args, **kwargs):
        calls.update(kwargs)
        assert args == ("nemo-conformer-rnnt", str(tmp_path))
        return SimpleNamespace(recognize=lambda _: " բարև ")

    monkeypatch.setitem(sys.modules, "onnx_asr", SimpleNamespace(load_model=load_model))
    (tmp_path / "PROVENANCE.json").write_text(json.dumps({"revision": "test"}))
    wav = tmp_path / "sample.wav"
    make_wav(wav)
    asr = OnnxArmenianASR(tmp_path, 4)
    segments, duration = asr.transcribe(wav)
    assert calls["providers"] == ["CPUExecutionProvider"]
    assert calls["quantization"] == "int8"
    assert calls["sess_options"].intra_op_num_threads == 4
    assert segments == [Segment(0, 0.01, "բարև")]
    assert duration == 0.01
    asr.model = SimpleNamespace(recognize=lambda _: "")
    assert asr.transcribe(wav) == ([], 0.01)


def test_asr_benchmark_scores_corpus_and_excludes_output_from_time(monkeypatch):
    class ASR:
        def transcribe(self, path):
            return [Segment(0, 2, "ա" if path.name == "a.wav" else "բ գ")], 2.0

    rows = [
        {"path": Path("a.wav"), "reference_hy": "ա"},
        {"path": Path("b.wav"), "reference_hy": "բ գ դ"},
    ]
    ticks = iter([0, 1, 2, 5])
    monkeypatch.setattr("armenian_speech.benchmark.perf_counter", lambda: next(ticks))
    result = evaluate(ASR(), rows)
    assert result["summary"]["mean_asr_s"] == 2
    assert result["summary"]["max_asr_s"] == 3
    assert result["summary"]["rtf"] == 1
    assert result["summary"]["wer"] == pytest.approx(0.25)


def test_whisper_explicit_language_task_temperature_and_lazy_consumption(monkeypatch):
    calls, consumed = {}, []

    class Model:
        def __init__(self, *args, **kwargs):
            assert kwargs["device"] == "cpu"
            assert kwargs["compute_type"] == "int8"

        def transcribe(self, *args, **kwargs):
            calls.update(kwargs)

            def segments():
                consumed.append(True)
                yield Segment(0, 1, " բարև ")

            return segments(), SimpleNamespace(duration=1.0)

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    asr = ArmenianASR("base", Path("unused"), 4, True, temperature=0.0)
    assert asr.transcribe(Path("unused.wav")) == ([Segment(0, 1, "բարև")], 1.0)
    assert consumed == [True]
    assert calls["language"] == "hy"
    assert calls["task"] == "transcribe"
    assert calls["temperature"] == 0.0
    assert calls["vad_filter"] is False

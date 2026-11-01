import io
import json
import struct
import wave
from pathlib import Path

import pytest

from armenian_speech.asr import Segment
from armenian_speech.cli import main, read_manifest
from armenian_speech.metrics import error_rates, normalize_text
from armenian_speech.output import timestamp
from armenian_speech.pipeline import process_wav
from scripts.prepare_samples import pcm_wav


def make_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * 160)


def test_armenian_punctuation_normalization():
    assert normalize_text("  Բարև,   ինչպե՞ս ես։ ") == "բարեւ ինչպես ես"


def test_corpus_error_rates_are_weighted_by_reference_length():
    scores = error_rates(["ա", "բ գ դ ե"], ["սխալ", "բ գ դ ե"])
    assert scores["wer"] == pytest.approx(1 / 5)


def test_missing_speech_counts_as_deletions():
    assert error_rates(["բարեւ աշխարհ"], [""]) == {"wer": 1.0, "cer": 1.0}


def test_empty_reference_is_rejected():
    with pytest.raises(ValueError, match="letters or numbers"):
        error_rates(["։"], ["բարեւ"])


def test_manifest_paths_are_relative_to_manifest(tmp_path):
    audio = tmp_path / "sample.wav"
    make_wav(audio)
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps({"audio": audio.name, "reference_hy": "բարեւ"}), encoding="utf-8",
    )
    assert read_manifest(manifest)[0]["path"] == audio.resolve()


def test_bad_manifest_fails_before_loading_models(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text('{"audio": "missing.wav", "reference_hy": ""}', encoding="utf-8")
    assert main(["--manifest", str(manifest)]) == 1


def test_pipeline_translates_each_segment_and_handles_empty_asr(capsys):
    class ASR:
        def __init__(self, segments):
            self.segments = segments

        def transcribe(self, _):
            return self.segments, 4.0

    class Translation:
        def __init__(self):
            self.seen = []

        def translate(self, text):
            self.seen.append(text)
            return "Hello"

    translator = Translation()
    result = process_wav(Path("unused.wav"), ASR([Segment(1, 2, "բարեւ")]), translator)
    assert translator.seen == ["բարեւ"]
    assert result["text"] == "բարեւ"
    assert result["rtf"] == result["elapsed_s"] / 4
    assert "[00:00:01] WAV  HY: բարեւ  EN: Hello" in capsys.readouterr().out
    empty = process_wav(Path("unused.wav"), ASR([]), translator)
    assert empty["text"] == ""
    assert translator.seen == ["բարեւ"]


def test_timestamp():
    assert timestamp(3672.9) == "01:01:12"


def test_float_wav_is_converted_to_pcm16():
    samples = struct.pack("<4f", 0.0, 0.5, -0.5, 0.0)
    fmt = struct.pack("<HHIIHH", 3, 1, 16_000, 64_000, 4, 32)
    payload = b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt
    payload += b"data" + struct.pack("<I", len(samples)) + samples
    source = b"RIFF" + struct.pack("<I", len(payload)) + payload
    normalized = pcm_wav(source)
    with wave.open(io.BytesIO(normalized), "rb") as wav:
        assert wav.getframerate() == 16_000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() == 4
        assert struct.unpack("<4h", wav.readframes(4)) == (0, 16_384, -16_384, 0)


def test_pipeline_timers_include_model_work_and_output(monkeypatch, capsys):
    class ASR:
        def transcribe(self, _):
            return [Segment(0, 1, "բարեւ")], 4.0

    class Translation:
        def translate(self, _):
            return "Hello"

    times = iter([0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0])
    monkeypatch.setattr("armenian_speech.pipeline.perf_counter", lambda: next(times))
    result = process_wav(Path("unused.wav"), ASR(), Translation())
    assert result["asr_s"] == 2
    assert result["translation_s"] == 1
    assert result["output_s"] == 1
    assert result["elapsed_s"] == 8
    assert result["rtf"] == 2

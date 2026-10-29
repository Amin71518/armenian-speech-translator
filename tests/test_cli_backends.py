import json

from armenian_speech.asr import Segment
from armenian_speech.cli import main, parser
from tests.test_experiment import make_wav


def test_default_cli_backend_is_onnx():
    args = parser().parse_args(["--wav", "sample.wav"])
    assert args.asr_backend == "onnx"
    assert args.asr_model is None


def test_cli_loads_onnx_and_translation_once_for_multiple_files(tmp_path, monkeypatch, capsys):
    calls = {"asr_loads": 0, "translation_loads": 0, "translations": []}
    directory = tmp_path / "models" / "vana"
    directory.mkdir(parents=True)
    (directory / "PROVENANCE.json").write_text("{}")
    manifest = tmp_path / "manifest.jsonl"
    rows = []
    for name in ("one.wav", "two.wav"):
        make_wav(tmp_path / name)
        rows.append({"audio": name, "reference_hy": "բարև"})
    manifest.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    class ASR:
        provenance = {"repo": "Vana-Labs/stt-fastconformer-armenian", "revision": "test"}

        def __init__(self, path, threads):
            assert path == directory
            calls["asr_loads"] += 1

        def transcribe(self, path):
            return [Segment(0, 0.01, "բարև")], 0.01

    class Translation:
        def __init__(self, model, cache, threads, offline):
            assert model == "Helsinki-NLP/opus-mt-hy-en"
            assert offline
            calls["translation_loads"] += 1

        def translate(self, text):
            calls["translations"].append(text)
            return "Hello"

    def forbidden_whisper(*args, **kwargs):
        raise AssertionError("Default ONNX pipeline must not load Whisper")

    monkeypatch.setattr("armenian_speech.asr_onnx.OnnxArmenianASR", ASR)
    monkeypatch.setattr("armenian_speech.translation.ArmenianTranslator", Translation)
    monkeypatch.setattr("armenian_speech.asr.ArmenianASR", forbidden_whisper)
    report = tmp_path / "report.json"
    assert main([
        "--manifest", str(manifest), "--cache-dir", str(directory.parent),
        "--offline", "--report", str(report),
    ]) == 0
    assert calls == {"asr_loads": 1, "translation_loads": 1, "translations": ["բարև", "բարև"]}
    assert capsys.readouterr().out.count("[00:00:00] WAV  HY: բարև  EN: Hello") == 2
    saved = json.loads(report.read_text(encoding="utf-8"))
    assert saved["asr_backend"] == "onnx"
    assert saved["asr_revision"] == "test"
    assert saved["asr_decoder"] == "rnnt_greedy"
    assert saved["asr_temperature"] is None
    assert all("text" not in row for row in saved["samples"])


def test_missing_onnx_model_fails_without_whisper_fallback(tmp_path, monkeypatch, capsys):
    audio = tmp_path / "sample.wav"
    make_wav(audio)

    def forbidden_model(*args, **kwargs):
        raise AssertionError("Missing ONNX artifacts must not trigger another model")

    monkeypatch.setattr("armenian_speech.asr.ArmenianASR", forbidden_model)
    monkeypatch.setattr("armenian_speech.translation.ArmenianTranslator", forbidden_model)
    assert main(["--wav", str(audio), "--cache-dir", str(tmp_path / "missing")]) == 1
    assert "scripts/download_asr.py" in capsys.readouterr().err


def test_explicit_whisper_backend_reaches_whisper(tmp_path, monkeypatch):
    audio = tmp_path / "sample.wav"
    make_wav(audio)
    selected = []

    def unavailable_whisper(model, cache, threads, offline):
        selected.append(model)
        raise RuntimeError("Intentional test failure")

    monkeypatch.setattr("armenian_speech.asr.ArmenianASR", unavailable_whisper)
    assert main(["--wav", str(audio), "--asr-backend", "whisper", "--offline"]) == 1
    assert selected == ["base"]

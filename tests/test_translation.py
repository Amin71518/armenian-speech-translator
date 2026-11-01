import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from armenian_speech.translation import DEFAULT_TRANSLATION_MODEL, NLLB_REVISION, ArmenianTranslator


def test_translation_language_controls_limits_and_empty_input(monkeypatch):
    import torch

    def local_snapshot(*args, **kwargs):
        assert args == (DEFAULT_TRANSLATION_MODEL,)
        assert kwargs["local_files_only"] is True
        assert kwargs["revision"] == NLLB_REVISION
        return "unused/pinned-snapshot"

    monkeypatch.setattr("huggingface_hub.snapshot_download", local_snapshot)
    calls = []

    class Tokenizer:
        eos_token_id = 2
        model_max_length = 1024

        def __init__(self, **kwargs):
            self.src_lang = kwargs.get("src_lang")
            assert self.src_lang == "hye_Armn"
            assert kwargs["local_files_only"]

        def convert_tokens_to_ids(self, token):
            assert token == "eng_Latn"
            return 77

        def __call__(self, text, **kwargs):
            assert kwargs["truncation"] is False
            return {"input_ids": torch.zeros((1, len(text.split())), dtype=torch.long)}

        def decode(self, tokens, **kwargs):
            return "Hello"

    class Model:
        config = SimpleNamespace(max_position_embeddings=1024, _commit_hash="revision")

        def to(self, device):
            assert device == "cpu"
            return self

        def eval(self):
            return self

        def generate(self, **kwargs):
            calls.append(kwargs)
            return torch.tensor([[0, 77, 2]])

    def tokenizer_from_pretrained(model_source, **kwargs):
        assert model_source == "unused/pinned-snapshot"
        return Tokenizer(**kwargs)

    tokenizer_class = SimpleNamespace(from_pretrained=tokenizer_from_pretrained)
    model_class = SimpleNamespace(from_pretrained=lambda *a, **kw: Model())
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoTokenizer=tokenizer_class, AutoModelForSeq2SeqLM=model_class,
    ))
    translator = ArmenianTranslator(Path("unused"), 4, True)
    assert translator.translate("   ") == ""
    assert not calls
    assert translator.translate("բարև") == "Hello"
    assert calls[0]["do_sample"] is False
    assert calls[0]["num_beams"] == 1
    assert calls[0]["forced_bos_token_id"] == 77
    with pytest.raises(ValueError, match="exceeds"):
        translator.translate("ա " * 513)
    assert len(calls) == 1

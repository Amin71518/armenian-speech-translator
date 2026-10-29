"""Explicit local HY -> EN translation; no automatic model fallback."""

from pathlib import Path

NLLB_REVISION = "f8d333a098d19b4fd9a8b18f94170487ad3f821d"
M2M100_REVISION = "55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636"
DEFAULT_TRANSLATION_MODEL = "facebook/nllb-200-distilled-600M"

SUPPORTED_TRANSLATION_MODELS = (
    "Helsinki-NLP/opus-mt-hy-en",
    "facebook/nllb-200-distilled-600M",
    "facebook/m2m100_418M",
)


class ArmenianTranslator:
    def __init__(self, model: str, cache: Path, threads: int, offline: bool) -> None:
        if model not in SUPPORTED_TRANSLATION_MODELS:
            raise ValueError(f"Unsupported translation model: {model}")
        import torch
        from transformers import (
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
            MarianMTModel,
            MarianTokenizer,
        )

        torch.set_num_threads(threads)
        self.torch = torch
        options = {"cache_dir": str(cache / "translation"), "local_files_only": offline}
        self.generation_options = {"num_beams": 1}
        revision = None
        source = model
        if model.startswith("facebook/"):
            from huggingface_hub import snapshot_download

            # Use prepared local files, including the tokenizer. Transformers 4.57.6
            # can otherwise query model_info even with local_files_only=True.
            source = snapshot_download(
                model, cache_dir=str(cache / "translation"), local_files_only=True,
                revision=NLLB_REVISION if model.endswith("600M") else M2M100_REVISION,
            )
            revision = Path(source).name
        if model == "facebook/nllb-200-distilled-600M":
            self.tokenizer = AutoTokenizer.from_pretrained(source, src_lang="hye_Armn", **options)
            self.generation_options["forced_bos_token_id"] = self.tokenizer.convert_tokens_to_ids(
                "eng_Latn",
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(source, **options)
        elif model == "facebook/m2m100_418M":
            self.tokenizer = AutoTokenizer.from_pretrained(source, src_lang="hy", **options)
            self.generation_options["forced_bos_token_id"] = self.tokenizer.get_lang_id("en")
            self.model = AutoModelForSeq2SeqLM.from_pretrained(source, **options)
        else:
            self.tokenizer = MarianTokenizer.from_pretrained(model, **options)
            self.model = MarianMTModel.from_pretrained(model, **options)
        self.model = self.model.to("cpu").eval()
        self.revision = revision or getattr(self.model.config, "_commit_hash", None)

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=False)
        limit = min(self.model.config.max_position_embeddings, self.tokenizer.model_max_length)
        # NLLB was trained on inputs up to 512 tokens, despite its larger positional capacity.
        if getattr(self.tokenizer, "src_lang", None) == "hye_Armn":
            limit = min(limit, 512)
        if inputs["input_ids"].shape[-1] > limit:
            raise ValueError(f"Translation input exceeds {limit} tokens; split the phrase.")
        with self.torch.inference_mode():
            tokens = self.model.generate(
                **inputs, max_new_tokens=256, do_sample=False,
                **self.generation_options,
            )
        if tokens[0, -1].item() != self.tokenizer.eos_token_id:
            raise ValueError("Translation reached its output limit without EOS.")
        return self.tokenizer.decode(tokens[0], skip_special_tokens=True).strip()

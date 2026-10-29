"""Explicit HY -> EN Marian adapter. Inference always runs locally on CPU."""

from pathlib import Path


class ArmenianTranslator:
    def __init__(self, model: str, cache: Path, threads: int, offline: bool) -> None:
        import torch
        from transformers import MarianMTModel, MarianTokenizer

        torch.set_num_threads(threads)
        self.torch = torch
        options = {"cache_dir": str(cache / "translation"), "local_files_only": offline}
        self.tokenizer = MarianTokenizer.from_pretrained(model, **options)
        self.model = MarianMTModel.from_pretrained(model, **options).to("cpu").eval()

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=False)
        limit = self.model.config.max_position_embeddings
        if inputs["input_ids"].shape[-1] > limit:
            raise ValueError(f"Translation input exceeds {limit} tokens; split the phrase.")
        with self.torch.inference_mode():
            tokens = self.model.generate(**inputs, num_beams=1, max_new_tokens=256)
        if tokens[0, -1].item() != self.tokenizer.eos_token_id:
            raise ValueError("Translation reached its output limit without EOS.")
        return self.tokenizer.decode(tokens[0], skip_special_tokens=True).strip()

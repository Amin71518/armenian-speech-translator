"""Local NLLB HY -> EN translation with greedy decoding."""

import re
from pathlib import Path

NLLB_REVISION = "f8d333a098d19b4fd9a8b18f94170487ad3f821d"
DEFAULT_TRANSLATION_MODEL = "facebook/nllb-200-distilled-600M"


class ArmenianTranslator:
    def __init__(self, cache: Path, threads: int, offline: bool) -> None:
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        torch.set_num_threads(threads)
        self.torch = torch
        options = {"cache_dir": str(cache / "translation"), "local_files_only": offline}
        # Use prepared local files, including the tokenizer. Transformers 4.57.6
        # can otherwise query model_info even with local_files_only=True.
        source = snapshot_download(
            DEFAULT_TRANSLATION_MODEL, cache_dir=str(cache / "translation"), local_files_only=True,
            revision=NLLB_REVISION,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(source, src_lang="hye_Armn", **options)
        self.generation_options = {
            "num_beams": 1,
            "forced_bos_token_id": self.tokenizer.convert_tokens_to_ids("eng_Latn"),
        }
        self.model = AutoModelForSeq2SeqLM.from_pretrained(source, **options)
        self.model = self.model.to("cpu").eval()
        self.revision = Path(source).name

    def split_text(self, text: str) -> list[str]:
        """Live-only word-boundary splitting; translate() keeps its WAV contract."""
        text = text.strip()
        if not text:
            return []
        limit = min(self.model.config.max_position_embeddings, self.tokenizer.model_max_length, 512)

        def size(value: str) -> int:
            return len(self.tokenizer(value, truncation=False)["input_ids"])

        if size(text) <= limit:
            return [text]
        result, current = [], ""
        for word in re.findall(r"\S+\s*", text):
            candidate = current + word
            if size(candidate.strip()) <= limit:
                current = candidate
                continue
            if current:
                result.append(current.strip())
            if size(word.strip()) > limit:
                raise ValueError(f"A single word exceeds {limit} NLLB tokens; cannot split safely.")
            current = word
        if current:
            result.append(current.strip())
        return result

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=False)
        # NLLB was trained on inputs up to 512 tokens, despite its larger positional capacity.
        limit = min(self.model.config.max_position_embeddings, self.tokenizer.model_max_length, 512)
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

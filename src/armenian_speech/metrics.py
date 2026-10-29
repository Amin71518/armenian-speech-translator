"""Reproducible ASR scoring and sampled process memory (including native models)."""

import threading
import unicodedata


def normalize_text(text: str) -> str:
    """NFC, casefold, remove punctuation, collapse whitespace; keep Armenian letters."""
    text = unicodedata.normalize("NFC", text).casefold()
    return " ".join(
        "".join(char for char in text if not unicodedata.category(char).startswith("P"))
        .split()
    )


def error_rates(references: list[str], hypotheses: list[str]) -> dict[str, float]:
    import jiwer

    if len(references) != len(hypotheses) or not references:
        raise ValueError("Scoring needs nonempty aligned reference and hypothesis lists.")
    refs = [normalize_text(text) for text in references]
    hyps = [normalize_text(text) for text in hypotheses]
    if not all(refs):
        raise ValueError("Reference text must contain letters or numbers.")
    return {"wer": jiwer.wer(refs, hyps), "cer": jiwer.cer(refs, hyps)}


class MemorySampler:
    """Sample process RSS every 50 ms. This is a sampled maximum, not exact peak RAM."""

    def __init__(self) -> None:
        import psutil

        self.process = psutil.Process()
        self.peak_bytes = 0
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _read(self) -> None:
        self.peak_bytes = max(self.peak_bytes, self.process.memory_info().rss)

    def _sample(self) -> None:
        while not self.stop.wait(0.05):
            self._read()

    def __enter__(self) -> "MemorySampler":
        self._read()
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop.set()
        self.thread.join()
        self._read()

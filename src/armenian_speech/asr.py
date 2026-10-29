"""CPU Whisper adapter; no language detection or automatic model fallback."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


class ArmenianASR:
    def __init__(
        self, model: str, cache: Path, threads: int, offline: bool,
        temperature: float | tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    ) -> None:
        from faster_whisper import WhisperModel

        self.temperature = temperature
        self.model = WhisperModel(
            model,
            device="cpu",
            compute_type="int8",
            cpu_threads=threads,
            download_root=str(cache / "whisper"),
            local_files_only=offline,
        )

    def transcribe(self, path: Path) -> tuple[list[Segment], float]:
        segments, info = self.model.transcribe(
            str(path), language="hy", task="transcribe", beam_size=1,
            condition_on_previous_text=False, vad_filter=False, temperature=self.temperature,
        )
        # faster-whisper is lazy: exhaust the generator inside the timed operation.
        return [Segment(s.start, s.end, s.text.strip()) for s in segments], info.duration

"""Sequential WAV experiment. The live queue belongs to stage 2."""

from pathlib import Path
from time import perf_counter
from typing import Protocol

from armenian_speech.asr import Segment
from armenian_speech.output import print_segment


class Transcriber(Protocol):
    def transcribe(self, path: Path) -> tuple[list[Segment], float]: ...


class Translator(Protocol):
    def translate(self, text: str) -> str: ...


def process_wav(path: Path, asr: Transcriber, translator: Translator) -> dict:
    started = perf_counter()
    segments, duration = asr.transcribe(path)
    asr_s = perf_counter() - started
    if duration <= 0:
        raise ValueError(f"Empty audio: {path}")
    translation_s = 0.0
    output_s = 0.0
    for segment in segments:
        before = perf_counter()
        english = translator.translate(segment.text)
        translation_s += perf_counter() - before
        before = perf_counter()
        print_segment(segment.start, "WAV", segment.text, english)
        output_s += perf_counter() - before
    elapsed = perf_counter() - started
    return {
        "duration_s": duration,
        "asr_s": asr_s,
        "translation_s": translation_s,
        "output_s": output_s,
        "elapsed_s": elapsed,
        "rtf": elapsed / duration,
        "text": " ".join(segment.text for segment in segments),
    }

"""Shared ASR result used by the ONNX adapter and WAV pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str

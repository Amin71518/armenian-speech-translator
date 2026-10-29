"""Terminal formatting shared by the WAV experiment and future live pipeline."""

import math


def timestamp(seconds: float) -> str:
    value = max(0, math.floor(seconds))
    hours, rest = divmod(value, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def print_segment(start: float, speaker: str, armenian: str, english: str) -> None:
    print(f"[{timestamp(start)}] {speaker}  HY: {armenian}  EN: {english}", flush=True)

"""Pinned CPU Silero inference and bounded, sample-indexed speech segmentation."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
WINDOW_SAMPLES = 512
VAD_VERSION = "6.2.3"
WHEEL_SHA256 = "7b7f5436cfcb02fae583a05b512ea96467fd449fe54cb49a5e4f06c51a1e43b8"
MODEL_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"


class SileroVAD:
    """The upstream ONNX contract: 512 samples plus 64 context samples at 16 kHz.

    State/context stay local to one audio stream. No Torch, downloads or fallback.
    See Silero's MIT-licensed OnnxWrapper for the published tensor contract.
    """

    def __init__(self, directory: Path) -> None:
        import onnxruntime as ort

        model = directory / "silero_vad.onnx"
        if not model.is_file() or not (directory / "PROVENANCE.json").is_file():
            raise FileNotFoundError(
                "Prepared VAD missing. Run: poetry run python scripts/download_vad.py"
            )
        provenance = json.loads((directory / "PROVENANCE.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(model.read_bytes()).hexdigest()
        if (provenance.get("version"), provenance.get("wheel_sha256"), digest) != (
            VAD_VERSION, WHEEL_SHA256, MODEL_SHA256,
        ):
            raise ValueError("VAD checksum/provenance mismatch; prepare the pinned model again.")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(model), sess_options=options, providers=["CPUExecutionProvider"],
        )
        self.reset()

    def reset(self) -> None:
        self._memory = np.zeros((2, 1, 128), dtype=np.float32)
        self._history = np.zeros((1, 64), dtype=np.float32)

    def probability(self, samples: np.ndarray) -> float:
        if samples.shape != (WINDOW_SAMPLES,) or samples.dtype != np.float32:
            raise ValueError("VAD requires exactly 512 mono float32 samples at 16 kHz.")
        if not np.isfinite(samples).all() or np.max(np.abs(samples)) > 1:
            raise ValueError("VAD samples must be finite and normalized to [-1, 1].")
        context = np.concatenate((self._history, samples.reshape(1, -1)), axis=1)
        scores, memory = self.session.run(
            ["output", "stateN"],
            {"input": context, "state": self._memory,
             "sr": np.asarray(SAMPLE_RATE, dtype=np.int64)},
        )
        result = float(scores[0, 0])
        if not math.isfinite(result) or not 0 <= result <= 1:
            raise RuntimeError("VAD returned an invalid probability.")
        self._memory = memory
        self._history = context[:, -64:].copy()
        return result


@dataclass(frozen=True)
class VADConfig:
    start_threshold: float = 0.65
    continue_threshold: float = 0.50
    pre_roll_ms: int = 300
    min_speech_ms: int = 300
    confirmation_ms: int = 160
    min_rms_db: float | None = None
    silence_ms: int = 600
    trailing_ms: int = 100
    target_segment_s: float = 3.5
    split_silence_ms: int = 256
    max_segment_s: float = 6.0

    def __post_init__(self) -> None:
        if not 0 < self.continue_threshold <= self.start_threshold < 1:
            raise ValueError("VAD thresholds must satisfy 0 < continue <= start < 1.")
        if min(self.pre_roll_ms, self.trailing_ms) < 0 or self.min_speech_ms <= 0:
            raise ValueError("Invalid VAD padding or minimum speech duration.")
        if not 0 < self.confirmation_ms <= self.min_speech_ms:
            raise ValueError("VAD confirmation must be positive and <= minimum speech duration.")
        if self.min_rms_db is not None and (
            not math.isfinite(self.min_rms_db) or not -120 <= self.min_rms_db <= 0
        ):
            raise ValueError("VAD minimum RMS must be finite and between -120 and 0 dBFS.")
        if self.silence_ms <= 0 or self.pre_roll_ms + self.trailing_ms > self.silence_ms:
            raise ValueError("Silence must cover pre-roll plus trailing padding without overlap.")
        if not math.isfinite(self.max_segment_s) or self.max_segment_s <= 0:
            raise ValueError("Maximum segment duration must be finite and positive.")
        if self.max_segment_s * 1000 <= self.pre_roll_ms + self.min_speech_ms:
            raise ValueError("Maximum segment duration must exceed pre-roll plus minimum speech.")
        if not math.isfinite(self.target_segment_s) or not (
            self.pre_roll_ms + self.min_speech_ms
            <= self.target_segment_s * 1000 < self.max_segment_s * 1000
        ):
            raise ValueError(
                "VAD segment target must cover pre-roll/minimum speech and be < maximum."
            )
        if not 0 < self.split_silence_ms <= self.silence_ms or (
            self.split_silence_ms < self.trailing_ms
        ):
            raise ValueError(
                "VAD split pause must cover trailing padding and be <= normal silence."
            )


@dataclass(frozen=True)
class CaptureAnchor:
    input_frame: int
    input_rate: int
    adc_time: float
    callback_time: float
    received_monotonic: float
    timeline_uncertain: bool


@dataclass(frozen=True)
class SpeechSegment:
    pcm: bytes  # Mono PCM16 at 16 kHz, [start_sample, end_sample), never padded zeros.
    start_sample: int
    end_sample: int
    vad_start_sample: int
    vad_end_sample: int
    decision_monotonic: float
    reason: str
    epoch: int = 0
    anchor: CaptureAnchor | None = None
    vad_end_anchor: CaptureAnchor | None = None
    timeline_origin_s: float | None = None

    @property
    def origin_s(self) -> float:
        if self.timeline_origin_s is not None:
            return self.timeline_origin_s
        return self.anchor.input_frame / self.anchor.input_rate if self.anchor else 0.0

    def metadata(self) -> dict:
        return {
            "epoch": self.epoch,
            "start_s": self.origin_s + self.start_sample / SAMPLE_RATE,
            "end_s": self.origin_s + self.end_sample / SAMPLE_RATE,
            "vad_start_s": self.origin_s + self.vad_start_sample / SAMPLE_RATE,
            "vad_end_s": self.origin_s + self.vad_end_sample / SAMPLE_RATE,
            "samples": self.end_sample - self.start_sample,
            "reason": self.reason,
            "decision_monotonic": self.decision_monotonic,
            "timeline_uncertain": self.anchor.timeline_uncertain if self.anchor else False,
            "clock_accuracy": "unvalidated",
            "timeline_source": (
                "callback_receipt_estimate" if self.timeline_origin_s is not None
                else "input_sample_indices"
            ),
            "vad_end_capture_anchor": asdict(self.vad_end_anchor) if self.vad_end_anchor else None,
        }


class Segmenter:
    """Hysteresis on 32 ms windows; padding uses exact sample counts.

    A forced split carries the remainder into a contiguous continuation. Natural
    segments have no shared samples. Only pre-roll and one bounded phrase are kept.
    """

    def __init__(self, config: VADConfig | None = None) -> None:
        self.config = config or VADConfig()
        self.cursor = 0
        self.buffer = bytearray()
        self.buffer_start = 0
        self.start: int | None = None
        self.speech_start = 0
        self.speech_end = 0
        self.speech_samples = 0
        self.continuation = False
        self.last_emitted_end = 0
        self.rejected_short = 0
        self.rejected_unconfirmed = 0
        self.onset_start: int | None = None
        self.onset_samples = 0
        self.peak_buffer_samples = 0

    def _trim(self, start: int) -> None:
        del self.buffer[:(start - self.buffer_start) * 2]
        self.buffer_start = start

    def _emit(self, end: int, reason: str, decision: float) -> SpeechSegment:
        assert self.start is not None
        segment = SpeechSegment(
            bytes(self.buffer[(self.start - self.buffer_start) * 2:(end - self.buffer_start) * 2]),
            self.start, end, self.speech_start, min(end, self.speech_end), decision, reason,
        )
        self.last_emitted_end = end
        return segment

    def push(self, pcm: bytes, probability: float, decision: float) -> list[SpeechSegment]:
        count = len(pcm) // 2
        if len(pcm) % 2 or not 0 < count <= WINDOW_SAMPLES:
            raise ValueError("Segmenter needs 1–512 PCM16 samples per VAD window.")
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Invalid speech probability.")
        before = self.cursor
        self.cursor += count
        self.buffer.extend(pcm)
        self.peak_buffer_samples = max(self.peak_buffer_samples, len(self.buffer) // 2)
        just_started = False
        if self.start is None:
            if probability >= self.config.start_threshold:
                if self.onset_start is None:
                    self.onset_start = before
                self.onset_samples += count
                if self.onset_samples >= self.config.confirmation_ms * 16:
                    self.start = max(
                        self.buffer_start, self.last_emitted_end,
                        self.onset_start - self.config.pre_roll_ms * 16,
                    )
                    self.speech_start = self.onset_start
                    self.speech_end = self.cursor
                    self.speech_samples = self.onset_samples
                    self.onset_start = None
                    self.onset_samples = 0
                    just_started = True
            else:
                if self.onset_samples:
                    self.rejected_unconfirmed += 1
                self.onset_start = None
                self.onset_samples = 0
        if self.start is not None:
            if not just_started and probability >= self.config.continue_threshold:
                self.speech_end = self.cursor
                self.speech_samples += count
            long_phrase = self.speech_end - self.start >= int(
                self.config.target_segment_s * SAMPLE_RATE
            )
            silence_ms = self.config.split_silence_ms if long_phrase else self.config.silence_ms
            if self.cursor - self.speech_end >= silence_ms * 16:
                reason = "short_pause" if silence_ms < self.config.silence_ms else "silence"
                return self.finish(reason, decision)
            limit = int(self.config.max_segment_s * SAMPLE_RATE)
            if self.cursor - self.start >= limit:
                if self.speech_samples < self.config.min_speech_ms * 16 and not self.continuation:
                    return self.finish("max_duration", decision)
                end = self.start + limit
                segment = self._emit(end, "max_duration", decision)
                self.start = end
                self.speech_start = end
                self.speech_samples = max(0, self.speech_end - end)
                self.continuation = True
                self._trim(end)
                return [segment]
        else:
            history_end = self.onset_start if self.onset_start is not None else self.cursor
            self._trim(max(self.buffer_start, history_end - self.config.pre_roll_ms * 16))
        return []

    def finish(self, reason: str, decision: float) -> list[SpeechSegment]:
        result = []
        if self.start is not None and self.speech_end > self.start:
            short = self.speech_samples < self.config.min_speech_ms * 16
            if not short or self.continuation:
                end = min(self.cursor, self.speech_end + self.config.trailing_ms * 16)
                result.append(self._emit(end, reason, decision))
            else:
                self.rejected_short += 1
        if self.onset_samples:
            self.rejected_unconfirmed += 1
        self.onset_start = None
        self.onset_samples = 0
        self.start = None
        self.continuation = False
        self._trim(max(self.buffer_start, self.cursor - self.config.pre_roll_ms * 16))
        return result

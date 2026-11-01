"""Streaming PCM conversion and VAD; capture callbacks never run this module."""

import math
from collections import deque
from dataclasses import replace
from fractions import Fraction
from time import perf_counter, thread_time

import av
import numpy as np

from armenian_speech.vad import (
    SAMPLE_RATE,
    WINDOW_SAMPLES,
    CaptureAnchor,
    Segmenter,
    SpeechSegment,
    VADConfig,
)


class PCMResampler:
    """Stateful FFmpeg anti-aliasing, preserving output PTS and flushing its tail."""

    def __init__(self, input_rate: int, channels: int) -> None:
        if input_rate <= 0 or channels not in (1, 2):
            raise ValueError("VAD capture supports a positive sample rate and mono/stereo input.")
        self.input_rate = input_rate
        self.channels = channels
        self.input_frames = 0
        self.output_samples = 0
        self.finished = False
        self.resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)

    def _collect(self, frames) -> bytes:
        pieces = []
        for frame in frames:
            if frame.pts != self.output_samples or frame.time_base != Fraction(1, SAMPLE_RATE):
                raise RuntimeError("Resampler output timeline is discontinuous.")
            pieces.append(frame.to_ndarray().tobytes())
            self.output_samples += frame.samples
        return b"".join(pieces)

    def push(self, pcm: bytes) -> bytes:
        if self.finished:
            raise RuntimeError("Resampler already flushed.")
        if not pcm or len(pcm) % (2 * self.channels):
            raise ValueError("Invalid interleaved PCM16 input block.")
        samples = np.frombuffer(pcm, dtype="<i2").reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(
            samples, format="s16", layout="mono" if self.channels == 1 else "stereo",
        )
        frame.sample_rate = self.input_rate
        frame.time_base = Fraction(1, self.input_rate)
        frame.pts = self.input_frames
        self.input_frames += len(pcm) // (2 * self.channels)
        return self._collect(self.resampler.resample(frame))

    def finish(self) -> bytes:
        if self.finished:
            return b""
        self.finished = True
        return self._collect(self.resampler.resample(None)) if self.input_frames else b""


class LiveVAD:
    """One stateful model and one bounded phrase buffer; no completed-segment queue.

    Exact queue gaps and driver epochs reset all audio/VAD state. Raw clock anchors
    are preserved, but their accuracy is explicitly not established here.
    """

    def __init__(self, model, input_rate: int, channels: int, config: VADConfig | None = None):
        self.model = model
        self.input_rate = input_rate
        self.channels = channels
        self.config = config or VADConfig()
        self.resampler = PCMResampler(input_rate, channels)
        self.segmenter = Segmenter(config)
        self.pending = bytearray()
        self.anchor: CaptureAnchor | None = None
        self.anchors: deque[CaptureAnchor] = deque()
        self.expected_frame: int | None = None
        self.capture_epoch = 0
        self.epoch = 0
        self.finished = False
        self.last_probability = 0.0
        self.last_rms_db = -120.0
        self.last_energy_pass = False
        self.stats = {
            "vad_windows": 0, "vad_wall_s": 0.0, "vad_thread_cpu_s": 0.0,
            "vad_max_window_s": 0.0, "resampled_samples": 0, "segments": 0,
            "discontinuities": 0, "known_missing_frames": 0, "rejected_short": 0,
            "rejected_unconfirmed": 0,
            "energy_rejected_speech_windows": 0,
            "max_buffer_samples": 0, "final_partial_samples": 0,
        }

    def _frames(self, pcm: bytes, final: bool = False) -> list[SpeechSegment]:
        self.pending.extend(pcm)
        self.stats["resampled_samples"] += len(pcm) // 2
        result = []
        while len(self.pending) >= WINDOW_SAMPLES * 2 or (final and self.pending):
            count = min(WINDOW_SAMPLES * 2, len(self.pending))
            raw = bytes(self.pending[:count])
            del self.pending[:count]
            samples = np.zeros(WINDOW_SAMPLES, dtype=np.float32)
            real_samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
            samples[:count // 2] = real_samples
            rms = float(np.sqrt(np.mean(real_samples * real_samples, dtype=np.float64)))
            self.last_rms_db = 20 * math.log10(rms) if rms > 0 else -120.0
            self.last_energy_pass = (
                self.config.min_rms_db is None or self.last_rms_db >= self.config.min_rms_db
            )
            cpu_before, before = thread_time(), perf_counter()
            self.last_probability = self.model.probability(samples)
            decision = perf_counter()
            elapsed = decision - before
            self.stats["vad_windows"] += 1
            self.stats["vad_wall_s"] += elapsed
            self.stats["vad_thread_cpu_s"] += thread_time() - cpu_before
            self.stats["vad_max_window_s"] = max(self.stats["vad_max_window_s"], elapsed)
            score = self.last_probability
            if not self.last_energy_pass:
                if score >= self.config.continue_threshold:
                    self.stats["energy_rejected_speech_windows"] += 1
                score = 0.0
            if count < WINDOW_SAMPLES * 2:
                self.stats["final_partial_samples"] += count // 2
            result.extend(self.segmenter.push(raw, score, decision))
        return self._stamp(result)

    def _stamp(self, segments: list[SpeechSegment]) -> list[SpeechSegment]:
        self.stats["segments"] += len(segments)
        self.stats["max_buffer_samples"] = max(
            self.stats["max_buffer_samples"], self.segmenter.peak_buffer_samples,
        )
        stamped = []
        for segment in segments:
            end_frame = (
                self.anchor.input_frame
                + (segment.vad_end_sample - 1) * self.input_rate / SAMPLE_RATE
            )
            end_anchor = next(
                (anchor for anchor in reversed(self.anchors) if anchor.input_frame <= end_frame),
                self.anchor,
            )
            stamped.append(replace(
                segment, epoch=self.epoch, anchor=self.anchor, vad_end_anchor=end_anchor,
            ))
        return stamped

    def _finish_epoch(self, reason: str) -> list[SpeechSegment]:
        result = self._frames(self.resampler.finish(), final=True)
        result.extend(self._stamp(self.segmenter.finish(reason, perf_counter())))
        self.stats["rejected_short"] += self.segmenter.rejected_short
        self.stats["rejected_unconfirmed"] += self.segmenter.rejected_unconfirmed
        return result

    def push(self, block) -> list[SpeechSegment]:
        if self.finished:
            raise RuntimeError("VAD stream already finished.")
        if len(block.pcm) != block.frames * 2 * self.channels:
            raise ValueError("Capture frame count does not match PCM16 byte length.")
        if self.expected_frame is not None and block.start_frame < self.expected_frame:
            raise ValueError("Capture sample indices went backwards or overlapped.")
        result = []
        gap = self.expected_frame is not None and (
            block.start_frame != self.expected_frame or block.capture_epoch != self.capture_epoch
        )
        if gap:
            result.extend(self._finish_epoch("gap"))
            self.stats["known_missing_frames"] += block.start_frame - self.expected_frame
            self.stats["discontinuities"] += 1
            self.epoch += 1
            self.model.reset()
            self.resampler = PCMResampler(self.input_rate, self.channels)
            self.segmenter = Segmenter(self.config)
            self.anchor = None
            self.anchors.clear()
        current_anchor = CaptureAnchor(
            block.start_frame, self.input_rate, block.adc_time, block.callback_time,
            block.received_monotonic, block.capture_epoch > 0,
        )
        if self.anchor is None:
            self.anchor = current_anchor
        self.anchors.append(current_anchor)
        history_s = self.config.max_segment_s + self.config.silence_ms / 1000 + 1
        oldest = block.start_frame - int(history_s * self.input_rate)
        while len(self.anchors) > 1 and self.anchors[1].input_frame < oldest:
            self.anchors.popleft()
        self.expected_frame = block.start_frame + block.frames
        self.capture_epoch = block.capture_epoch
        result.extend(self._frames(self.resampler.push(block.pcm)))
        return result

    def finish(
        self, reason: str = "shutdown", *, final_input_frame: int | None = None,
        final_capture_epoch: int | None = None,
    ) -> list[SpeechSegment]:
        if self.finished:
            return []
        expected = self.expected_frame or 0
        missing = 0 if final_input_frame is None else final_input_frame - expected
        if missing < 0:
            raise ValueError("Final capture sample count precedes processed audio.")
        gap = missing > 0 or (
            final_capture_epoch is not None and final_capture_epoch != self.capture_epoch
        )
        if gap:
            self.stats["known_missing_frames"] += missing
            self.stats["discontinuities"] += 1
        self.finished = True
        return self._finish_epoch("gap" if gap else reason)

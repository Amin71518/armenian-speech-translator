"""Finalize real loopback PCM when an idle renderer stops delivering callbacks."""

from dataclasses import replace

from armenian_speech.live_vad import LiveVAD
from armenian_speech.vad import VADConfig


class LoopbackVAD:
    def __init__(self, model, rate, channels, started, config=None):
        self.model, self.rate, self.channels = model, rate, channels
        self.started = started
        self.config = config or VADConfig()
        self.idle_s = max(0.65, self.config.silence_ms / 1000)
        self.wait_s = self.idle_s
        self.processor = None
        self.last_received = None
        self.origin = 0.0
        self.first_frame = 0
        self.epoch = 0
        self.stats = {"idle_flushes": 0}

    def _stamp(self, segments):
        return [replace(
            s, epoch=self.epoch + s.epoch,
            timeline_origin_s=self.origin + (s.anchor.input_frame - self.first_frame) / self.rate,
        ) for s in segments]

    def push(self, block):
        result = []
        if self.processor is not None and (
            block.received_monotonic - self.last_received >= self.wait_s
        ):
            gap = (block.start_frame != self.processor.expected_frame
                   or block.capture_epoch != self.processor.capture_epoch)
            if not gap:
                self.stats["idle_flushes"] += 1
            result.extend(self.finish("gap" if gap else "idle",
                                      block.start_frame, block.capture_epoch))
        if self.processor is None:
            self.model.reset()
            self.processor = LiveVAD(self.model, self.rate, self.channels, self.config)
            self.origin = max(
                0.0, block.received_monotonic - block.frames / self.rate - self.started,
            )
            self.first_frame = block.start_frame
        self.last_received = block.received_monotonic
        self.wait_s = max(self.idle_s, 2 * block.frames / self.rate)
        result.extend(self._stamp(self.processor.push(block)))
        return result

    def idle(self, now, final_frame, capture_epoch):
        if self.processor is None or now - self.last_received < self.wait_s:
            return []
        self.stats["idle_flushes"] += 1
        return self.finish("idle", final_frame, capture_epoch)

    def finish(self, reason="shutdown", final_frame=None, capture_epoch=None):
        if self.processor is None:
            return []
        result = self._stamp(self.processor.finish(
            reason, final_input_frame=final_frame, final_capture_epoch=capture_epoch,
        ))
        for key, value in self.processor.stats.items():
            if key in {"max_buffer_samples", "vad_max_window_s"}:
                self.stats[key] = max(self.stats.get(key, 0), value)
            else:
                self.stats[key] = self.stats.get(key, 0) + value
        self.epoch += self.processor.epoch + 1
        self.processor = None
        return result

import json
from types import SimpleNamespace

import pytest

from armenian_speech import combined
from armenian_speech.fair_queue import FairQueue
from tests.test_live_pipeline import phrase
from tests.test_microphone import callback_status
from tests.test_vad import AlwaysSpeech


class Worker:
    capacity = 1
    shutdown_timeout = 1

    def __init__(self):
        self.stats = {"accepted": 0, "completed": 0}
        self.seen = []

    def poll(self):
        pass

    def submit(self, segment, *, speaker):
        self.seen.append((speaker, segment))
        self.stats["accepted"] += 1
        return True


def test_flooded_source_cannot_take_other_source_pending_slots_or_all_turns():
    worker = Worker()
    queue = FairQueue(worker, capacity=2)
    assert queue.offer("System", phrase())
    assert queue.offer("System", phrase())
    assert not queue.offer("System", phrase())
    assert queue.offer("Me", phrase())
    queue.dispatch()
    assert worker.seen[0][0] == "Me"
    # Continuously refill Me; System still receives the next turn.
    assert queue.offer("Me", phrase())
    worker.stats["completed"] += 1
    queue.dispatch()
    assert worker.seen[1][0] == "System"
    worker.stats["completed"] += 1
    queue.dispatch()
    assert worker.seen[2][0] == "Me"
    assert queue.stats["System"]["dropped_full"] == 1
    assert queue.stats["System"]["peak_pending"] == 2
    queue.cancel()
    assert queue.pending == 0 and queue.stats["System"]["cancelled"] == 1


def test_gap_and_bad_labels_never_enter_worker_queue():
    worker = Worker()
    queue = FairQueue(worker)
    assert not queue.offer("Me", phrase(reason="gap"))
    queue.dispatch()
    assert worker.seen == [] and queue.stats["Me"]["skipped_gap"] == 1
    with pytest.raises(ValueError):
        queue.offer("unknown", phrase())


@pytest.mark.parametrize("failure", [False, True, "open_error", "timeout"])
def test_two_inputs_stay_separate_and_both_close_before_final_inference(
    monkeypatch, failure, capsys,
):
    backend = SimpleNamespace(paInt16=8, paInputOverflow=2, paContinue=0, paAbort=2)
    models = []

    def load_model(_):
        model = AlwaysSpeech()
        models.append(model)
        return model

    monkeypatch.setattr(combined, "SileroVAD", load_model)

    class Mic:
        latency = 0.01
        closed = False
        active = failure is not True

        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]

        def start(self):
            self.callback(b"\x64\x00" * 8000, 8000,
                          SimpleNamespace(inputBufferAdcTime=1, currentTime=2), callback_status())

        def close(self):
            self.closed = True

    class System:
        closed = False

        def start_stream(self):
            self.callback(b"\xc8\x00" * 8000, 8000,
                          {"input_buffer_adc_time": 1, "current_time": 2}, 0)

        def is_active(self):
            return True

        def close(self):
            self.closed = True

    mic = Mic(callback=None)
    system = System()

    def open_mic(**kwargs):
        mic.callback = kwargs["callback"]
        return mic

    def open_system(**kwargs):
        if failure == "open_error":
            system.closed = True  # No native handle was created.
            raise RuntimeError("open failed")
        system.callback = kwargs["stream_callback"]
        return system

    monkeypatch.setattr(combined.sd, "RawInputStream", open_mic)
    manager = SimpleNamespace(open=open_system, get_device_info_by_index=lambda _: {
        "isLoopbackDevice": True, "maxInputChannels": 1, "defaultSampleRate": 16000,
    })
    args = SimpleNamespace(device=10, microphone_device=9, microphone_rate=16000,
                           microphone_channels=1, pending_per_source=2, block_frames=1024,
                           diagnostics=True, duration=0.01,
                           shutdown_timeout=0.05 if failure == "timeout" else 1, vad_model=None,
                           live=True, segment_max_s=6, segment_target_s=3.5, segment_pause_ms=256,
                           vad_threshold=0.65, vad_continue_threshold=0.5, min_speech_ms=300,
                           vad_confirm_ms=160, min_rms_db=None)

    class Immediate(Worker):
        def submit(self, segment, *, speaker):
            assert mic.closed and system.closed
            super().submit(segment, speaker=speaker)
            if failure != "timeout":
                self.stats["completed"] += 1
            return True

        def close(self, *, drain=True):
            assert mic.closed and system.closed

        def summary(self):
            return self.stats

    worker = Immediate()
    if failure:
        match = {True: "stream stopped", "open_error": "open failed", "timeout": "timed out"}
        with pytest.raises(RuntimeError, match=match[failure]):
            combined.run(manager, backend, args, worker, lambda: False)
        if failure != "timeout":
            assert worker.seen == []
    else:
        assert combined.run(manager, backend, args, worker, lambda: False) == 0
        assert [(label, segment.pcm[:2]) for label, segment in worker.seen] == [
            ("Me", b"\x64\x00"), ("System", b"\xc8\x00"),
        ]
        assert all(len(segment.pcm) == 16000 for _, segment in worker.seen)
    assert mic.closed and system.closed and models[0] is not models[1]
    summary = json.loads(capsys.readouterr().out.split("Capture summary: ")[1])
    assert summary["stream_closed"]
    if failure == "timeout":
        assert summary["scheduler"]["System"]["cancelled"] == 1

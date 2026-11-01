from types import SimpleNamespace

import pytest

from armenian_speech.system_audio import LoopbackCapture, capture, select_device

BACKEND = SimpleNamespace(paInputOverflow=2, paContinue=0, paAbort=2, paInt16=8)
TIMING = {"input_buffer_adc_time": 1, "current_time": 2}


def test_callback_copies_pcm_and_counts_full_queue_and_epoch():
    source = LoopbackCapture(BACKEND, 2, capacity=1)
    data = bytearray(b"\x01\x00" * 8)
    assert source.callback(data, 4, TIMING, 0) == (None, 0)
    data[0] = 4
    source.callback(data, 4, TIMING, 2)
    block = source.blocks.get_nowait()
    assert block.pcm[0] == 1 and block.start_frame == 0
    source.callback(data, 4, TIMING, 0)
    assert source.blocks.get_nowait().capture_epoch == 1
    assert source.stats.frames == 12 and source.stats.queue_dropped_frames == 4
    assert source.stats.input_overflows == 1


def test_callback_failure_aborts_explicitly():
    source = LoopbackCapture(BACKEND, 2)
    assert source.callback(b"bad", 4, TIMING, 0) == (None, 2)
    assert isinstance(source.error, ValueError)


def test_microphone_is_not_accepted_as_loopback():
    manager = SimpleNamespace(get_device_info_by_index=lambda _: {
        "maxInputChannels": 2, "isLoopbackDevice": False,
    })
    with pytest.raises(ValueError, match="loopback ID"):
        select_device(manager, 1)


@pytest.mark.parametrize("mode", ["idle", "ctrl_c", "callback_failure"])
def test_stream_closes_with_idle_input_stop_and_errors(mode, capsys):
    class Stream:
        closed = False

        def start_stream(self):
            if mode == "callback_failure":
                callback(None, 4, TIMING, 0)

        def is_active(self):
            return True

        def close(self):
            self.closed = True

        def get_input_latency(self):
            return 0.01

    stream = Stream()

    def open_stream(**kwargs):
        nonlocal callback
        callback = kwargs["stream_callback"]
        return stream

    callback = None
    manager = SimpleNamespace(open=open_stream, get_device_info_by_index=lambda _: {
        "maxInputChannels": 2, "isLoopbackDevice": True,
        "defaultSampleRate": 48000, "name": "test loopback",
    })
    args = SimpleNamespace(device=10, duration=0.01, block_frames=1024)
    if mode == "callback_failure":
        with pytest.raises(RuntimeError, match="callback failed"):
            capture(manager, BACKEND, args, lambda: False)
    else:
        assert capture(manager, BACKEND, args, lambda: mode == "ctrl_c") == (
            130 if mode == "ctrl_c" else 0
        )
    assert stream.closed
    assert '"pending_frames": 0' in capsys.readouterr().out


@pytest.mark.parametrize("diagnostics", [False, True])
@pytest.mark.parametrize("worker_error", [False, True])
def test_live_final_pcm_routes_after_stream_close_and_keeps_quiet_output(
    monkeypatch, capsys, diagnostics, worker_error,
):
    from armenian_speech.microphone import parser
    from tests.test_vad import AlwaysSpeech

    args = parser().parse_args(["--device", "10", "--live", "--duration", "0.01"])
    args.block_frames = 1024
    args.diagnostics = diagnostics
    monkeypatch.setattr("armenian_speech.vad.SileroVAD", lambda _: AlwaysSpeech())

    class Stream:
        closed = False

        def start_stream(self):
            callback(b"\x01\x00" * 8000, 8000, TIMING, 0)

        def is_active(self):
            return True

        def close(self):
            self.closed = True

        def get_input_latency(self):
            return 0.01

    stream = Stream()
    callback = None

    def open_stream(**kwargs):
        nonlocal callback
        callback = kwargs["stream_callback"]
        return stream

    class Worker:
        seen = []

        def poll(self):
            if worker_error:
                raise RuntimeError("worker failed")

        def submit(self, segment):
            assert stream.closed
            self.seen.append(segment)

        def close(self, *, drain):
            assert stream.closed and drain != worker_error

        def summary(self):
            return {"completed": len(self.seen)}

    worker = Worker()
    manager = SimpleNamespace(open=open_stream, get_device_info_by_index=lambda _: {
        "maxInputChannels": 1, "isLoopbackDevice": True,
        "defaultSampleRate": 16000, "name": "test loopback",
    })
    if worker_error:
        with pytest.raises(RuntimeError, match="worker failed"):
            capture(manager, BACKEND, args, lambda: False, worker)
        assert worker.seen == []
    else:
        assert capture(manager, BACKEND, args, lambda: False, worker) == 0
        assert len(worker.seen) == 1 and len(worker.seen[0].pcm) == 16000
        assert worker.seen[0].reason == "duration"
    output = capsys.readouterr().out
    assert ("Capture summary:" in output) == (diagnostics or worker_error)

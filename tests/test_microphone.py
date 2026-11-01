import json
import signal
from itertools import count
from types import SimpleNamespace

import pytest

from armenian_speech import microphone


def callback_status(*, overflow=False, underflow=False):
    class Status:
        input_overflow = overflow
        input_underflow = underflow

        def __bool__(self):
            return overflow or underflow

    return Status()


def test_callback_copies_audio_and_preserves_sample_indices_and_device_times():
    capture = microphone.MicrophoneCapture()
    data = bytearray(b"\x01\x00\x02\x00")
    times = SimpleNamespace(inputBufferAdcTime=12.0, currentTime=12.1)
    capture.callback(data, 2, times, callback_status(overflow=True))
    data[0] = 99
    capture.callback(data, 2, times, callback_status(underflow=True))
    first = capture.blocks.get_nowait()
    second = capture.blocks.get_nowait()
    assert first.pcm == b"\x01\x00\x02\x00"
    assert (first.start_frame, second.start_frame) == (0, 2)
    assert (first.adc_time, first.callback_time) == (12.0, 12.1)
    assert capture.stats.frames == 4
    assert capture.stats.input_overflow_events == 1
    assert capture.stats.input_underflow_events == 1
    assert capture.stats.status_events == 2


def test_full_raw_buffer_drops_newest_without_losing_accounting():
    capture = microphone.MicrophoneCapture(buffer_blocks=1)
    times = SimpleNamespace(inputBufferAdcTime=1.0, currentTime=1.1)
    for _ in range(100):
        capture.callback(b"\x00\x00" * 4, 4, times, callback_status())
    assert capture.blocks.qsize() == 1
    assert capture.blocks.get_nowait().start_frame == 0
    assert capture.stats.frames == 400
    assert capture.stats.queue_dropped_blocks == 99
    assert capture.stats.queue_dropped_frames == 396
    capture.callback(b"\x00\x00" * 4, 4, times, callback_status())
    assert capture.blocks.get_nowait().start_frame == 400


def test_callback_failure_is_available_to_main_thread():
    capture = microphone.MicrophoneCapture()
    with pytest.raises(microphone.sd.CallbackAbort):
        capture.callback(None, 4, None, callback_status())
    assert isinstance(capture.error, TypeError)


def test_timestamp_anomalies_are_counted_without_fabricating_times():
    capture = microphone.MicrophoneCapture()
    for adc_time, callback_time in [(0.0, 0.0), (0.0, 0.0), (2.0, 1.99), (float("nan"), 3)]:
        capture.callback(
            b"\x00\x00", 1,
            SimpleNamespace(inputBufferAdcTime=adc_time, currentTime=callback_time),
            callback_status(),
        )
    assert capture.stats.adc_zero_blocks == 2
    assert capture.stats.adc_nonmonotonic_events == 1
    assert capture.stats.adc_after_callback_events == 1
    assert capture.stats.timestamp_nonfinite_blocks == 1


@pytest.fixture
def fake_device(monkeypatch):
    device = {
        "name": "Test microphone", "max_input_channels": 2,
        "default_samplerate": 48000.0, "hostapi": 0,
    }
    monkeypatch.setattr(microphone.sd, "query_devices", lambda: [device])
    monkeypatch.setattr(
        microphone.sd, "query_hostapis",
        lambda index=None: [{"name": "Test API"}] if index is None else {"name": "Test API"},
    )
    monkeypatch.setattr(microphone.sd, "check_input_settings", lambda **kwargs: None)
    return device


@pytest.fixture
def fake_stream(monkeypatch, fake_device):
    class Stream:
        samplerate = 16000.0
        channels = 1
        dtype = "int16"
        latency = 0.01
        active = False
        closed = False
        created = []
        fail_callback = False
        stop_unexpectedly = False

        def __init__(self, **kwargs):
            self.callback = kwargs["callback"]
            self.created.append(self)

        def __enter__(self):
            self.active = not self.stop_unexpectedly
            if self.fail_callback:
                self.callback.__self__.error = RuntimeError("device callback failed")
            else:
                self.callback(
                    b"\x00\x40" * 4, 4,
                    SimpleNamespace(inputBufferAdcTime=1.0, currentTime=1.01),
                    callback_status(),
                )
            return self

        def close(self):
            self.closed = True
            self.active = False

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(microphone.sd, "RawInputStream", Stream)
    return Stream


def summary_from(output):
    line = next(line for line in output.splitlines() if line.startswith("Capture summary: "))
    return json.loads(line.removeprefix("Capture summary: "))


def test_finite_capture_reports_format_counts_and_releases_stream(monkeypatch, fake_stream, capsys):
    ticks = iter(index / 1000 for index in range(100))
    monkeypatch.setattr(microphone, "perf_counter", lambda: next(ticks))
    assert microphone.main(["--device", "0", "--duration", "0.01"]) == 0
    summary = summary_from(capsys.readouterr().out)
    assert summary["sample_rate"] == 16000
    assert summary["channels"] == 1
    assert summary["dtype"] == "int16"
    assert summary["frames"] == summary["processed_frames"] == 4
    assert summary["peak"] == 0.5
    assert summary["driver_lost_frames"] is None
    assert summary["stopped_by"] == "duration"
    assert summary["stream_closed"] and fake_stream.created[0].closed


def test_ctrl_c_closes_stream_and_allows_a_second_capture(monkeypatch, fake_stream, capsys):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(microphone.Queue, "get", interrupt)
    for _ in range(2):
        assert microphone.main(["--device", "0"]) == 130
        summary = summary_from(capsys.readouterr().out)
        assert summary["stopped_by"] == "ctrl_c"
        assert summary["stream_closed"]
        assert summary["pending_frames"] == 4
    assert len(fake_stream.created) == 2
    assert all(stream.closed for stream in fake_stream.created)


@pytest.mark.parametrize("callback_failure", [False, True])
def test_stream_failure_is_reported_and_closed(callback_failure, fake_stream, capsys):
    fake_stream.fail_callback = callback_failure
    fake_stream.stop_unexpectedly = not callback_failure
    assert microphone.main(["--device", "0"]) == 1
    output = capsys.readouterr()
    expected = "Audio callback failed" if callback_failure else "unexpectedly"
    assert expected in output.err
    assert summary_from(output.out)["stopped_by"] == "error"
    assert fake_stream.created[0].closed


@pytest.mark.parametrize("arguments", [
    ["--device", "-1"], ["--device", "1"], ["--device", "0", "--channels", "3"],
])
def test_invalid_selection_fails_before_opening_stream(arguments, fake_stream, capsys):
    assert microphone.main(arguments) == 1
    assert "Error:" in capsys.readouterr().err
    assert not fake_stream.created


def test_unsupported_rate_fails_without_another_format(monkeypatch, fake_stream, capsys):
    calls = []

    def unsupported(**kwargs):
        calls.append(kwargs)
        raise microphone.sd.PortAudioError("Invalid sample rate")

    monkeypatch.setattr(microphone.sd, "check_input_settings", unsupported)
    assert microphone.main(["--device", "0"]) == 1
    assert len(calls) == 1 and calls[0]["samplerate"] == 16000
    assert not fake_stream.created
    assert "Invalid sample rate" in capsys.readouterr().err


def test_listing_excludes_output_only_devices(monkeypatch, fake_device, capsys):
    monkeypatch.setattr(
        microphone.sd, "query_devices", lambda: [
            {"name": "Speakers", "max_input_channels": 0}, fake_device,
        ],
    )
    assert microphone.main(["--list-devices"]) == 0
    output = capsys.readouterr().out
    assert "1: Test microphone | Test API" in output
    assert "Speakers" not in output


@pytest.mark.parametrize("duration", ["0", "-1", "nan", "inf"])
def test_invalid_duration_is_rejected(duration):
    with pytest.raises(SystemExit) as error:
        microphone.main(["--device", "0", "--duration", duration])
    assert error.value.code == 2


def test_device_selection_is_required():
    with pytest.raises(SystemExit) as error:
        microphone.main([])
    assert error.value.code == 2


def test_vad_ctrl_c_drains_pending_audio_and_flushes_partial_window(
    monkeypatch, fake_stream, capsys,
):
    from tests.test_vad import AlwaysSpeech

    monkeypatch.setattr("armenian_speech.vad.SileroVAD", lambda directory: AlwaysSpeech())
    original_get = microphone.Queue.get

    def interrupt_wait(self, *args, **kwargs):
        if "timeout" in kwargs:
            raise KeyboardInterrupt
        return original_get(self, *args, **kwargs)

    monkeypatch.setattr(microphone.Queue, "get", interrupt_wait)
    assert microphone.main(["--device", "0", "--vad"]) == 130
    output = capsys.readouterr().out
    assert "VAD phrase:" not in output
    summary = summary_from(output)
    assert summary["processed_frames"] == summary["frames"] == 4
    assert summary["pending_frames"] == 0
    assert summary["vad"]["final_partial_samples"] == 4
    assert summary["vad"]["segments"] == 0
    assert summary["vad"]["rejected_unconfirmed"] == 1
    assert summary["stream_closed"] and fake_stream.created[0].closed


def test_vad_inference_failure_closes_capture_without_retry(monkeypatch, fake_stream, capsys):
    class BrokenModel:
        def probability(self, samples):
            raise RuntimeError("VAD inference failed")

    monkeypatch.setattr("armenian_speech.vad.SileroVAD", lambda directory: BrokenModel())
    # Enough raw frames to invoke VAD before shutdown rather than only in finalization.
    fake_stream.samplerate = 16000
    original_enter = fake_stream.__enter__

    def enter(self):
        original_enter(self)
        self.callback(
            b"\x00\x00" * 512, 512,
            SimpleNamespace(inputBufferAdcTime=1.1, currentTime=1.2), callback_status(),
        )
        return self

    monkeypatch.setattr(fake_stream, "__enter__", enter)
    assert microphone.main(["--device", "0", "--vad"]) == 1
    output = capsys.readouterr()
    assert "VAD inference failed" in output.err
    summary = summary_from(output.out)
    assert summary["vad_audio_discarded_on_error"]
    assert summary["stream_closed"] and fake_stream.created[0].closed


def test_live_mode_routes_final_phrase_and_closes_device_before_worker(
    monkeypatch, fake_stream, capsys,
):
    from tests.test_vad import AlwaysSpeech

    class Worker:
        metadata = {}
        stats = {"accepted": 0, "completed": 0, "dropped_full": 0}
        closed = False
        seen = []

        def start(self):
            assert not fake_stream.created

        def poll(self):
            pass

        def submit(self, segment):
            self.seen.append(segment)
            self.stats["accepted"] += 1

        def close(self, *, drain=True):
            if not self.closed:
                assert fake_stream.created[0].closed
            self.closed = True

        def summary(self):
            return {"worker_closed": self.closed}

    worker = Worker()
    monkeypatch.setattr("armenian_speech.live_pipeline.InferenceWorker", lambda *a, **kw: worker)
    monkeypatch.setattr("armenian_speech.vad.SileroVAD", lambda directory: AlwaysSpeech())
    original_enter = fake_stream.__enter__
    previous_handler = signal.getsignal(signal.SIGINT)

    def enter_and_interrupt(self):
        original_enter(self)
        self.callback(
            b"\x00\x40" * 8000, 8000,
            SimpleNamespace(inputBufferAdcTime=1.01, currentTime=1.02), callback_status(),
        )
        signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        return self

    monkeypatch.setattr(fake_stream, "__enter__", enter_and_interrupt)
    assert microphone.main(["--device", "0", "--live", "--diagnostics"]) == 130
    assert len(worker.seen) == 1 and worker.seen[0].reason == "shutdown"
    assert len(worker.seen[0].pcm) == 16008
    assert summary_from(capsys.readouterr().out)["inference"]["worker_closed"]
    assert signal.getsignal(signal.SIGINT) == previous_handler


def test_invalid_live_device_fails_before_inference_initialization(
    monkeypatch, fake_device, capsys,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid device must not load ASR/MT")

    monkeypatch.setattr("armenian_speech.live_pipeline.InferenceWorker", forbidden)
    assert microphone.main(["--device", "-1", "--live"]) == 1
    assert "Invalid device index" in capsys.readouterr().err


@pytest.mark.parametrize("diagnostics", [False, True])
def test_live_status_is_opt_in(monkeypatch, fake_stream, capsys, diagnostics):
    from tests.test_vad import AlwaysSpeech

    class Worker:
        stats = {"accepted": 0, "completed": 0, "dropped_full": 0}

        def poll(self):
            pass

        def submit(self, segment):
            raise AssertionError("An unconfirmed four-sample candidate must not reach ASR")

        def close(self, **kwargs):
            pass

        def summary(self):
            return {}

    monkeypatch.setattr("armenian_speech.vad.SileroVAD", lambda directory: AlwaysSpeech())
    ticks = count(step=0.05)
    monkeypatch.setattr(microphone, "perf_counter", lambda: next(ticks))
    arguments = ["--device", "0", "--live", "--duration", "1.5"]
    if diagnostics:
        arguments.append("--diagnostics")
    assert microphone.capture(microphone.parser().parse_args(arguments), Worker()) == 0
    output = capsys.readouterr().out
    assert ("audio=" in output) == diagnostics
    assert ("Capture summary:" in output) == diagnostics


@pytest.mark.parametrize("options", [
    ["--vad-threshold", "nan"], ["--vad-threshold", "1"], ["--vad-confirm-ms", "0"],
    ["--segment-target-s", "nan"], ["--segment-max-s", "0"], ["--segment-pause-ms", "0"],
])
def test_invalid_vad_cli_values_are_rejected(options):
    with pytest.raises(SystemExit) as error:
        microphone.parser().parse_args(["--device", "0", "--live", *options])
    assert error.value.code == 2


@pytest.mark.parametrize("options", [
    ["--vad-threshold", "0.4"], ["--min-speech-ms", "100"],
    ["--segment-target-s", "6"], ["--segment-max-s", "13"],
    ["--segment-pause-ms", "99"],
])
def test_contradictory_vad_options_fail_before_loading_models(
    monkeypatch, fake_device, capsys, options,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid VAD settings must not load ASR/MT")

    monkeypatch.setattr("armenian_speech.live_pipeline.InferenceWorker", forbidden)
    assert microphone.main(["--device", "0", "--live", *options]) == 1
    assert "VAD" in capsys.readouterr().err

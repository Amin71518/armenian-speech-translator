import hashlib
import json

import numpy as np
import pytest

from armenian_speech.live_vad import LiveVAD, PCMResampler
from armenian_speech.microphone import AudioBlock
from armenian_speech.vad import (
    SAMPLE_RATE,
    WHEEL_SHA256,
    WINDOW_SAMPLES,
    Segmenter,
    SileroVAD,
    VADConfig,
)


def pcm(count, value=1234):
    return np.full(count, value, dtype="<i2").tobytes()


def feed(segmenter, probabilities):
    result = []
    for index, probability in enumerate(probabilities):
        result.extend(segmenter.push(pcm(512, index), probability, index * 0.032))
    return result


def test_silence_only_is_bounded_and_never_emits():
    segmenter = Segmenter()
    assert feed(segmenter, [0.0] * 10000) == []
    assert segmenter.finish("shutdown", 321) == []
    assert len(segmenter.buffer) // 2 == 4800
    assert segmenter.peak_buffer_samples <= 4800 + 512


def test_padding_and_hangover_use_audio_samples_not_decision_time():
    segmenter = Segmenter()
    segments = feed(segmenter, [0.0] * 20 + [1.0] * 10 + [0.0] * 19)
    assert len(segments) == 1
    segment = segments[0]
    assert segment.start_sample == 20 * 512 - 4800
    assert segment.vad_start_sample == 20 * 512
    assert segment.vad_end_sample == 30 * 512
    assert segment.end_sample == 30 * 512 + 1600
    assert segment.reason == "silence"
    original = b"".join(pcm(512, index) for index in range(49))
    assert segment.pcm == original[segment.start_sample * 2:segment.end_sample * 2]
    assert segment.decision_monotonic > segment.vad_end_sample / SAMPLE_RATE


def test_short_pause_and_hysteresis_keep_one_phrase():
    segmenter = Segmenter()
    probabilities = [1.0] * 10 + [0.0] * 10 + [0.55] * 10 + [0.0] * 19
    segments = feed(segmenter, probabilities)
    assert len(segments) == 1
    assert segments[0].vad_start_sample == 0
    assert segments[0].vad_end_sample == 30 * 512
    assert feed(Segmenter(), [0.55] * 50) == []


@pytest.mark.parametrize("reason", ["silence", "shutdown", "duration", "eof", "gap"])
def test_short_confirmed_candidate_is_rejected_for_every_finish_reason(reason):
    segmenter = Segmenter()
    feed(segmenter, [1.0] * 5)
    assert segmenter.finish(reason, 1) == []
    assert segmenter.rejected_short == 1


def test_repeated_brief_spikes_never_confirm_a_phrase():
    segmenter = Segmenter()
    assert feed(segmenter, ([0.95] * 4 + [0.01]) * 100) == []
    assert segmenter.finish("shutdown", 20) == []
    assert segmenter.rejected_unconfirmed == 100
    assert segmenter.peak_buffer_samples <= (300 + 160) * 16 + 512


def test_one_spike_cannot_latch_on_ambiguous_continuation_probability():
    segmenter = Segmenter()
    assert feed(segmenter, [0.95] + [0.55] * 500) == []
    assert segmenter.start is None
    assert segmenter.finish("shutdown", 20) == []


def test_threshold_setting_changes_which_speech_can_start():
    frames = [0.60] * 10 + [0.0] * 19
    assert feed(Segmenter(), frames) == []
    relaxed = Segmenter(VADConfig(start_threshold=0.55, continue_threshold=0.4))
    assert len(feed(relaxed, frames)) == 1


def test_natural_phrases_do_not_overlap():
    segmenter = Segmenter()
    result = feed(segmenter, ([1.0] * 10 + [0.0] * 19) * 3)
    assert len(result) == 3
    assert all(
        first.end_sample <= second.start_sample
        for first, second in zip(result, result[1:], strict=False)
    )


def test_long_speech_splits_exactly_without_lost_or_duplicated_samples():
    segmenter = Segmenter()
    result = feed(segmenter, [1.0] * 800)
    tail = pcm(137, 123)
    result.extend(segmenter.push(tail, 1.0, 26))
    result.extend(segmenter.finish("shutdown", 26))
    assert len(result) == 5
    assert [segment.reason for segment in result] == ["max_duration"] * 4 + ["shutdown"]
    assert all(len(segment.pcm) // 2 <= 6 * SAMPLE_RATE for segment in result)
    assert all(
        first.end_sample == second.start_sample
        for first, second in zip(result, result[1:], strict=False)
    )
    assert b"".join(segment.pcm for segment in result) == (
        b"".join(pcm(512, index) for index in range(800)) + tail
    )
    assert segmenter.peak_buffer_samples <= 6 * SAMPLE_RATE + WINDOW_SAMPLES


def test_long_phrase_finishes_at_short_pause_before_normal_hangover():
    segmenter = Segmenter()
    assert feed(segmenter, [1.0] * 120 + [0.0] * 7) == []
    result = segmenter.push(pcm(512), 0.0, 4.096)
    assert len(result) == 1 and result[0].reason == "short_pause"
    assert result[0].vad_end_sample == 120 * 512
    assert result[0].end_sample == 120 * 512 + 1600
    assert segmenter.cursor - result[0].vad_end_sample == 4096  # 256 ms.


def test_short_pause_before_target_keeps_short_utterance_together():
    segmenter = Segmenter()
    assert feed(segmenter, [1.0] * 50 + [0.0] * 8 + [1.0] * 50 + [0.0] * 18) == []
    result = segmenter.push(pcm(512), 0.0, 4.064)
    assert len(result) == 1 and result[0].reason == "silence"
    assert result[0].vad_end_sample == 108 * 512


def test_long_phrase_pause_shorter_than_split_threshold_is_not_a_boundary():
    segmenter = Segmenter()
    assert feed(segmenter, [1.0] * 120 + [0.0] * 7 + [1.0] * 10) == []
    result = segmenter.finish("shutdown", 5)
    assert len(result) == 1
    assert result[0].vad_end_sample == 137 * 512


def test_quick_resumption_after_short_pause_preserves_speech_and_has_no_overlap():
    segmenter = Segmenter()
    probabilities = [1.0] * 120 + [0.0] * 8 + [1.0] * 15 + [0.0] * 19
    result = feed(segmenter, probabilities)
    assert len(result) == 2
    assert result[0].reason == "short_pause" and result[1].reason == "silence"
    assert result[0].end_sample == result[1].start_sample
    original = b"".join(pcm(512, index) for index in range(len(probabilities)))
    for segment in result:
        assert segment.pcm == original[segment.start_sample * 2:segment.end_sample * 2]
    for start, end in ((0, 120 * 512), (128 * 512, 143 * 512)):
        assert any(segment.start_sample <= start < end <= segment.end_sample for segment in result)


def test_short_tail_after_six_second_limit_survives_shutdown():
    segmenter = Segmenter()
    first = feed(segmenter, [1.0] * 188)  # 6.016 s; 256 real samples after the split.
    tail = segmenter.finish("shutdown", 6.016)
    assert len(first) == len(tail) == 1
    assert first[0].end_sample == tail[0].start_sample == 96000
    assert tail[0].end_sample == 188 * 512
    assert len(tail[0].pcm) == 512


def test_legacy_twelve_second_settings_remain_available_for_comparison():
    segmenter = Segmenter(VADConfig(max_segment_s=12, split_silence_ms=600))
    assert feed(segmenter, [1.0] * 200 + [0.0] * 8) == []
    result = segmenter.finish("shutdown", 7)
    assert len(result) == 1


@pytest.mark.parametrize("rate,channels", [(16000, 1), (44100, 1), (48000, 1), (48000, 2)])
def test_streaming_resampling_matches_whole_input_and_flushes_tail(rate, channels):
    signal = (np.sin(np.arange(rate + 137) * 2 * np.pi * 1000 / rate) * 10000).astype("<i2")
    interleaved = np.repeat(signal[:, None], channels, axis=1).tobytes()
    whole = PCMResampler(rate, channels)
    expected = whole.push(interleaved) + whole.finish()
    stream = PCMResampler(rate, channels)
    step = 137 * 2 * channels
    result = b"".join(
        stream.push(interleaved[i:i + step]) for i in range(0, len(interleaved), step)
    )
    result += stream.finish()
    assert result == expected
    assert abs(len(result) / 2 - len(signal) * SAMPLE_RATE / rate) <= 1
    assert stream.finish() == b""


def test_downsampling_filters_out_frequencies_above_new_nyquist():
    def amplitude(frequency):
        samples = (np.sin(np.arange(48000) * 2 * np.pi * frequency / 48000) * 10000).astype("<i2")
        converter = PCMResampler(48000, 1)
        output = np.frombuffer(converter.push(samples.tobytes()) + converter.finish(), dtype="<i2")
        return np.sqrt(np.mean(output[100:-100].astype(float) ** 2))

    assert amplitude(12000) / amplitude(1000) < 0.01


class AlwaysSpeech:
    def __init__(self):
        self.resets = 0
        self.last_input = None

    def probability(self, samples):
        assert samples.shape == (512,) and samples.dtype == np.float32
        self.last_input = samples.copy()
        return 1.0

    def reset(self):
        self.resets += 1


def block(start, frames, *, epoch=0, rate=16000):
    return AudioBlock(pcm(frames), frames, start, 10 + start / rate, 11 + start / rate, 99, epoch)


def test_partial_final_vad_window_has_no_fabricated_audio_or_timestamps():
    model = AlwaysSpeech()
    processor = LiveVAD(model, 16000, 1)
    assert processor.push(block(0, 8681)) == []
    segments = processor.finish()
    assert len(segments) == 1
    assert segments[0].pcm == pcm(8681)
    assert segments[0].end_sample == 8681
    assert segments[0].anchor.received_monotonic == 99
    assert processor.stats["final_partial_samples"] == 489
    assert np.all(model.last_input[489:] == 0)
    assert processor.last_rms_db == pytest.approx(20 * np.log10(1234 / 32768))
    assert processor.finish() == []


def test_quiet_background_is_rejected_even_if_model_reports_speech():
    model = AlwaysSpeech()
    processor = LiveVAD(model, 16000, 1, VADConfig(min_rms_db=-50))
    raw = pcm(16000, value=20)
    processor.push(AudioBlock(raw, 16000, 0, 1, 2))
    assert processor.finish() == []
    assert processor.last_probability == 1
    assert not processor.last_energy_pass
    assert processor.stats["energy_rejected_speech_windows"] > 0
    relaxed = LiveVAD(AlwaysSpeech(), 16000, 1, VADConfig(min_rms_db=-70))
    relaxed.push(AudioBlock(raw, 16000, 0, 1, 2))
    assert relaxed.finish()[0].pcm == raw


def test_quiet_speech_is_not_volume_gated_by_default():
    processor = LiveVAD(AlwaysSpeech(), 16000, 1)
    raw = pcm(16000, value=1)
    processor.push(AudioBlock(raw, 16000, 0, 1, 2))
    assert processor.finish()[0].pcm == raw


@pytest.mark.parametrize("driver_gap", [False, True])
def test_gaps_flush_incomplete_phrase_reset_state_and_preserve_source_origin(driver_gap):
    model = AlwaysSpeech()
    processor = LiveVAD(model, 48000, 1)
    assert processor.push(block(0, 48000, rate=48000)) == []
    start = 48000 if driver_gap else 48960
    result = processor.push(block(start, 48000, epoch=int(driver_gap), rate=48000))
    result.extend(processor.finish())
    assert [segment.reason for segment in result] == ["gap", "shutdown"]
    assert result[0].pcm == result[1].pcm
    assert len(result[0].pcm) // 2 == 16000
    assert result[1].origin_s == start / 48000
    assert result[1].anchor.timeline_uncertain == driver_gap
    assert result[1].epoch == 1 and model.resets == 1
    assert processor.stats["known_missing_frames"] == (0 if driver_gap else 960)
    assert processor.stats["resampled_samples"] == 32000
    assert result[1].vad_end_anchor.input_frame == start
    assert result[1].metadata()["clock_accuracy"] == "unvalidated"


def test_overlapping_capture_blocks_are_rejected():
    processor = LiveVAD(AlwaysSpeech(), 16000, 1)
    processor.push(block(0, 512))
    with pytest.raises(ValueError, match="overlapped"):
        processor.push(block(0, 512))


@pytest.mark.parametrize("driver_gap", [False, True])
def test_trailing_loss_is_accounted_even_without_a_later_capture_block(driver_gap):
    processor = LiveVAD(AlwaysSpeech(), 16000, 1)
    processor.push(block(0, 8681))
    segments = processor.finish(
        final_input_frame=8681 if driver_gap else 8880,
        final_capture_epoch=int(driver_gap),
    )
    assert len(segments) == 1 and segments[0].reason == "gap"
    assert segments[0].pcm == pcm(8681)
    assert processor.stats["known_missing_frames"] == (0 if driver_gap else 199)
    assert processor.stats["discontinuities"] == 1


def test_silero_adapter_cpu_state_context_and_reset(tmp_path, monkeypatch):
    import onnxruntime as ort

    content = b"test model"
    monkeypatch.setattr("armenian_speech.vad.MODEL_SHA256", hashlib.sha256(content).hexdigest())
    (tmp_path / "silero_vad.onnx").write_bytes(content)
    (tmp_path / "PROVENANCE.json").write_text(json.dumps({
        "version": "6.2.3", "wheel_sha256": WHEEL_SHA256,
    }))
    calls = []

    class Session:
        def __init__(self, path, *, sess_options, providers):
            assert providers == ["CPUExecutionProvider"]
            assert sess_options.intra_op_num_threads == sess_options.inter_op_num_threads == 1

        def run(self, names, inputs):
            calls.append({key: value.copy() for key, value in inputs.items()})
            return np.array([[0.7]], dtype=np.float32), inputs["state"] + 1

    monkeypatch.setattr(ort, "InferenceSession", Session)
    model = SileroVAD(tmp_path)
    for _ in range(2):
        assert model.probability(np.ones(512, dtype=np.float32)) == pytest.approx(0.7)
    assert calls[0]["input"].shape == (1, 576)
    assert np.all(calls[0]["input"][:, :64] == 0)
    assert np.all(calls[1]["input"] == 1)
    assert calls[0]["state"].shape == (2, 1, 128)
    assert np.all(calls[1]["state"] == 1)
    assert calls[0]["sr"].item() == 16000
    model.reset()
    assert np.all(model._memory == 0) and np.all(model._history == 0)


def test_missing_or_changed_model_fails_without_download(tmp_path):
    with pytest.raises(FileNotFoundError, match="download_vad.py"):
        SileroVAD(tmp_path)
    (tmp_path / "silero_vad.onnx").write_bytes(b"invalid")
    (tmp_path / "PROVENANCE.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        SileroVAD(tmp_path)


@pytest.mark.parametrize("options", [
    {"start_threshold": 0}, {"continue_threshold": 0.8}, {"silence_ms": 10},
    {"max_segment_s": float("inf")}, {"max_segment_s": 0.1},
    {"confirmation_ms": 0}, {"confirmation_ms": 301},
    {"min_rms_db": float("nan")}, {"min_rms_db": 1},
    {"target_segment_s": float("nan")}, {"target_segment_s": 0.1},
    {"target_segment_s": 6}, {"split_silence_ms": 0},
    {"split_silence_ms": 601}, {"split_silence_ms": 99},
])
def test_invalid_segmentation_settings_are_rejected(options):
    with pytest.raises(ValueError):
        VADConfig(**options)


def test_download_checks_wheel_before_extracting_or_writing(tmp_path, monkeypatch):
    import io

    from scripts.download_vad import prepare

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: io.BytesIO(b"invalid"))
    with pytest.raises(ValueError, match="wheel checksum"):
        prepare(tmp_path / "vad")
    assert not (tmp_path / "vad").exists()

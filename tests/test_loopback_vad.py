from dataclasses import replace

import pytest

from armenian_speech.loopback_vad import LoopbackVAD
from tests.test_vad import AlwaysSpeech, block


def incoming(start, when, frames=8000, epoch=0):
    return replace(block(start, frames, epoch=epoch), received_monotonic=when)


def test_idle_flush_has_real_pcm_only_and_resume_keeps_session_pause():
    model = AlwaysSpeech()
    vad = LoopbackVAD(model, 16000, 1, started=100)
    assert vad.push(incoming(0, 101)) == []
    first = vad.idle(102.1, 8000, 0)
    assert len(first) == 1 and first[0].reason == "idle"
    assert len(first[0].pcm) == 16000
    assert first[0].origin_s == pytest.approx(0.5)
    assert vad.idle(104, 8000, 0) == []
    assert vad.push(incoming(8000, 110)) == []
    second = vad.finish()[0]
    assert second.epoch > first[0].epoch
    assert second.origin_s == pytest.approx(9.5)
    assert second.metadata()["timeline_source"] == "callback_receipt_estimate"
    assert second.anchor.input_frame == 8000  # Raw anchor is not rewritten.
    assert model.resets == 2


def test_short_unconfirmed_idle_candidate_never_reaches_asr():
    vad = LoopbackVAD(AlwaysSpeech(), 16000, 1, started=100)
    vad.push(incoming(0, 101, frames=512))
    assert vad.idle(102, 512, 0) == []
    assert vad.stats["rejected_unconfirmed"] == 1


def test_lost_tail_is_a_gap_not_a_clean_idle_phrase():
    vad = LoopbackVAD(AlwaysSpeech(), 16000, 1, started=100)
    vad.push(incoming(0, 101))
    result = vad.idle(102, 9000, 0)
    assert result[0].reason == "gap"
    assert vad.stats["known_missing_frames"] == 1000


def test_arriving_block_after_idle_splits_without_waiting_for_timer():
    vad = LoopbackVAD(AlwaysSpeech(), 16000, 1, started=100)
    vad.push(incoming(0, 101))
    result = vad.push(incoming(8000, 110))
    assert result[0].reason == "idle"
    assert vad.stats["idle_flushes"] == 1
    assert vad.finish()[0].origin_s == pytest.approx(9.5)


def test_raw_gap_inside_burst_preserves_frame_offset_and_unique_epochs():
    vad = LoopbackVAD(AlwaysSpeech(), 16000, 1, started=100)
    vad.push(incoming(0, 101))
    first = vad.push(incoming(9000, 101.5))[0]
    second = vad.finish()[0]
    assert first.reason == "gap"
    assert second.epoch > first.epoch
    assert second.origin_s == pytest.approx(0.5 + 9000 / 16000)


def test_large_normal_callback_blocks_do_not_look_like_idle_gaps():
    vad = LoopbackVAD(AlwaysSpeech(), 16000, 1, started=100)
    vad.push(incoming(0, 101, frames=16000))
    assert vad.idle(101.8, 16000, 0) == []
    assert vad.push(incoming(16000, 102, frames=16000)) == []
    result = vad.idle(104.1, 32000, 0)
    assert len(result) == 1 and len(result[0].pcm) == 64000

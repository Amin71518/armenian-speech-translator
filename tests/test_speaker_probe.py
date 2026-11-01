import numpy as np
import pytest

from scripts.speaker_probe import Extractor, Registry, calibrate, unit


def test_returning_speakers_keep_ids_and_new_speaker_gets_new_id():
    registry = Registry(0.7)
    assert registry.assign([1, 0, 0])["label"] == "Speaker 1"
    assert registry.assign([0, 1, 0])["label"] == "Speaker 2"
    assert registry.assign([0.95, 0.05, 0])["label"] == "Speaker 1"
    assert registry.assign([0, 0, 1])["label"] == "Speaker 3"
    assert registry.assign([0, 1, 0])["label"] == "Speaker 2"
    assert registry.counts == [2, 2, 1]


def test_ambiguity_short_input_and_capacity_do_not_pollute_centroids():
    registry = Registry(0.6, capacity=2)
    registry.assign([1, 0, 0])
    registry.assign([0, 1, 0])
    centers = [value.copy() for value in registry.centroids]
    assert registry.assign([1, 1, 0])["reason"] == "ambiguous"
    assert registry.assign(None)["reason"] == "short_or_silent"
    assert registry.assign([0, 0, 1])["reason"] == "capacity"
    assert registry.counts == [1, 1]
    for before, after in zip(centers, registry.centroids, strict=True):
        np.testing.assert_array_equal(before, after)


def test_calibration_separates_same_and_different_speakers():
    result = calibrate([[1, 0], [0.95, 0.05], [0, 1], [0.05, 0.95]], ["a", "a", "b", "b"])
    assert result["same_pairs"] == 2
    assert result["different_pairs"] == 4
    assert result["different_max"] < result["threshold"] < result["same_min"]
    assert result["balanced_error"] == 0
    with pytest.raises(ValueError, match="same- and different"):
        calibrate([[1, 0], [0, 1]], ["a", "b"])


@pytest.mark.parametrize("value", [[0, 0], [float("nan"), 1], [[1, 0]], []])
def test_invalid_embeddings_fail_explicitly(value):
    with pytest.raises(ValueError):
        unit(value)


def test_short_and_silent_audio_skip_native_extractor():
    # No native extractor attached: any accidental model invocation fails the test.
    extractor = Extractor.__new__(Extractor)
    assert extractor.embed(np.ones(6400, dtype=np.float32) * 0.1) is None
    assert extractor.embed(np.zeros(64000, dtype=np.float32)) is None
    with pytest.raises(ValueError, match="normalized"):
        extractor.embed(np.ones(16000, dtype=np.float32) * 2)

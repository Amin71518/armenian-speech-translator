"""Experimental speaker embeddings/clustering only; never imported by live commands."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from scripts.prepare_diarization import MODELS


def unit(vector):
    value = np.asarray(vector, dtype=np.float32)
    if value.ndim != 1 or not value.size or not np.isfinite(value).all():
        raise ValueError("Expected a finite, nonempty embedding vector")
    length = float(np.linalg.norm(value))
    if length < 1e-8:
        raise ValueError("Zero embedding")
    return value / length


class Extractor:
    def __init__(self, name, threads=1):
        import sherpa_onnx

        directory = Path(".cache/models/speakers") / name
        model = directory / "model.onnx"
        expected = MODELS[name][1]
        provenance = json.loads((directory / "PROVENANCE.json").read_text(encoding="utf-8"))
        if (hashlib.sha256(model.read_bytes()).hexdigest() != expected
                or provenance["sha256"] != expected):
            raise ValueError("Speaker model checksum/provenance mismatch")
        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(model), num_threads=threads, provider="cpu", debug=False,
        )
        if not config.validate():
            raise ValueError("Invalid speaker extractor configuration")
        self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)

    def embed(self, pcm):
        samples = np.asarray(pcm, dtype=np.float32)
        if samples.ndim != 1 or not np.isfinite(samples).all():
            raise ValueError("Expected finite mono samples")
        if not len(samples) or np.max(np.abs(samples)) > 1:
            raise ValueError("Expected normalized samples in [-1, 1]")
        # Abstain on short/near-silent material; no speaker creation or model call.
        if len(samples) < 16000 or float(np.sqrt(np.mean(samples ** 2))) < 0.003:
            return None
        stream = self.extractor.create_stream()
        stream.accept_waveform(sample_rate=16000, waveform=samples)
        stream.input_finished()
        if not self.extractor.is_ready(stream):
            return None
        return unit(self.extractor.compute(stream))


def calibrate(embeddings, speakers):
    """Choose cosine threshold using calibration utterances only (balanced error)."""
    if len(embeddings) != len(speakers):
        raise ValueError("Mismatched labels")
    pairs = [(float(unit(a) @ unit(b)), speakers[i] == speakers[j])
             for i, a in enumerate(embeddings) for j, b in enumerate(embeddings) if j > i]
    same = [score for score, match in pairs if match]
    different = [score for score, match in pairs if not match]
    if not same or not different:
        raise ValueError("Calibration requires same- and different-speaker pairs")
    scores = sorted(set(score for score, _ in pairs))
    candidates = [-1.0, 1.0] + [
        (a + b) / 2 for a, b in zip(scores, scores[1:], strict=False)
    ]

    def error(threshold):
        return (sum(s < threshold for s in same) / len(same)
                + sum(s >= threshold for s in different) / len(different)) / 2

    ideal = (min(same) + max(different)) / 2
    threshold = min(candidates, key=lambda x: (error(x), abs(x - ideal)))
    return {"threshold": threshold, "balanced_error": error(threshold),
            "same_min": min(same), "different_max": max(different),
            "same_pairs": len(same), "different_pairs": len(different)}


class Registry:
    """Bounded online centroids, stable encounter-order IDs, ambiguity abstention."""

    def __init__(self, threshold, margin=0.08, capacity=8):
        if not math.isfinite(threshold) or not -1 <= threshold <= 1:
            raise ValueError("Invalid cosine threshold")
        if not math.isfinite(margin) or not 0 <= margin <= 2 or capacity < 1:
            raise ValueError("Invalid margin/capacity")
        self.threshold, self.margin, self.capacity = threshold, margin, capacity
        self.centroids = []
        self.counts = []

    def assign(self, embedding):
        if embedding is None:
            return {"label": "Unknown", "reason": "short_or_silent"}
        value = unit(embedding)
        scores = [float(value @ center) for center in self.centroids]
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        if not order or scores[order[0]] < self.threshold:
            if len(self.centroids) >= self.capacity:
                return {"label": "Unknown", "reason": "capacity"}
            self.centroids.append(value)
            self.counts.append(1)
            return {"label": f"Speaker {len(self.centroids)}", "reason": "new"}
        best = order[0]
        score = scores[best]
        if len(order) > 1 and score - scores[order[1]] < self.margin:
            return {"label": "Unknown", "reason": "ambiguous", "score": score}
        count = self.counts[best]
        self.centroids[best] = unit(self.centroids[best] * count + value)
        self.counts[best] = count + 1
        return {"label": f"Speaker {best + 1}", "reason": "match", "score": score}

"""Bounded, session-local System speaker tracking; approximate two-second boundaries."""

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np

MODELS = {"campplus": ("model.onnx",
    "aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2")}


def unit(vector):
    value = np.asarray(vector, dtype=np.float32)
    if value.ndim != 1 or not value.size or not np.isfinite(value).all():
        raise ValueError("Expected a finite, nonempty embedding vector")
    length = float(np.linalg.norm(value))
    if length < 1e-8:
        raise ValueError("Zero embedding")
    return value / length


class Extractor:
    def __init__(self, name="campplus", threads=1, directory=None):
        import sherpa_onnx

        directory = Path(directory) if directory else Path(".cache/models/speakers") / name
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

    def assign(self, embedding, *, learn=True):
        if embedding is None:
            return {"label": "Unknown", "reason": "short_or_silent"}
        value = unit(embedding)
        scores = [float(value @ center) for center in self.centroids]
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        if not order or scores[order[0]] < self.threshold:
            if not learn:
                return {"label": "Unknown", "reason": "insufficient_evidence"}
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
        if learn:
            self.centroids[best] = unit(self.centroids[best] * count + value)
            self.counts[best] = count + 1
        return {"label": f"Speaker {best + 1}", "reason": "match", "score": score}


class SpeakerTracker:
    def __init__(self, extractor, threshold=0.47, margin=0.08, capacity=8, *, experimental=False):
        self.extractor = extractor
        self.experimental = experimental
        self.registry = Registry(threshold, margin, capacity)
        self.stats = {"jobs": 0, "parts": 0, "unknown_parts": 0, "compute_s": 0.0}

    def split(self, segment, *, on_decision=None):
        from time import perf_counter

        before = perf_counter()
        self.stats["jobs"] += 1
        samples = np.frombuffer(segment.pcm, dtype="<i2").astype(np.float32) / 32768
        cells = []
        for start in range(0, len(samples), 32000):
            end = min(start + 32000, len(samples))
            pcm = samples[start:end]
            vector = self.extractor.embed(pcm)
            candidate = (self.registry.assign(vector, learn=False) if self.experimental else None)
            # Two half-window probes can expose a transition/mix. They never create
            # identities or train centroids; one-second embeddings are unreliable.
            consistent = True
            halves = None
            half_score = None
            probe_kind = None
            if len(pcm) == 32000:
                halves = [self.extractor.embed(pcm[:16000]), self.extractor.embed(pcm[16000:])]
                probe_kind = "disjoint_halves"
            elif (self.experimental and len(pcm) >= 24000
                  and candidate["reason"] != "match"):
                # Single-utterance views, not accumulated audio or independent samples.
                halves = [self.extractor.embed(pcm[:16000]), self.extractor.embed(pcm[-16000:])]
                probe_kind = "overlapping_short_views"
            if halves is not None:
                if all(v is not None for v in halves):
                    half_score = float(halves[0] @ halves[1])
                consistent = half_score is not None and half_score >= self.registry.threshold
            # Observe pre-update similarities only when requested. No diagnostic
            # values feed assignment, and no embeddings/audio are retained.
            if on_decision is not None:
                counts_before = list(self.registry.counts)
                centers_before = list(self.registry.centroids)
                half_matches = ([self.registry.assign(v, learn=False) for v in halves]
                                if halves is not None else None)
                scores = ([] if vector is None else sorted(
                    [{"label": f"Speaker {i + 1}", "score": float(unit(vector) @ center)}
                     for i, center in enumerate(centers_before)],
                    key=lambda item: item["score"], reverse=True,
                ))
            learn = len(pcm) == 32000 or (self.experimental and probe_kind is not None)
            event = {"label": "Unknown"}
            rescued = False
            if consistent:
                event = self.registry.assign(vector, learn=learn)
            elif self.experimental and candidate["reason"] == "match":
                matches = [self.registry.assign(v, learn=False) for v in halves]
                if all(m["reason"] == "match" and m["label"] == candidate["label"]
                       for m in matches):
                    # Keep the existing identity but never train from a rejected cell.
                    event = {**candidate, "reason": "anchored_match"}
                    rescued = True
            label = event["label"]
            if on_decision is not None:
                reason = event.get("reason")
                if not consistent and not rescued:
                    reason = ("half_embedding_unavailable" if any(v is None for v in halves)
                              else "half_disagreement")
                elif vector is None:
                    reason = "embedding_unavailable"
                rms = float(np.sqrt(np.mean(pcm ** 2)))
                unavailable = ("too_short" if len(pcm) < 16000 else
                               "low_rms" if rms < 0.003 else "extractor_not_ready")
                updated = next((i for i, count in enumerate(counts_before)
                                if self.registry.counts[i] != count), None)
                on_decision({
                    "cell_start_sample": segment.start_sample + start,
                    "cell_end_sample": segment.start_sample + end,
                    "start_s": segment.origin_s + (segment.start_sample + start) / 16000,
                    "duration_s": len(pcm) / 16000, "rms": rms,
                    "embedding_available": vector is not None,
                    "embedding_rejection": unavailable if vector is None else None,
                    "halves_available": ([v is not None for v in halves]
                                         if halves is not None else None),
                    "half_rms": ([float(np.sqrt(np.mean(half ** 2)))
                                  for half in (pcm[:16000],
                                               pcm[-16000:] if len(pcm) < 32000
                                               else pcm[16000:])]
                                 if halves is not None else None),
                    "half_score": half_score, "consistent": consistent,
                    "half_matches": half_matches,
                    "probe_kind": probe_kind, "experimental": self.experimental,
                    "registry_consulted": consistent or rescued,
                    "learn_allowed": consistent and learn,
                    "label": label, "reason": reason,
                    "best": scores[0] if scores else None,
                    "second": scores[1] if len(scores) > 1 else None,
                    "score_gap": (scores[0]["score"] - scores[1]["score"]
                                  if len(scores) > 1 else None),
                    "threshold": self.registry.threshold, "margin": self.registry.margin,
                    "capacity": self.registry.capacity,
                    "counts_before": counts_before, "counts_after": list(self.registry.counts),
                    "centroid_step_cosine": (float(centers_before[updated]
                        @ self.registry.centroids[updated]) if updated is not None else None),
                })
            if cells and cells[-1][2] == label:
                cells[-1] = (cells[-1][0], end, label)
            else:
                cells.append((start, end, label))
        parts = []
        for start, end, label in cells:
            absolute_start, absolute_end = segment.start_sample + start, segment.start_sample + end
            part = replace(segment, pcm=segment.pcm[start * 2:end * 2],
                           start_sample=absolute_start, end_sample=absolute_end,
                           vad_start_sample=max(absolute_start,
                                                min(absolute_end, segment.vad_start_sample)),
                           vad_end_sample=max(absolute_start,
                                              min(absolute_end, segment.vad_end_sample)))
            parts.append((part, label))
        self.stats["parts"] += len(parts)
        self.stats["unknown_parts"] += sum(label == "Unknown" for _, label in parts)
        self.stats["compute_s"] += perf_counter() - before
        return parts

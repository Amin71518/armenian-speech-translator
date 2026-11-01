"""Probe existing VAD boundaries on synthetic turns; source ownership is not speech DER."""

import json
from pathlib import Path

import numpy as np

from armenian_speech.live_vad import LiveVAD
from armenian_speech.microphone import AudioBlock
from armenian_speech.vad import SileroVAD
from scripts.check_speakers import read_rows


def probe(rows, pause_s):
    speakers = list(dict.fromkeys(row["speaker"] for row in rows))[:2]
    sequence = [next(row for row in rows if row["speaker"] == speaker
                     and row["split"] == "evaluation") for speaker in speakers] * 2
    pieces, owners, cursor = [np.zeros(16000, dtype=np.float32)], [], 16000
    for row in sequence:
        pieces.append(row["pcm"])
        owners.append((cursor, cursor + len(row["pcm"]), row["speaker"]))
        cursor += len(row["pcm"])
        silence = np.zeros(int(16000 * pause_s), dtype=np.float32)
        pieces.append(silence)
        cursor += len(silence)
    pieces.append(np.zeros(16000, dtype=np.float32))
    pcm = (np.concatenate(pieces) * 32768).astype("<i2").tobytes()
    vad = LiveVAD(SileroVAD(Path(".cache/models/silero")), 16000, 1)
    segments = []
    for offset in range(0, len(pcm) // 2, 320):
        block = pcm[offset * 2:(offset + 320) * 2]
        segments.extend(vad.push(AudioBlock(block, len(block) // 2, offset,
                                            offset / 16000, offset / 16000)))
    segments.extend(vad.finish("eof"))
    observations = []
    for segment in segments:
        overlaps = {}
        for start, end, speaker in owners:
            count = max(0, min(segment.end_sample, end) - max(segment.start_sample, start))
            if count:
                overlaps[speaker] = overlaps.get(speaker, 0) + count / 16000
        observations.append({"start_s": segment.start_sample / 16000,
                             "end_s": segment.end_sample / 16000, "reason": segment.reason,
                             "source_ownership_s": overlaps,
                             "mixed_sources": len(overlaps) > 1})
    return {"pause_s": pause_s, "segments": observations,
            "mixed_segments": sum(row["mixed_sources"] for row in observations),
            "vad_stats": vad.stats}


def main():
    rows = read_rows()
    report = {"scope": "Concatenated public clips; ownership includes in-file silence, not DER",
              "conditions": [probe(rows, 0.8), probe(rows, 0.0)],
              "audio_saved": False}
    path = Path("reports/stage41_boundaries.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

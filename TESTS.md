# Validation record

## 2026-10-29 Stage 1

- Python 3.13.5; Poetry 2.5.1; local `.venv/`.
- Dependencies installed and pinned in `poetry.lock`. Imports verified:
  faster-whisper 1.2.1, CTranslate2 4.8.4, Transformers 4.57.6,
  PyTorch 2.15.0+cpu (`torch.version.cuda is None`), SentencePiece 0.2.2.
- PyAV 19.0.2 initially failed at actual faster-whisper decoding because it removed
  `metadata_errors`. Added `av<19`; locked PyAV 18.1.0. Real decoding now passes.
- `python -m pytest -q`: **11 passed**. Covers Armenian punctuation inside words,
  corpus WER weighting, empty ASR, invalid references, manifest path resolution,
  pre-model validation, terminal fields, timing boundaries, float WAV -> PCM16 and
  actual faster-whisper decoder compatibility.
- `ruff check .`: passed.
- FLEURS source revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`: 15 distinct
  test sentences, 138.96 seconds total, 15 Armenian and 15 aligned English references.
  Original float WAVs normalized into mono PCM16 16 kHz. Local manifest records hashes.
- The dataset viewer endpoint returned HTTP 500. Preparation therefore explicitly
  uses the original pinned TSVs and streaming archive rather than the viewer endpoint.
- Both models run from cache with `--offline` in the restricted execution environment.

### Actual baseline results

Command: `poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/base.json`

Settings: Whisper Base, CPU INT8, language `hy`, beam 1, no VAD, four CPU threads;
Marian HY -> EN CPU float32, beam 1. No separate warmup. Models loaded once.

| Measurement | Observed value |
| --- | ---: |
| Corpus WER | 137.92% |
| Corpus CER | 98.65% |
| Mean ASR time per WAV | 11.133 s |
| Mean translation time per WAV on ASR outputs | 0.588 s |
| Mean total processing time per WAV | 11.721 s |
| Median total processing time | 11.107 s |
| Maximum total processing time | 24.356 s |
| Corpus RTF | 1.265 |
| Sampled maximum process RSS | 1012.32 MiB |
| ASR loading time | 0.938 s |
| Translation loading time | 5.786 s |
| WAVs processed within 5 s | 0 / 15 |

Whisper snapshot: `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`.
Marian snapshot: `79b0a5051bdb77155f96bb5f091c054ff575b04b`.
Source sentence IDs: 1889, 1921, 1866, 1990, 1685, 1905, 1702, 1747, 1825, 1791,
1980, 1764, 1737, 1788, 1746. Per-file numeric results remain local in `reports/base.json`.

ASR produced mixed scripts, unrelated tokens and two empty transcripts. WER above
100% is possible because insertions add errors beyond the number of reference words.
This baseline is rejected on this screening sample. The ASR stage dominates runtime.

### Translator isolation

Command: `poetry run python scripts/check_translation.py --manifest data/local/fleurs/manifest.jsonl --offline`

All 15 normalized Armenian reference transcripts were translated directly, excluding
ASR and loading from the timed region. Mean translation time: **0.231 s**;
maximum: **0.463 s**. These are different inputs from the corrupted ASR outputs above.

Qualitative comparison of predicted English with aligned FLEURS English reveals
substantial omissions, altered entities and changed meaning. For example, the unit
35 mm becomes 35 meters per second, and photosynthesis becomes bacteria. This is
a preliminary semantic comparison of English outputs, not a qualified Armenian
speaker's review or a formal translation score. Inputs were normalized FLEURS text;
capitalization and punctuation effects have not been separately measured.

Marian is fast enough to merit a lightweight CPU baseline, but these quality failures
mean it is not accepted as the final translator. Better ASR alone will not resolve them.

### Limits and next experiment

This is one 15-clip read-speech screening run. It does not establish representative
conversational accuracy, precise peak memory or live end-of-phrase latency. CPU load
outside this process was not controlled. Reproduce and extend measurements before
making deployment claims.

Keep stage 1 open for deliberate model comparison: verify an Armenian ASR alternative
and compare a stronger translator on the same references. Do not proceed to live
capture with the rejected baseline or hide these failures with automatic fallback.

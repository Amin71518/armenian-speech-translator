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

## 2026-10-29 ASR-only follow-up

See ASR_COMPARISON.md for the benchmark audit and all actual comparison numbers.
Installed onnx-asr 0.12.0; existing ONNX Runtime 1.31.1 runs the Vana INT8 export
on CPU. NeMo is not installed. Source audio and references are unchanged.

`pytest`: **14 passed**; `ruff check .`: passed. New tests verify CPU/INT8 adapter
configuration and file bounds, empty recognition, corpus scoring and ASR timer
boundaries, and explicit Whisper language/task/temperature with lazy consumption.
Both full backends ran successfully in the restricted environment from local files.
The ONNX adapter remains compatible with the existing pipeline contract; no live
components or translation changes were introduced.

## 2026-10-29 Default ONNX WAV pipeline integration

The user accepted Vana-Labs FastConformer INT8 for MVP. Main CLI now defaults to
the existing ONNX adapter; pipeline.py and translation.py are unchanged. Both models
initialize once before iterating input files. Whisper requires explicit selection.

Command: `poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/vana_marian_pipeline.json`

The complete WAV -> ONNX ASR -> unchanged Marian -> terminal chain completed all
15 existing WAVs, with timestamp, WAV label, Armenian and English printed. No model
downloads were needed. Each WAV produced one file-spanning ASR segment.

| Measurement | Observed value |
| --- | ---: |
| Mean complete WAV processing after model loading | 0.452 s |
| Median complete WAV processing | 0.409 s |
| Maximum complete WAV processing | 0.747 s |
| Mean ASR time | 0.172 s |
| Mean translation time | 0.281 s |
| Total processing RTF | 0.0488 |
| ASR model loading including imports | 2.016 s |
| Marian loading including imports | 7.868 s |
| Sampled peak process RSS including both models | 952.68 MiB |
| Corpus ASR WER | 6.67% |
| Corpus ASR CER | 2.03% |

File timers include decoding, ASR, translation and printing HY/EN. They exclude
model loading, WER/CER scoring, reference printing and final report writing. This
is one fresh-process run without separate warmup; all models reuse their instances.
It is not a process-launch-to-exit measurement or a live phrase-end latency test.
Translation remains semantically unreliable on some samples; successfully executing
the full chain does not establish that the English output meets final quality goals.

The JSON report contains numeric measurements and backend metadata, not recognized
text or translations. ONNX fields identify its repo, revision and RNN-T decoder;
the old ambiguous beam_size is split into asr_beam_size and translation_beam_size.

`pytest`: **18 passed**. Four additional tests verify default backend selection,
single ASR/translator initialization across multiple WAVs with terminal output and
correct report metadata, missing-model failure without fallback, and explicit Whisper
selection. Existing 14 tests also pass. `ruff check .`: passed.

## 2026-10-29 Translation comparison and selected NLLB pipeline

TRANSLATION_COMPARISON.md contains all numbers, model revisions, examples and limits.
Correct normalized Armenian references were used for translator selection, without
ASR output. Final greedy second-pass corpus chrF++ / mean / maximum MT:

| Model | chrF++ | Mean MT seconds | Max MT seconds |
| --- | ---: | ---: | ---: |
| Marian | 32.8794 | 0.1857 | 0.3592 |
| NLLB distilled 600M | 57.8622 | 1.3352 | 2.0068 |
| M2M100 418M | 39.6059 | 1.0848 | 1.7375 |

Each ran two passes in its own process, four CPU threads, float32, without sampling.
Final reports recorded connected power at both start and end. NLLB beam=2 was a
separate unsuccessful experiment: chrF++ 56.8279, with higher, unstable processing times.
Initial NLLB setup exposed a Windows cache symlink race and an unwanted Transformers
metadata request. Sequential preparation and local snapshot paths resolved these;
subsequent real inference succeeded in the restricted environment without network.

Default pipeline command: `poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/vana_nllb_pipeline.json`

All 15 WAVs completed: mean 1.6603 s, median 1.6052 s, max 2.8048 s, RTF 0.1792;
mean ASR 0.2043 s and mean MT 1.4560 s; sampled RSS 3076.56 MiB. ASR loading
2.0793 s and NLLB loading 6.2493 s are separate. ASR WER/CER remain 6.67%/2.03%.
The English outputs differ from reference-text evaluation because actual ASR outputs
contain errors and retain punctuation/case. Translation quality is still imperfect.
These file timings do not establish live end-of-phrase latency.

`pytest`: **22 passed**; `ruff check .`: passed. Tests include multilingual source
and target language controls, greedy decoding, local-only pinned snapshots, empty
input, oversized input, unsupported-model rejection and updated default CLI.
SacreBLEU 2.6.0 is a dev dependency; the normal WAV pipeline does not import it.
Historical commands for the Marian-only check now need explicit `--model Helsinki-NLP/opus-mt-hy-en`.

# Armenian speech transcription and translation

Stage 1 is a local CPU experiment: WAV -> Armenian transcription -> English translation
in the terminal. Live capture, VAD and speaker identification are later stages in PLAN.md.
The first baseline has been measured and rejected; see TESTS.md for results and limits.

## Setup on Windows

Python 3.13 and Poetry 2 are required. In this project directory:

```powershell
poetry install
poetry run python scripts/prepare_samples.py
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --report reports/base.json
```

Poetry creates `.venv/` in this directory. PyTorch comes from the official CPU wheel
index; no CUDA is needed. The first inference run downloads the selected models into
`.cache/models/`. Audio preparation uses public dataset download endpoints.
Inference itself is entirely local. After the models are cached:

```powershell
poetry run armenian-speech --wav data/local/fleurs/001.wav --offline
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline
```

Use `--asr-model small` for a deliberate comparison, `--threads 4` to control CPU
threads, and `--help` for all arguments. Model failures are reported without automatic
fallback. Only WAV input is supported in this experiment; keep clips short.

## Baseline candidates

- [Multilingual Whisper Base via faster-whisper](https://github.com/SYSTRAN/faster-whisper):
  CPU INT8, fixed `hy` transcription, beam size 1. Base is a modest starting point for
  CPU latency, not a claim of adequate Armenian quality. ASR consumes each entire WAV
  and exhausts the lazy segment generator before timing ends.
- [Helsinki-NLP/opus-mt-hy-en](https://huggingface.co/Helsinki-NLP/opus-mt-hy-en):
  Marian HY -> EN, CPU float32, greedy decoding, one translation per ASR segment.
  This directly tests the transcript -> translation path requested in the brief.
- Next candidates, if measurements justify them: Whisper Small, a verified Armenian
  fine-tune, and NLLB-200 distilled 600M. No alternate model is selected automatically.

## Evaluation

`scripts/prepare_samples.py` selects the first 15 distinct utterances of 3-15 seconds
in the original Armenian **test** archive order of
[Google FLEURS](https://huggingface.co/datasets/google/fleurs), in source order.
FLEURS is released under CC BY 4.0; attribution and source row metadata are retained
in a local manifest. Downloaded WAV files and reference transcripts stay outside Git.
The script pins source revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd` and records
source filenames and WAV SHA-256 checksums. It streams the original archive and stops
once 15 eligible clips have been read, without saving the whole archive. This avoids
the dataset viewer API, which returned HTTP 500 during initial preparation.
Source float WAVs are decoded through PyAV into mono 16 kHz PCM16 WAVs, recording
both the original and normalized SHA-256 hashes.
This is a small screening sample of read speech, not a representative call benchmark.
Repeated readings of the same sentence are excluded by dataset ID.

The CLI reports per-file ASR, translation, output and total wall time; duration and
real-time factor (RTF = total processing time / audio duration); corpus WER/CER;
model loading times; and a sampled process RSS maximum including model loading.
The first sample includes cold inference; there is no hidden warmup. The 50 ms
memory sampler may miss short peaks. Corpus WER/CER are calculated over all aligned
references, not by averaging file scores. Scores use Unicode NFC, case folding,
punctuation removal and whitespace collapsing, without transliteration. Removing
Armenian punctuation inside a word preserves that word for scoring.
Low RTF and WAV processing below 5 seconds do **not** establish live end-of-phrase
latency: live VAD, queueing and actual speech endings are not measured in stage 1.

English translation quality must be reviewed for meaning preservation, names/numbers,
negation and hallucinations. Do not infer translation quality from WER/CER. The
manifest also contains the English FLEURS text aligned by sentence ID where available,
which is printed beside the output for manual comparison. No invented reference or
automatic translation score is substituted for a human assessment.

To isolate translator errors from recognition errors, feed it the Armenian reference:

```powershell
poetry run python scripts/check_translation.py --manifest data/local/fleurs/manifest.jsonl --offline
```

This diagnostic prints predicted and reference English and translation time. It does
not run ASR, and its input is an ideal transcript rather than actual recognized speech.

An opt-in `--report` JSON contains numeric metrics, sample filenames and model
configuration only. Recognized text and translations appear only in the terminal.
Reports, audio, weights and local references are ignored by Git.

## Structure and validation

`src/armenian_speech/` separates ASR, translation, pipeline, scoring, CLI and terminal
output. Each model is loaded once per CLI process. There is no concurrency in inference
at this stage; only memory sampling uses a background thread. No live-stage modules
are added before the experiment is evaluated.

```powershell
poetry run pytest
poetry run ruff check .
```

Tests use temporary WAVs and fake model adapters to validate scoring, input handling,
pipeline timing boundaries and handling of empty ASR output. They cannot establish
real model accuracy or speed. Decisions and observed results belong in DECISIONS.md
and TESTS.md respectively.

## AI conversation deliverables

Keep every original Codex conversation available for the interview. Before submission,
export **each** project conversation in full and unedited as its own Markdown file in
`chats/`. A summary, generated reconstruction, or placeholder is not a full export.

## Current limitations

This stage does not capture microphone/system audio, identify speakers, handle live
segmentation or verify the required 5 second end-of-phrase latency. Read-speech samples
will need to be complemented by real conversational Armenian. Model choices remain
provisional until actual quality, speed and memory results have been reviewed.

The initial 15-clip screening run of Base + Marian had WER 137.92%, CER 98.65%,
mean WAV processing time 11.72 s, maximum 24.36 s and sampled RSS 1012 MiB.
ASR is the main speed and quality bottleneck. Marian also changes meaning when
given correct normalized Armenian references (mean translation time 0.231 s).
These defaults are retained to reproduce the failed baseline, not as accepted models.
Stage 1 continues with deliberate model comparisons before live implementation.

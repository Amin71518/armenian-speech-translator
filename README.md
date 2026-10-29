# Armenian speech transcription and translation

Stage 1 is a local CPU experiment: WAV -> Armenian transcription -> English translation
in the terminal. Live capture, VAD and speaker identification are later stages in PLAN.md.
Vana-Labs FastConformer RNN-T INT8 is the accepted MVP ASR and default WAV backend.
NLLB-200 distilled 600M is the default translator (CPU float32, greedy). Translation
quality limitations remain; see TRANSLATION_COMPARISON.md for the measured comparison.

## Setup on Windows

Python 3.13 and Poetry 2 are required. In this project directory:

```powershell
poetry install
poetry run python scripts/download_asr.py
poetry run python scripts/download_translation.py --model nllb
poetry run python scripts/prepare_samples.py
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/vana_nllb_pipeline.json
```

Poetry creates `.venv/` in this directory. PyTorch comes from the official CPU wheel
index; no CUDA is needed. The download script prepares the pinned ONNX model in
`.cache/models/vana/`. The CLI requires that directory and does not download or
replace the ONNX model automatically. The translation download script prepares a
pinned snapshot in `.cache/models/translation/`; NLLB/M2M100 inference loads that
local directory, including its tokenizer. No NeMo is required. Audio preparation uses public endpoints.
Inference itself is entirely local. After both models are cached:

```powershell
poetry run armenian-speech --wav data/local/fleurs/001.wav --offline
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline
```

Use `--asr-model PATH` for another prepared ONNX directory; otherwise the CLI uses
`--cache-dir` followed by `vana/`. ONNX requires mono PCM16 16 kHz WAV. Use
`--threads 4` to control model CPU threads and `--help` for all arguments.
Missing ONNX files are an error with preparation instructions; there is no fallback.
Whisper is available only through explicit `--asr-backend whisper`, for example
`--asr-backend whisper --asr-model base`; its default model is Base. A model name
alone does not switch the backend. Keep WAV clips short.

## Models

- [Vana-Labs FastConformer Armenian](https://huggingface.co/Vana-Labs/stt-fastconformer-armenian):
  default ASR, RNN-T INT8, ONNX Runtime CPU, revision
  `ec92cef52199c3874681321b13853e8fe602d23f`. Accepted for MVP after the same
  15-WAV comparison (WER 6.67%, CER 2.03%). Loaded once before the file loop.

- [Multilingual Whisper Base via faster-whisper](https://github.com/SYSTRAN/faster-whisper):
  historical baseline, available explicitly for comparison. CPU INT8, fixed `hy`
  transcription, beam size 1 and the documented temperature schedule. ASR consumes
  each entire WAV and exhausts the lazy segment generator before timing ends.
- [NLLB-200 distilled 600M](https://huggingface.co/facebook/nllb-200-distilled-600M):
  default translator, CPU float32, greedy, one translation per ASR segment;
  `hye_Armn` -> forced `eng_Latn`, pinned revision
  `f8d333a098d19b4fd9a8b18f94170487ad3f821d`. Input limit 512 tokens; oversized
  input is rejected. On correct reference text: chrF++ 57.86 versus Marian 32.88.
  This is a research model under CC-BY-NC 4.0, not a general commercial deployment license.
- [M2M100 418M](https://huggingface.co/facebook/m2m100_418M): tested reserve,
  chrF++ 39.61, lower quality than NLLB on these references. MIT license.
- [Marian HY EN](https://huggingface.co/Helsinki-NLP/opus-mt-hy-en): historical
  translator baseline, still available explicitly with `--translation-model
  Helsinki-NLP/opus-mt-hy-en`. Supported translation IDs are exactly these three;
  there is no automatic model switching after errors.

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
poetry run python scripts/check_translation.py --manifest data/local/fleurs/manifest.jsonl --offline --report reports/nllb_translation.json
```

This diagnostic prints predicted and reference English and translation time, and
runs two passes by default. It does not run ASR. `--model` selects a supported model;
`--beams` explicitly tests another decoding configuration. Its optional local report
contains timing, chrF++, power state and three research examples. SacreBLEU is a dev
dependency, separate from the WAV runtime. Full results are in TRANSLATION_COMPARISON.md.

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
will need to be complemented by real conversational Armenian. Vana is accepted as
the MVP ASR; translator quality and broader conversational evaluation remain unresolved.

The initial 15-clip screening run of Base + Marian had WER 137.92%, CER 98.65%,
mean WAV processing time 11.72 s, maximum 24.36 s and sampled RSS 1012 MiB.
ASR is the main speed and quality bottleneck. Marian also changes meaning when
given correct normalized Armenian references (mean translation time 0.231 s).
The old configuration remains available explicitly for reproducibility. Vana is now
the default ASR. NLLB now replaces Marian as the default translator. Stage 1 continues.

The earlier ONNX -> Marian -> terminal chain was run offline on all 15 WAVs:
mean processing 0.452 s, maximum 0.747 s, RTF 0.0488, sampled RSS 952.68 MiB.
ASR loading was 2.016 s and translator loading 7.868 s, excluded from file processing.
These numbers establish successful integration and WAV processing speed; they do not
establish translation quality or live phrase-end latency. See TESTS.md for details.

The selected ONNX -> NLLB -> terminal chain completed all 15 WAVs offline:
mean 1.660 s, maximum 2.805 s, RTF 0.1792, sampled RSS 3076.56 MiB.
ASR/NLLB loading took 2.079/6.249 s, excluded from file processing. Final measurements
used connected power. Meanings, names and longer sentences can still be mistranslated;
this does not establish the 5 second live target or final call quality.

## ASR-only comparison

The Vana-Labs FastConformer RNN-T INT8 adapter implements the existing `transcribe`
interface. The translation module and pipeline are unchanged. NeMo is not required.
The comparison runner never imports or loads Marian. Downloads and inference are
separate; inference reads local artifacts only and explicitly selects the CPU provider.

```powershell
poetry run python scripts/download_asr.py
poetry run python -m armenian_speech.benchmark --backend whisper --passes 2 --report reports/whisper_asr.json
poetry run python -m armenian_speech.benchmark --backend whisper --whisper-decoding greedy --passes 2 --report reports/whisper_greedy.json
poetry run python -m armenian_speech.benchmark --backend onnx --limit 1 --passes 1 --report reports/onnx_smoke.json
poetry run python -m armenian_speech.benchmark --backend onnx --passes 2 --report reports/vana_asr.json
```

Run commands sequentially in fresh processes. Each model is loaded once per process;
pass 1 includes first inference, pass 2 reuses the model. Times include WAV decoding
and ASR, and exclude scoring and terminal output. RTF is ASR seconds / audio seconds.
RSS includes model loading and all passes in that process. File SHA-256 checksums
must match the existing manifest. Reports contain numeric metrics and three explicitly
requested recognition examples for the research comparison; they are ignored by Git.
No general transcript logging is added to the application.

Audit correction: the original Whisper run used faster-whisper's default temperature
schedule `[0, 0.2, 0.4, 0.6, 0.8, 1]`. Beam size 1 alone does not ensure greedy decoding.
The schedule can trigger repeated decoding and stochastic outputs. `--whisper-decoding
greedy` is a separately labelled experiment with temperature 0, never a silent change
to the original baseline. These settings are unrelated to replacing failed models.

The ONNX adapter returns one segment spanning the file, or no segments for empty text.
Those bounds are not detected phrase or word timestamps. The CPU default preprocessor
in onnx-asr 0.12 is its NumPy implementation; the downloaded model's `nemo80.onnx` is
retained as source provenance, not silently substituted into that implementation.

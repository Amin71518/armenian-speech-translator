# Validation record

## 2026-11-01 Delivery documentation and chat export validation

The author selected the runtime snapshot after the call and authorized project
completion documentation, deferring GitHub. Runtime/ASR/MT/WAV behavior is frozen.
**222 passed in20.05s**, Ruff and Poetry passed. Four new exporter tests supplement
the prior218runtime/research cases; they do not establish model quality.
Current commands, artifact checks, limitations and deferred items:
[VALIDATION_REPORT.md](VALIDATION_REPORT.md). JUnit is local at
reports/submission_release_tests.xml. No live devices, fresh model benchmark,
recording, commit or push was used for documentation preparation.

## 2026-11-01 Opt-in matching trial on exact user excerpts

Final production tests:216 passed in19.54s; Ruff/Poetry passed. JUnit:
reports/speaker_trial_tests.xml. Default parity with exact first4.2 reference on
150jobs/169cells remains identical (reports/first42_parity_after_trial.json).
Actual source/negative controls and full real-worker results are recorded in
SPEAKER_MATCHING_TRIAL.md; do not summarize its2IDs/0Unknown as general stability.
Known short-channel duplicate IDs and overlap mistakes keep the change opt-in:
--experimental-speaker-matching. Existing ASR/MT/WAV models/contracts unchanged.
Release boundary checks:218 passed in19.98s; reports/speaker_trial_release_tests.xml.
Adverse candidate/production parity report:
reports/speaker_candidates_production_verified.json. Both default and opt-in
production labels/durations match their offline counterparts on every control.

## 2026-11-01 First4.2 diagnostic observation step

Before edits: **194 passed in20.26s**. After adding opt-in speaker decision events
and the public-fixture probe: **209 passed in23.08s**, Ruff and Poetry checks passed.
The added tests verify identical PCM/labels/centroids with observation on/off,
abstention/capacity/ambiguity reasons and pre-update scores; real Windows spawn
verifies System events even when ASR is empty/filtered, Me isolation, opt-in output,
paired HY/EN and normal job accounting/cleanup. Probe scoring has a separate
regression for duplicate IDs and cross-person assignments with zero Unknown.

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest-speaker-diagnostics-final --junitxml=reports/speaker_diagnostics_tests.xml
poetry run ruff check .
poetry check
poetry run python -m scripts.check_speaker_decisions --baseline .cache/first42-speakers-baseline.py --report reports/speaker_decisions_verified.json
```

Exact baseline SHA and full protocol/results: DIARIZATION_DIAGNOSIS.md. Real native
CAMPPlus/Silero, existing public fixtures, three comparison arms. All labels,
boundaries, PCM, centroids/counts and extractor input sequences match first4.2.
Clean2s:3/14 Unknown from half disagreements. Synthetic300–3400Hz after clean
enrollment: five IDs for three voices, two false-new IDs,2/14 subsequent Unknown;
16s under duplicate own-person IDs, zero observed cross-person assignments on this
tiny reused series. Gain×0.1:8/14 subsequent Unknown, six half-unavailable and two
half-disagreement refusals. These are not new call accuracy/DER measurements.

Initial verification exposed two compatibility failures in System capture helpers
using microphone-parser Namespaces without the new field. Summary now reads the
optional flag with getattr(..., False); final209-test run passed. Initial Ruff caught
loop callback binding and one unused import; both corrected. No failed check is
counted as a pass. Models and original WAV implementation remain unchanged;
their prior WAV metrics are historical and were not remeasured in this step.
No live capture/audio recording or commit. Stage4.3 acceptance remains pending.

Follow-up offline control: reports/speaker_decisions_with_frozen_control.json.
Original three arms remain identical on150jobs/169cells. Freezing matched centroid
updates still allows all new IDs; synthetic bandwidth series worsened5->6IDs,
2->3duplicates,0->2s cross-person assignments. Source-channel replay returns1/2/3
under both policies. This rejects freezing as a fix on this series and does not
establish Armenian-call quality. The control is scripts-only, absent from live.
Final control regression: **210 passed in23.81s**, Ruff and Poetry passed.
JUnit: reports/speaker_diagnostics_control_tests.xml. Added coverage proves the
offline control freezes matches while still registering an unrestricted new voice
under the existing capacity. No further live-rule changes followed these checks.

Stage 1 is complete. Entries dated 2026-10-29 are historical; their commands and
model availability describe the code at that time (up to commit 0aabc46).
Current post-cleanup commands and Stage 2 acceptance criteria are at the end.

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
At that point, historical Marian-only commands required explicit
`--model Helsinki-NLP/opus-mt-hy-en`; this option was later removed in cleanup.

## 2026-10-30 Stage 1 legacy cleanup validation

Before changes: HEAD 0aabc46; **22 passed**, Ruff passed. Local JSON reports confirm
ASR WER 6.6667%, CER 2.0293%, second-pass mean 0.1394166 s; NLLB reference-text
chrF++ 57.862188; full WAV mean 1.6603357 s, max 2.8047758 s, RSS 3076.5625 MiB.
No discrepancy with the supplied rounded results was found.

After cleanup, in the synchronized Poetry environment:

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest-after-cleanup
poetry run ruff check .
poetry check
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/stage1_cleanup_pipeline.json
poetry run python -m armenian_speech.benchmark --passes 2 --report reports/stage1_cleanup_asr.json
poetry run python scripts/check_translation.py --manifest data/local/fleurs/manifest.jsonl --offline --passes 1 --report reports/stage1_cleanup_translation.json
```

- **16 tests passed**, Ruff passed, `poetry check` passed. Six obsolete cases removed:
  Whisper decoder, Whisper adapter, Whisper CLI selection, Marian/M2M100 parameter
  cases and unsupported translation-model selection. Active pipeline/metrics/ONNX/
  NLLB tests retained and adapted, including once-only loading across two WAVs.
- `poetry run pytest` failed collection because that entry point did not put the
  repository root on sys.path for tests/scripts namespace imports. The verified
  command above uses `python -m pytest`, which does. No application change was needed.
- A later check of `poetry run python -m pytest -q` without the explicit temp path
  produced 11 passes / 5 setup errors: the sandbox Windows Temp pytest directory
  could not be created. Documentation therefore includes `--basetemp .cache/pytest`
  and `-p no:cacheprovider`. With this exact command, all 16 tests passed again.
- `poetry lock` and `poetry sync` succeeded: 0 installs, 0 updates, 5 removals.
  faster-whisper, ctranslate2, sacremoses, joblib and cloudpickle are absent from
  both the locked package list and installed environment. Remaining versions are
  unchanged. Names in upstream optional-extra metadata are not installed packages;
  Poetry-generated metadata is retained rather than edited manually.
- CLI and download helper `--help` work; Python source parses; searches find no
  imports/branches for removed implementations in src/, scripts/ or tests/.
- Original 15 WAV hashes and manifest SHA-256 match:
  `8d7e72f87970345fc5dd454f3f0368d63fcfae325eaf7a7185cf940dd582854c`.
- Both real models loaded from their original pinned local revisions; all 15 WAVs
  printed HY/EN to the terminal offline. Each loaded once, no alternate model used.

| Full WAV regression | Result |
| --- | ---: |
| Files / total audio duration | 15 / 138.96 s |
| WER / CER | 6.67% / 2.03% |
| Mean / median / max processing | 2.1025 / 1.9143 / 3.4322 s |
| RTF / sampled RSS | 0.2270 / 3076.07 MiB |
| ASR / NLLB loading, excluded from file time | 2.7704 / 9.9867 s |

ASR-only runner, two passes: mean 0.4133 / 0.3216 s; max 1.1428 / 0.4775 s;
second-pass RTF 0.03472; RSS 453.39 MiB; same WER/CER both passes.
Translation runner, one pass over correct references: chrF++ **57.862188**,
mean 1.8526 s, max 2.6458 s, RSS 2754.84 MiB. Its report recorded battery power
at both start and end (40% → 39%); the original final translator runs used AC power.

These new timings are slower than the original results and are retained separately.
No causal performance comparison is established: power conditions differ in the
recorded translation runs, and load/thermal conditions were not controlled across
historical and cleanup runs. The new WAV/ASR reports do not record power. Models, decoding,
sample order and existing processing logic are unchanged. No timing tuning or repeated
runs to select faster values were performed.

File timers still include decoding, ASR, translation and terminal HY/EN printing;
loading, scoring and JSON writing are separate. **Ready-WAV processing does not prove
live end-of-phrase latency ≤5 seconds.** No capture, VAD or queue was tested or added.

Git checks: cache/model/audio/report/.env paths are ignored; tracked and unignored
candidate files contain no model/audio artifacts or detected credential patterns.
This is a pattern scan, not a guarantee that every possible secret can be identified.
Pre-existing staged deletion of chats/README.md was left untouched; no chat exports
were found on disk. Full actual Codex exports remain required before submission.
No commit was created during this cleanup.

## Stage 2 acceptance criteria

Stage 2.1–2.3 implementation and actual results are recorded below.
Stage 2.4 remains planned; its latency acceptance criteria are not yet satisfied.

### 2.1 Microphone Capture

- Enumerate input devices and select one explicitly; verify invalid/unavailable
  devices fail clearly. Confirm actual sample rate, channels and buffer format.
- Capture continuously for an agreed test interval with counters/status for dropped
  audio or device errors. First step runs without VAD and ASR/translation models.
- Ctrl+C closes the stream and releases the device; another capture can start.

### 2.2 VAD + Segmentation

- On known speech/silence input, check speech start/end, silence-only behavior,
  short pauses, utterance edges and absence of lost or duplicated samples.
- Verify pre-roll, trailing silence and a maximum segment length agreed in the plan;
  define handling of long speech and partial final buffers. Check real device format
  conversion against the chosen VAD and ASR requirements.

### 2.3 Producer–Consumer Pipeline

- Slow inference must not block the audio callback/capture. Reuse loaded
  FastConformer and NLLB instances; preserve terminal HY/EN output and WAV CLI.
- Use a bounded queue of completed segments. Test full queue and prolonged slow
  consumer; the approved overflow policy must be explicit and observable, with
  queue depth/wait and any dropped segments counted. Memory must stay bounded.
- Ctrl+C stops producers and worker without deadlock; define queued/in-progress
  segment handling and propagate errors without hidden fallback.

### 2.4 Live Latency Testing

- Use a monotonic timeline mapped to capture samples. Record actual speech end,
  VAD decision, enqueue/dequeue, ASR, MT and completed terminal output.
- E2E latency = terminal output time minus actual speech-end time, including VAD
  hangover, buffering and queue wait. Do not start the timer at the VAD decision.
  Validate end timestamps against independently labelled speech endings in a
  controlled live/replayed recording; state the annotation/timestamp uncertainty.
- On the agreed phrase set, check **≤5 seconds per phrase** and report mean,
  percentiles, maximum and violations; low average or RTF alone is insufficient.
  Include varying phrase lengths, pauses, sustained capture and queue stress.
- Run existing unit tests, Ruff and the same 15-WAV pipeline as regression; compare
  WER/CER, reference-text chrF++ and performance with Stage 1, documenting changes.
- No System Audio, Speaker Diarization, GUI, server or database in this stage.

## 2026-10-30 Stage 2.1 microphone capture validation

Before Stage 2 edits, the exact documented pytest command passed **16 tests**;
Ruff and `poetry check` passed. Environment: Windows 11 x64, Python 3.13.5,
Poetry 2.5.1, project-local `.venv`. sounddevice and CFFI were absent.

Poetry installed sounddevice 0.5.6, cffi 2.1.1 and pycparser 3.12, using the
project-local `.cache/poetry` and disabling keyring for that command after a
Windows CredRead access error. Network access required the sandbox escalation.
No existing package version changed; the Stage 1 legacy removals remain intact.
PortAudio reports V19.7.0-devel (revision unknown). No VAD package was installed.

Commands used for input enumeration and real finite capture:

```powershell
poetry run python -m armenian_speech.microphone --list-devices
poetry run python -m armenian_speech.microphone --device 1 --duration 5
poetry run python -m armenian_speech.microphone --device 9 --duration 5
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --duration 5
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --duration 60
```

Five input entries were enumerated: MME input mapper / Intel microphone, DirectSound
input mapper / Intel microphone, and Intel Microphone Array over WASAPI. Only input
devices appear; selection requires an explicit index. Device indices are local and
can change. This was real device access, not a mock-only validation.

| Actual capture | Observed result |
| --- | --- |
| MME device 1, mono int16 16 kHz, requested 5 s | 192 blocks, 79,872 frames / 4.992 s; closed |
| WASAPI device 9 at default 16 kHz | Clear `Invalid sample rate` failure, exit 1; no alternate rate attempted |
| WASAPI device 9, mono int16 48 kHz, requested 5 s | 499 blocks, 239,520 frames / 4.990 s; closed |
| WASAPI device 9, requested 60 s | 5,999 blocks, 2,879,520 frames / 59.990 s, wall 60.041 s; closed |

All successful finite runs had zero input overflow/underflow events and zero
application queue drops. The 60 s run had no pending raw blocks at shutdown.
Its maximum normalized peak was 0.107605, confirming a changing input signal;
speech intelligibility, Armenian recognition and translation were not evaluated.
The opened stream reported input latency 0.026 s for MME and 0.022 s for WASAPI.
Rates/formats are what the backend delivers to the application, not measured
physical ADC-clock accuracy. No audio or recognized text was saved.

Timestamp observations: MME returned zero ADC/callback times. WASAPI ADC times
advanced monotonically, but were about 10 ms later than corresponding callback
times: all 5,999 blocks in the minute run triggered `adc_after_callback_events`.
No zero, nonfinite or nonmonotonic WASAPI ADC times occurred. These observations
are recorded without changing the timestamps or claiming valid speech-end timing.
Stage 2.2–2.4 must validate/calibrate the audio clock and any resampling delays.

Ctrl+C was tested using real Windows `GenerateConsoleCtrlEvent(CTRL_C_EVENT, 0)`
delivered to a child in a separate hidden console, with stdout captured. This avoids
the tool terminal's interrupt path, which terminated the process with Windows code
0xC000013A before a summary was captured; that path is not counted as graceful.

- Direct project Python: exit **130**, `stopped_by=ctrl_c`, `stream_closed=true`;
  176 blocks / 84,480 frames captured, 480 pending frames reported at shutdown.
- The same test with `poetry run python -m ...`: child printed the same successful
  close summary, 181 blocks / 86,880 frames, 480 pending; Poetry's parent returned
  **1** after also receiving Ctrl+C. Do not confuse its code with a device failure.
- Following both interrupts, a real 3 s capture reopened the same device:
  299 blocks / 143,520 frames / 2.990 s; zero driver events or queue drops; closed.
  A fresh-process check found none of `torch`, `transformers`, `onnxruntime`,
  `onnx_asr`, `silero_vad` in `sys.modules` after running capture.

A separate 5 s real-input overload check wrapped the main-thread peak conversion
with a 50 ms sleep per consumed block; production code was not changed. The callback
captured 500 blocks / 240,000 frames and reported no driver overflows. The 32-block
raw queue remained bounded: 369 incoming blocks / 177,120 frames were dropped,
47,520 frames processed, 15,360 pending. Accounting matches exactly:
240,000 = 177,120 + 47,520 + 15,360. This tests the raw capture buffer, not the future
VAD/ASR consumer or completed-segment queue.

Final automated checks:

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest
poetry run ruff check .
poetry check
```

**34 tests passed**, Ruff passed, `poetry check` passed. The 18 new cases cover
buffer copying and timestamps/sample indices, exact queue-overflow accounting,
timestamp anomalies, callback/stream failures, Ctrl+C closure/reopening, finite
capture, input-only enumeration, unsupported formats and invalid arguments.
These controlled cases complement the real device checks; they do not replace them.

Existing WAV sources and all 16 original tests were retained. The 15-WAV model
regression was not rerun in this capture-only substage; run the documented
`reports/stage2_wav_regression.json` command after live inference integration.
No models or VAD were connected to capture, no latency ≤5 s claim is made,
and no System Audio, diarization or commit was added.

## 2026-10-31 Stage 2.2 VAD/segmentation validation

The user authorized 2.2 after inspecting the 2.1 trial. Before edits, all **34 tests**
passed. Existing Stage 1 edits and the staged deletion of chats/README.md are retained.

### Runtime and prepared model

- Actual Windows/Python 3.13.5 inference passed with Silero VAD 6.2.3 ONNX,
  ONNX Runtime 1.31.1 CPUExecutionProvider, intra/inter-op threads=1,
  NumPy 2.5.4 and PyAV 18.1.0. No ASR/MT model is used by this mode.
- No new packages were installed or removed. Existing NumPy is declared as a direct
  dependency and Poetry regenerated the lock metadata without changing versions.
  No silero-vad, TorchAudio, TorchCodec or NeMo Python package was installed.
- `poetry run python scripts/download_vad.py` was run successfully with network
  permission. It downloads a pinned upstream wheel as data, verifies its hash,
  extracts only ONNX/MIT license, verifies the model hash and writes provenance.
  Runtime loads only prepared local files and verifies hashes without network.
- Wheel SHA-256: `7b7f5436cfcb02fae583a05b512ea96467fd449fe54cb49a5e4f06c51a1e43b8`.
  Model SHA-256: `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.
  These artifacts and the license remain in ignored `.cache/models/silero/`.

### Controlled segmentation/conversion checks

Final automated command: `poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest`.
**61 passed** (34 existing + 27 new). `poetry run ruff check .` and `poetry check` passed.

- Exact byte/sample assertions cover pre-roll, trailing silence, minimum speech,
  hysteresis, short pauses, silence-only input, multiple phrases, maximum duration,
  continuous long-speech concatenation, final partial windows and no shared samples.
- Streaming resampling at 16/44.1/48 kHz and stereo matches one-shot conversion
  exactly across arbitrary 137-frame input chunks, including the flushed filter tail.
  Final duration is within one output sample of the rational rate conversion.
  A 12 kHz tone is attenuated below 1% of the 1 kHz tone's RMS when downsampling
  48→16 kHz, checking anti-aliasing rather than naive sample decimation.
- Tests verify local hash validation, CPU thread/provider settings, recurrent state,
  64-sample model context, normalization, missing-model failure without downloading,
  queue/driver gaps, backwards input indices, EOF losses with no subsequent block,
  pending-buffer drain on Ctrl+C and closure without retry after VAD failure.
- A separate deterministic stress check ran 10 seeds × 10,000 probability windows
  with a short 0.7 s maximum. PCM bounds, duration caps, VAD bounds and non-overlap
  passed. This was a state-machine check, not evidence of real speech quality.

### Actual-model offline streaming screening

```powershell
poetry run python scripts/check_vad.py --passes 2 --report reports/stage2_vad_screening.json
```

The existing 15 WAV checksums were verified. Each file had 1 s of known digital
silence inserted before and after it, then was replayed in 511-sample chunks.
The same loaded Silero instance was reset per file. A separate 5 s digital-silence
control emitted **0** segments. Both corpus passes found speech in **15/15** files,
emitting **16** segments per pass. 004.wav split into two contiguous segments at
the cap; 014.wav reached the cap during end hangover but emitted only one segment.
Every emitted segment was at most 192,000 samples, with non-overlapping bounds.

| Final offline screening, both passes | Observation |
| --- | ---: |
| VAD windows | 10,574 |
| Mean / maximum VAD window wall time | 0.1862 / 1.7009 ms |
| Streaming processing RTF (conversion/framing/VAD/segmentation) | 0.007772 |
| Process CPU seconds / audio seconds | 0.007629 |
| Sampled RSS | 90.92 MiB |
| Peak retained PCM buffer | 192,192 samples |

The report records battery power, 45% at start/end. A first screening run recorded
mean/max 0.2043/4.2951 ms and RSS 91.64 MiB at 47% battery; its numeric report is
retained as `reports/stage2_vad_screening_initial.json`. Screening was repeated to
fix a report field collision (segment count overwrote metadata) and include raw
speech-end capture anchors. These are separate observations, not a tuning/speedup
claim. Cold load is separate; CPU load/power conditions were not tightly controlled.
No WAV ASR or translator benchmark ran concurrently with VAD screening.

Inserted silence provides known nonspeech regions, not independently labelled
speech onset/end. These results do not establish conversational VAD accuracy,
word-edge preservation or real speech-end latency. No speech text/audio was saved.

### Real microphone, Ctrl+C and overload

Device: Intel Microphone Array, current WASAPI index 9, mono PCM16 48 kHz input,
stateful conversion to mono PCM16 16 kHz. Command:

```powershell
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --vad --duration 60
```

The minute check used a fresh process wrapper for sampled memory/process CPU:
5,999 blocks, 2,879,520 captured frames / 59.990 s, 959,840 resampled samples,
1,875 VAD windows; zero driver events, queue drops or discontinuities. Closed
normally with no pending frames. Input was quiet (peak 0.001892); **0** phrases
were emitted. This quiet run does not itself demonstrate real voice detection.
VAD wall mean/max was approximately 0.511/1.437 ms per window, total 0.958 s.
Whole-process CPU including VAD initialization was 3.766 s, sampled RSS 88.00 MiB.
Window-level `thread_time` values have Windows timer granularity and should not be
treated as a precise CPU-utilization measurement. Torch/Transformers/onnx_asr
were absent from sys.modules after capture.

A subsequent normal **20 s real-input** run did emit two natural `silence` segments:
nominal bounds [0.116, 11.236) and [11.444, 13.092) s, estimated VAD speech ends
11.136 and 12.992 s. One further short candidate was rejected. Captured 1,999 blocks /
959,520 frames / 19.990 s; 319,840 converted samples, 625 windows. Zero driver events,
queue losses or discontinuities, stream closed, no pending frames. VAD total/max wall
0.355 s / 1.533 ms. Source content/language and physical speech endings were not
independently annotated; the two detections are not a precision/recall evaluation.

Real Windows CTRL_C_EVENT was delivered to a VAD child in a hidden separate console:
exit **130**, stopped_by=ctrl_c, stream_closed=true. It captured 362 blocks /
173,760 frames / 3.620 s, flushed 57,920 normalized samples, including the final
64-sample partial window, and had no pending raw frames. The same device then
reopened for a real 3 s VAD capture: 299 blocks / 2.990 s, zero drops, closed normally.
Active-speech Ctrl+C semantics are additionally checked with controlled probabilities;
the actual interrupt run was quiet. The 2.1 Poetry-parent exit-code caveat remains.

A final real-input overload test injected 50 ms sleep per VAD call without editing
production code. Capture continued: **502 blocks / 240,960 frames**, zero PortAudio
overflow/underflow events, **220 dropped blocks / 105,600 frames** in the bounded raw
queue. Consumer processed 135,360 frames, then drained pending blocks at shutdown:
240,960 = 135,360 + 105,600; pending=0. VAD reported the same 105,600 known missing
frames (including final drops), 77 discontinuities and 45,120 normalized samples.
It emitted 7 explicitly incomplete `gap` candidates, some below the ordinary
minimum; these must not be confused with clean phrases. Shutdown completed in
5.80 s wall time for 5.02 s captured audio. This tests slow VAD/raw buffering,
not the unimplemented completed-segment/ASR queue.

### Timestamp and integration limits

All WASAPI blocks again showed ADC time about 10 ms later than callback time.
Raw anchors are retained, not corrected. Segment metadata carries epoch-relative
sample positions, epoch origin, the observed capture block at estimated VAD speech
end, decision_monotonic and clock_accuracy=unvalidated. Driver-gap duration is unknown;
known queue gaps preserve nominal source indices. No physical speech-end timestamp,
clock drift or resampling-delay calibration has been validated against independent
annotations. That remains part of Stage 2.4; no <=5 s claim is made here.

WAV pipeline/ASR/MT code and original tests are retained; no ASR/translation model
was connected to live capture. The full 15-WAV ASR/MT regression remains required
after Stage 2.3 integration. No System Audio, diarization, transcript/audio saving,
completed-segment worker queue or commit is included in this substage.

## 2026-10-31 Stage 2.3 live pipeline validation

The user confirmed the 2.2 manual trial and authorized 2.3. Baseline: **61 tests**
passed. No dependencies or weights were replaced/installed. Existing FastConformer
INT8 and NLLB greedy load once in one Windows spawn process, before capture begins.

### Automated checks and shutdown policy

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest
poetry run ruff check .
poetry check
```

**73 tests passed** (61 existing + 12 new cases); Ruff and poetry check passed.
Tests use real spawned Windows processes with controlled fake models for failures:

- Once-only factory loading across multiple jobs, ordered `Me HY/EN` output,
  empty-ASR handling, skipped gap counters, closed PCM16 WAV input and cleanup.
- A consumer sleeping for 30 s: submit stays below 0.2 s, a capacity-1 full queue
  drops the incoming job and reports it. A 0.2 s drain deadline forces termination,
  completes cleanup within the 5 s test bound and counts both unfinished jobs.
- Startup/ASR/MT exceptions propagate without fallback; native `os._exit(7)` is
  detected without waiting for a result. Exact temporary WAV/session cleanup is
  checked after both exceptions and process termination.
- Live capture finalizes the real Segmenter and routes the final partial phrase;
  the microphone closes before worker drain. First SIGINT sets a stop flag and the
  original signal handler is restored. Invalid devices fail before model startup.
- Token tests include special-token overhead, all-word preservation, exact limits
  and an oversized indivisible word failing without truncation.

An early real spawn check exposed Windows `PipeConnection.poll()` raising
BrokenPipeError at EOF. It is now treated as channel closure while preserving
received worker errors and checking the process exit/completion counts. Shutdown
uses a separate small control pipe carrying the final accepted-job count, not
Queue.empty() or a sentinel that could block behind a full queue. Queue feeder
joining is cancelled after shutdown/termination; terminated IPC is never reused.

Default live queue: 2 waiting phrases, drop incoming on full with warning and
`dropped_full`. Incomplete gap phrases increment `skipped_gap`. First Ctrl+C closes
capture, drains raw input/finalizes VAD, offers the remainder under the same queue
policy, then drains accepted work for 15 s. Deadline/second Ctrl+C force termination
and report unfinished accepted jobs. Worker errors stop capture with nonzero status.

### Real ASR/MT and actual tokenization

```powershell
poetry run python -m scripts.check_live_pipeline --limit 3 --report reports/stage2_live_worker_replay.json
```

Three checksum-verified WAVs passed through real VAD -> phrase queue -> one real
FastConformer/NLLB worker -> parent terminal. **3 accepted / 3 completed**, HY/EN
printed for all, zero drops/gaps/empty ASR, worker exit 0, temporary sessions removed.
Model revisions match the original pinned revisions. Loading: ASR 1.889 s, NLLB
7.572 s, separate from inference. This helper requires `python -m` for its scripts
namespace imports; direct file launch failed imports before inference and was corrected
to the documented module command without an application sys.path workaround.

This is unpaced file/VAD replay with deliberately paced queue submission. Queue wait
max was **4.051 s**, sum ASR **0.621 s**, sum MT **9.091 s**, maximum VAD-decision to
output **9.549 s**. These measurements explicitly do not demonstrate <=5 s after
real speech, and do not omit the observed backlog. Report power: AC, 44% battery.
Worker RSS immediately after loading was 589.28 MiB; this is a cold mapped-weight
snapshot, not peak model memory and not comparable to full-process sampled peaks.

After finalizing shutdown control, a one-file smoke run was retained separately in
`reports/stage2_live_worker_replay_final.json`: **1 accepted / 1 completed**, exit 0,
ASR 0.141 s, MT 2.212 s, decision->output 2.389 s. This is a separate observation,
not a speedup claim or a representative live latency statistic.

The actual pinned NLLB tokenizer was also checked without loading translation weights:
a constructed 578-token input split into **512- and 68-token** parts (each includes
its own special tokens), with all source words preserved. Numeric result is local
at `reports/stage2_token_split_check.json`. The initial 25-repeat fixture was below
the limit; the successful test increased repetition until the actual count exceeded 512.
The normal WAV translate() path still rejects oversized input rather than splitting.

### Real microphone and Windows Ctrl+C

Full `--live` mode ran on WASAPI device 9, mono PCM16 48 kHz -> 16 kHz VAD.
A real CTRL_C_EVENT was sent to the app's separate hidden console after 30 s of
capture. **3,000 blocks / 1,440,000 frames / 30.000 s**, zero input errors/raw drops,
480,000 resampled samples, 938 VAD windows, no pending frames. Input was quiet;
0 phrases/outputs were produced. The app reported stream_closed=true,
worker_closed=true, worker_exitcode=0, forced_termination=false and exited **130**.
The report is `reports/stage2_live_microphone.json`.

That first controller's immediate PID-existence assertion returned false for its
all-children-exited check despite correct app/worker exit reports. It was retained,
not silently relabelled. A follow-up identity-aware `psutil.wait_procs` check confirmed
both Python processes and the hidden console host exited. This repeat captured
**300 blocks / 3.000 s**, flushed one live candidate on Ctrl+C, printed one HY/EN pair,
completed **1/1** jobs without drops/forced termination, and exited **130**. Its numeric
report is `reports/stage2_live_ctrlc_exit_check.json`. Input content/actual speech
boundaries were not independently labelled; the output is not a quality evaluation.
Afterwards the same microphone reopened in capture-only mode for **199 blocks /
1.990 s**, zero errors/drops, closed normally.

Concurrent real-inference capture check:

```powershell
poetry run python -m scripts.check_live_pipeline --limit 1 --microphone-device 9 --report reports/stage2_capture_under_inference.json
```

One known WAV job was offered, then the actual microphone captured 5 s while the
same worker ran ASR/MT. Two additional microphone VAD phrases were offered, including
the final remainder. **499 blocks / 239,520 frames / 4.990 s**, no driver errors,
raw queue drops or discontinuities. **3 accepted / 3 completed**, phrase queue peak 1,
no full/gap/unfinished discards, worker exit 0; HY/EN arrived before and after capture
closed. This confirms capture continues under real inference load, not that injected
WAV source times are microphone speech times. Actual microphone content was unlabelled.
Maximum queue wait was 0.881 s; decision->output 3.842 s, not physical speech-end latency.

### WAV regression and limits

```powershell
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/stage2_wav_regression.json
```

All **15/15 WAVs / 138.96 s** completed offline, using the original CLI and WAV label.
All 15 WAV hashes match their manifest; manifest SHA-256 remains
`8d7e72f87970345fc5dd454f3f0368d63fcfae325eaf7a7185cf940dd582854c`.

| Stage 2.3 WAV regression | Result |
| --- | ---: |
| WER / CER | 6.67% / 2.03%, unchanged |
| Mean / median / maximum processing | 2.1245 / 1.9724 / 3.5335 s |
| RTF / sampled RSS | 0.22933 / 3072.64 MiB |

New timing observations are retained separately from Stage 1. The WAV report does
not record power, and conditions differ; no causal performance comparison is made.
Existing semantic translation errors remain (e.g. riders rendered as horses).
Reference-text chrF++ and independently labelled conversational quality were not
remeasured in this integration. Benchmarks with real models ran sequentially.

No temporary live session/WAV remained after the checks. No recognized text/audio
was saved to reports, no model fallback was added and no commit was created.
VAD/raw clock anchors still have unvalidated physical accuracy; Stage 2.4 must
measure actual speech-end latency including hangover, queues, inference and output,
reporting every violation. System Audio and Speaker Diarization remain unimplemented.

## 2026-10-31 False-trigger mitigation and quiet live output

The user reported invented phrases while silent, with a distant TV and other noise
in the room, and requested removal of per-second diagnostics. These checks cover
admission rules and output visibility; the reported room audio was not recorded or
labelled, so no false-positive rate or target-speaker separation is claimed.

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest
poetry run ruff check .
poetry check
```

**94 tests passed**; Ruff and Poetry checks passed. Regression cases cover repeated
short probability spikes, consecutive onset confirmation, configurable thresholds,
minimum duration on silence/Ctrl+C/duration/EOF/gap, and preservation of a short
continuation after a valid forced split. The previous shutdown/EOF path could send
unconfirmed tiny fragments to ASR; it now applies the same minimum-duration rule.
Tests also cover the opt-in RMS gate, default acceptance of quiet speech without
that gate, RMS computation over real samples rather than final zero padding,
invalid settings rejected before model loading, quiet live status, and diagnostic
timings from a real Windows-spawned worker using fake models.

Final defaults are start/continue probability **0.65/0.50**, consecutive onset
confirmation **160 ms**, minimum positive speech **300 ms**, RMS gate **disabled**.
The initial onset and pre-roll are retained while awaiting confirmation.

```powershell
poetry run python scripts/check_vad.py --passes 2 --report reports/vad_strict_screening.json
```

The pinned real Silero model detected speech in **15/15 WAVs in each of two passes**,
16 segments per pass, and emitted **0 segments for 5 s of digital silence**. This
unpaced VAD replay does not evaluate ASR word accuracy, conversational noise, or
live latency. Across 10,574 speech windows: mean model call 0.1672 ms, maximum
1.7803 ms, streaming RTF 0.00734, sampled RSS 91.28 MiB. These are separate timing
observations, not a performance comparison with earlier runs.

A trial fixed RMS floor of -50 dBFS rejected **5/15 valid WAVs entirely** in each
pass (003, 005, 007, 009, 010), so it was rejected as a default. Its numeric report
is retained as `reports/vad_strict_fixed_energy_screening.json`; the temporal-only
screen is `reports/vad_strict_temporal_screening.json`. `--min-rms-db` is available
for room-specific adjustment when the background is quieter than the user's voice.
TV speech at comparable levels still passes VAD; these changes do not identify
the intended speaker. No text blacklist or model/decoder change was introduced.

A 12 s real `--live` run exited 0 with **0 periodic status lines, 0 inference timing
lines, and 0 JSON summaries**, while still printing two HY/EN pairs. The input was
unlabelled; those pairs are not evidence that false outputs were eliminated.
`reports/noise_fix_quiet_live.json` contains counts only. The observation wrapper
subsequently failed while echoing Armenian into its own CP1251 console; the UTF-8
application had already exited successfully and the saved numeric report was
independently rechecked. `--diagnostics` restores detailed status and timings.

The existing WAV ASR/MT implementation and dependency files were not modified by
this fix. The earlier Stage 2.3 WAV quality regression above remains the applicable
measurement. No live temporary WAV/session remained after verification, no audio
or recognized text was persisted in the new reports, and no commit was created.

## 2026-10-31 Shorter long-speech fragments, paired output preserved

The user authorized shorter fragments and explicitly required HY and EN to appear
together. The parent still receives one completed result after ASR and translation;
no partial Armenian output was introduced. Config now prefers a 256 ms VAD-negative
pause after 3.5 s (segment start through last positive window, including pre-roll
and internal pauses) and uses a 6 s hard audio limit. Shorter utterances retain the
600 ms silence decision. The earlier-boundary reason is `short_pause`.

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest
poetry run ruff check .
poetry check
```

**113 tests passed**; Ruff and Poetry checks passed. New cases cover early/short
pauses, sub-threshold pauses, quick resumption without overlapping PCM, exact
six-second forced splits, short shutdown tails, retained legacy settings, and
invalid CLI/config combinations before model startup. A Windows-spawned worker
test pauses the translator after ASR: no HY is printed while translation is blocked;
after release exactly one line contains both HY and EN. Existing capture Ctrl+C,
gap handling, queue-full, worker failure and bounded-shutdown tests still pass.

### Actual-model VAD and ASR boundary comparison

```powershell
poetry run python scripts/check_vad.py --passes 2 --report reports/short_segments_vad_screening.json
```

All **15/15 checksum-verified WAVs** had detections in both passes: **27 fragments
per pass**, maximum emitted PCM duration **6 s**, **0 fragments for 5 s digital
silence**. Across 10,574 speech windows: mean model call 1.0630 ms, maximum 8.5044 ms,
streaming RTF 0.04827, sampled RSS 91.83 MiB. These are separate observations under
different host conditions; no causal speed comparison with previous runs is made.

An inline, sequential comparison reused one pinned Silero and one real
FastConformer INT8 instance. Each WAV hash was verified, one second of silence
was added at both ends, and each emitted segment passed through the existing
closed-WAV ASR adapter. The same normalized reference texts were scored after
concatenating ASR results in segment order; hypotheses/audio were not retained.
The previous policy used max=12 s and split_silence=600 ms with otherwise identical
thresholds. Report: `reports/short_segments_asr_comparison.json`.

| VAD + ASR on the same 15 WAVs | Previous policy | Shorter fragments |
| --- | ---: | ---: |
| Detected files | 15/15 | 15/15 |
| Total fragments | 16 | 27 |
| WER | 6.67% | 11.67% |
| CER | 2.25% | 3.72% |

This is an observed **quality regression**, consistent with harder word boundaries
and less context; sample continuity does not guarantee word accuracy. Translation
quality was not independently scored here. These VAD-clipped results must not be
substituted for the original full-WAV pipeline's metrics. The shorter policy remains
tunable, and `--segment-max-s 12 --segment-pause-ms 600` selects the previous behavior.

### Nominal-rate real-worker replay: overload retained

```powershell
poetry run python -m scripts.check_live_pipeline --limit 5 --realtime --report reports/short_segments_realtime.json
```

The helper delivered 20 ms file blocks at nominal 16 kHz, ran actual VAD and one
spawned FastConformer/NLLB worker, polled outputs while feeding, and did not wait
for phrase-queue space. It printed seven completed HY/EN pairs, warned about two
full-queue drops, and exited **1** on the existing **15 s shutdown timeout**.
Observed MT times were about 2.9-10.8 s; some decision-to-output times exceeded 20 s.
A separate nearby host snapshot showed battery power (28%, unplugged) and about
1.49 GiB available memory; it is context, not a causal attribution for the slowdown.

The original helper raised before saving its summary. Counts observed in stdout
are retained explicitly as such in `reports/short_segments_realtime_first_failure.json`;
the missing intended report is not relabelled as a successful run. The helper now
writes actual numeric worker statistics and the error before re-raising; production
queue capacity/drop policy and shutdown deadline were not relaxed.

This replay demonstrates the current overload limitation, not physical microphone
latency or success of the <=5 s target. Stage 2.4 remains open. More frequent jobs
can accumulate faster than CPU translation completes; six seconds bounds only
audio accumulation. No literal 5-6-word segmentation, audio overlap/deduplication,
new model, dependency installation or commit was added.

After the helper update, a separate two-file nominal-rate run completed **3/3 jobs**,
zero drops/forced termination, queue wait maximum **0.0031 s**, MT **1.14-2.26 s**,
maximum VAD-decision-to-output **2.4533 s**, worker exit **0**. Actual report:
`reports/short_segments_realtime_two_files.json`. It covers **20.56 s** of input
including inserted silence. Power was now **AC (29-30% battery)**, unlike the earlier
failed run. This smaller workload and changed conditions do not establish a speedup
or erase the overload failure. HY and EN appeared in the same completed lines.

### Original WAV pipeline regression

```powershell
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/short_segments_wav_regression.json
```

All **15/15 full WAVs / 138.96 s** completed using the original command and WAV label.
**WER 6.67%, CER 2.03%**, unchanged from the original full-WAV baseline. Mean/median/
maximum full-file processing were **2.9539/2.7724/5.1124 s**, RTF **0.31886**, sampled
RSS **3077.40 MiB**. These are whole-file processing times, not physical live latency;
no causal timing comparison is made. Model revisions/greedy decoding are unchanged.
The manifest SHA-256 is still
`8d7e72f87970345fc5dd454f3f0368d63fcfae325eaf7a7185cf940dd582854c`.
Reference translation semantics were not rescored. Real-model checks ran sequentially.

The same **five-file nominal-rate workload** was repeated after the WAV regression,
now on **AC power**: **10 offered / 10 accepted / 10 completed**, zero drops/gaps/
unfinished jobs/forced termination, queue depth peak 1, queue wait maximum **0.5879 s**,
VAD-decision-to-output maximum **2.4831 s**, worker exit **0**. Report:
`reports/short_segments_realtime_five_files_repeat.json`. HY/EN appeared together for
every result. The earlier failed five-file run remains recorded separately; changed
host/power conditions preclude a causal comparison or a general latency guarantee.
All test-created live WAV/session paths were gone after verification. Git index and
unrelated pre-existing dirty files were preserved; no commit was made.

## 2026-10-31 Isolated ASR fragment guard

The user supplied recurring `HY: Հ։`/`Հ.` followed by unsupported English sentences
and asked to suppress small/noisy detections. These lines show one-letter ASR
output amplified by translation. They do not establish the acoustic cause: cough,
breath, background speech or a forced-cut tail cannot be distinguished from text.
No new recording of the user's microphone was made.

The default live guard inspects NFC/casefolded ASR text before tokenization/MT.
It skips results without letters/numbers and single alphabetic characters, while
preserving short words, numbers, Armenian ա/է and the casefold-expanded և ligature.
Accepted text is not normalized for display/translation. Initials inside a longer
name pass; a standalone spelled letter can be lost. `--allow-asr-fragments` disables
the guard. This structural rule does not identify arbitrary nonsense or replace VAD.

Skipped jobs return empty HY/EN plus a reason, do not call translation, and count
as completed + filtered_asr_fragments (not empty_asr, a queue drop, or an actual
terminal-output latency sample). Under diagnostics their timing endpoint is labelled
completion, not output. Default output remains quiet; kept HY/EN remain paired.

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest
poetry run ruff check .
poetry check
```

**138 tests passed**; Ruff and Poetry checks passed. New regression cases cover
both exact user strings, punctuation-only output,
case/spacing/zero-width characters, short yes/no/name responses, numbers and
Armenian single-letter words. A translator that raises on any call verifies that
filtered inputs reach neither tokenizer nor model, and the temporary WAV is gone.
Real Windows-spawned fake-model tests verify suppressed output in quiet/diagnostic
modes, reason/counter reporting, completion/drain accounting, a subsequent valid
short response, and explicit opt-out. Existing error propagation and paired-output
tests remain in the suite.

An inline real-model screening reused pinned Silero and FastConformer INT8 across
all **15 checksum-verified WAVs / 27 emitted segments** with current chunk settings.
For each segment the unchanged ASR path adapter ran once; hypotheses before/after
the text guard were compared in memory. **0 of 27 existing segment results were
filtered**. WER/CER were **11.67%/3.72% both before and after**. Numeric report:
`reports/asr_fragment_guard_screening.json` (including config, manifest hash and
ASR revision). No recognized text/audio is persisted in that report, and the exact
temporary WAV/session was removed. This checks this small speech set; it does not
measure cough rejection or the user's room false-positive rate. The earlier
short-chunk accuracy regression remains unresolved and is not hidden by this guard.

VAD thresholds/durations, models/decoders, dependencies and original WAV processing
were not changed by this fix. The full-WAV regression recorded above remains the
applicable model measurement; it was not rerun for this live-only text condition.
No commit was created, and the existing staged deletion/dirty files were preserved.

## 2026-10-31–2026-11-01 Stage 2.4 latency and stability audit

**Audit executed; physical <=5 s acceptance is not certified.** The user explicitly
skipped listening verification of endpoint annotations and authorized speaker playback
at unchanged Windows volume. `data/latency_endpoints.json` therefore retains
`human_verified=false`. Its intervals were manually selected from 10 ms waveform
RMS plots independently of Silero, not established as phonetic gold. Audio/recognized
text are not saved by the measurement reports. The optional worker observer samples
the endpoint immediately after the paired HY/EN print/flush; this is not a measurement
of terminal pixel rendering. Existing live output and model settings are unchanged.

### Nominal-rate replay and real microphone under load

```powershell
poetry run python -m scripts.check_live_latency --repeat 2 --capture-device 9 --report reports/stage24_replay_5min.json
```

Known WAV audio was delivered at nominal rate, with two seconds between files.
The microphone captured concurrently; it supplied health counters, not model audio.
Do not label this file replay as acoustic microphone latency. Report conditions:
battery, unplugged, **26% -> 22%**. Models loaded once (ASR 6.642 s, MT 22.735 s),
outside inference measurements; revisions match the existing pinned models.

| Observation | Result |
| --- | ---: |
| Input fixture duration | 338.92 s |
| Offered / accepted / completed jobs | 54 / 54 / 54 |
| HY/EN pairs / empty ASR / filtered fragments | 52 / 2 / 0 |
| Phrase queue peak / maximum wait | 1 / 3.1493 s |
| Full/gap/unfinished discards | 0 / 0 / 0 |
| Raw capture blocks / frames | 33,901 / 16,272,480 |
| Captured duration at nominal 48 kHz | 339.01 s |
| Driver status events / raw queue drops | 0 / 0 |
| Maximum file delivery lateness | 23.6973 ms |
| Parent sampled RSS range | 98.15–101.26 MiB |
| Worker sampled RSS after first minute | 3022.79–3051.17 MiB |

Every captured frame was processed/discarded without a permanent recording.
Worker exited 0 without forced termination; stream closed. Sampled memory ranges
describe this run, not a proof that all future sessions are leak-free.

### Endpoint E2E: all cases and uncertainty retained

E2E starts at the independent provisional endpoint interval, including delivery,
VAD hangover, dispatch, queue, WAV preparation, ASR, MT and terminal handoff/flush.
There were **30 planned natural endpoints**: **14 measurable**, **12 definitely within
the 5 s limit under the provisional interval**, **2 threshold-uncertain**, and **16
uncovered/ambiguous**. The last group means that the entire proposed interval was
not covered by a single emitted segment; it is not a claim that 16 outputs were lost.
Do not narrow annotations to fit VAD or count these cases as successful.

| Distribution on the 14 measurable cases only | Midpoint estimate | Upper interval bound |
| --- | ---: | ---: |
| Mean | 4.1641 s | 4.2998 s |
| p50 | 4.0695 s | 4.2070 s |
| p95 | 5.0249 s | 5.1499 s |
| p99 | 5.0354 s | 5.1604 s |
| Maximum | 5.0380 s | 5.1630 s |

Quantiles use linear interpolation. The small selected denominator and unreviewed
labels preclude general latency claims. All non-passing/uncertain cases:

- **1:009.wav:** [4.9130, 5.1630] s; midpoint 5.0380 s.
- **2:009.wav:** [4.8929, 5.1429] s; midpoint 5.0179 s.
- **Both passes of 001, 002, 006, 007, 008, 012, 013, 015:** 16 uncovered/ambiguous
  endpoint intervals; full numeric details remain in the report.

No interval was definitively wholly >5 s; two cross the threshold, so they cannot
be certified <=5 s. Mean measured phase contributions were delivery/VAD **0.5511 s**,
queue **0.8075 s**, ASR **0.2368 s**, MT **2.5319 s**; remaining dispatch/WAV/handoff
time accounts for the rest. MT and queue time are the largest contributors here.

The first runner report omitted an explicit replay-start field. Its recorded output
and phase/reference midpoints recover that origin consistently (span <0.5 ns), marked
as derived in `reports/stage24_replay_analysis.json`. The runner now emits the actual
start and reference timestamps directly. This does not validate a physical ADC clock.

### Real clock consistency

`reports/stage24_clock_probe.json`: 10 s of real WASAPI input, **999 blocks**, zero
errors/drops, but **999/999 ADC timestamps about 10 ms ahead of callback entry**.
Stream/perf_counter offset span was **0.0396 ms**. During the long run, offset span
was **0.1026 ms**, maximum clock-query bracket **0.1894 ms**, with **389 nonmonotonic
ADC events** and future-dated ADC on every callback. These are actual observed
inconsistencies; query precision is not physical ADC accuracy. No guessed correction
or subtraction of driver latency was introduced.

### Acoustic attempts: no usable end-to-end result

```powershell
poetry run python -m scripts.check_acoustic_latency --input-device 9 --output-device 8 --report reports/stage24_acoustic.json
poetry run python -m scripts.check_acoustic_latency --input-device 9 --output-device 8 --samples 001.wav 003.wav 006.wav --peak 0.3 --report reports/stage24_acoustic_normalized_repeat.json
```

The six-file attempt captured **7732 blocks**, but emitted **0 VAD phrases** and had
**0/6 reliable waveform alignments** (correlations 0.008–0.103 vs threshold 0.20).
It also had **9 dropped raw blocks / 4320 frames**, one accounted discontinuity.
The original helper opened output after starting input, potentially blocking the
consumer during initialization; the revised helper opens both before starting.
The first observation is retained and not relabelled as passing.

The three-file repeat on 2026-11-01 used explicit digital peak normalization to 0.3:
gains **1.5925 / 15.5544 / 0.7138**. Windows volume/settings were not changed. It
captured **3749 blocks / 37.49 s**, zero raw/driver losses, yet still had **0 VAD
phrases / 0 reliable alignments**. Mic peak was **0.0006714**, RMS **0.00002444**.
The very weak captured signal is observed; routing/acoustic/echo processing causes
were not isolated. Alignment thresholds were not lowered to manufacture a result.
All three unmatched references remain counted as `reference_unavailable`; there
is no latency distribution. The first version's `evaluation.expected=0` is accompanied
by explicit 6 expected recordings/6 alignment failures; the revised evaluator keeps
all failed alignments in its main expected-case denominator as well.

Both probes completed the stream procedure and exited 0; **this is not latency
acceptance**. All streams/workers closed, without forced termination, and buffered
audio was discarded from RAM. No new permanent recording was made. User-requested
listening review remains skipped. Physical E2E therefore remains unconfirmed.

### Overload, actual Ctrl+C and cleanup

- `reports/stage24_raw_overload.json`: real 48 kHz mic, deliberate 50 ms main-consumer
  stalls, default bounded raw queue. **303 blocks / 145440 frames**, **215 dropped
  blocks / 103200 frames**, **42240 processed**, **49 VAD discontinuities**. Exact
  accounting holds: processed + dropped = captured; VAD known missing = raw dropped.
  Driver errors were zero; stream reopened after Ctrl+C and closed successfully.
- Real Windows-spawn slow-consumer tests cover queue capacities **1 and 2**, a
  consumer blocked for 30 s, immediate incoming-job rejection and bounded shutdown.
  The accepted-but-unfinished jobs are explicitly counted, and temporary WAV/session
  paths are removed. Synthetic overload is not reported as model latency.
- `reports/stage24_ctrlc.json`: actual CTRL_C_EVENT in a private hidden console,
  **504 blocks / 5.04 s**, zero losses, exit **130**, shutdown **1.6386 s**, no controller
  kills, worker exit 0, both stream/worker closed, no pending frames/blocks. Input was
  quiet, no phrases were offered; this run does not test translation quality.

No Stage 3 implementation, model replacement, dependency installation or commit
was included. Original dirty files and the staged chats/README.md deletion remain.

### Final automated checks and WAV regression — 2026-11-01

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest --junitxml=reports/stage24_tests.xml
poetry run ruff check .
poetry check
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/stage24_wav_regression.json
```

**156 tests passed**, Ruff and Poetry checks passed. New coverage verifies that
delivery/hangover and queue time are included, backwards clocks are rejected,
uncertain intervals cannot falsely pass the limit, every missing/filtered/alignment-
failed reference stays in the denominator, transcripts are stripped from reports,
and the real spawned worker observer runs after paired print/flush. Waveform
alignment is checked on delayed/scaled signals and unrelated-noise rejection;
its heuristic thresholds are not calibrated speech/clock confidence.

The original WAV CLI completed **15/15 files / 138.96 s**: **WER 6.67%, CER 2.03%**,
unchanged. Whole-file mean/median/max were **1.8378/1.6962/2.7836 s**, RTF **0.19838**,
sampled RSS **3078.84 MiB**. This is neither physical live latency nor a causal
speed comparison with earlier host conditions. The model revisions and manifest
hash remain unchanged. All actual model probes ran sequentially.

One cleanup-only assertion initially overlapped running worker tests, which were
actively creating temporary sessions. The final check ran after suite exit and
confirmed `.cache/live` was empty. No test-created audio/session remained, and
numeric reports contain no recognized-text or PCM fields. The Git index hash and
all unrelated pre-existing dirty files match the pre-2.4 snapshot.

The audit is complete in the user-approved scope, including the waived listening
review. **Acceptance status remains: physical <=5 s not demonstrated.** No reviewed
gold endpoints or validated physical ADC mapping were substituted, and failed
acoustic probes were not used as successful latency samples. Stage 3 has not begun.

## 2026-11-01 Stage 3.1 capture-only WASAPI loopback

Official PyAudioWPatch 0.2.12.9 wheel for CPython 3.13 Windows x64 installed via
Poetry: one install, zero package updates/removals. No VAD/model integration.
The actual endpoint list contains **10: Realtek Speakers [Loopback], 48 kHz stereo**.

```powershell
poetry run python -m armenian_speech.system_audio --list-devices
poetry run python -m armenian_speech.system_audio --device 10 --duration 2
poetry run python -m scripts.check_live_shutdown --source system_audio --device 10 --seconds 3 --report reports/stage31_ctrlc.json
```

Quiet input: zero callbacks for 2.035 s, valid waiting-for-playback state, exit 0,
stream closed. No silence was synthesized and no recording was written.

Controlled playback of existing 001.wav through output 8 while actual loopback 10
captured for 10 s: **311 blocks / 318464 frames / 6.6347 s of delivered stereo PCM16**,
peak **0.7460**, zero status/overflow/queue-drop events and no pending frames; exit 0.
Numeric report: `reports/stage31_loopback_signal.json`. Source playback had 319680
frames (6.66 s), **1216 frames / 25.33 ms more than delivered**. No bit-perfect or
lossless start/end guarantee is claimed: endpoint idle/start/stop behavior and clock
accuracy need further checks before live segmentation. Observed loopback levels
also need not equal source levels because Windows processing can intervene.

Actual CTRL_C_EVENT in a private hidden console: exit **130**, stopped_by=ctrl_c,
shutdown **0.1030 s**, zero controller kills, stream closed. The endpoint reopened
after the preceding capture. The shared shutdown helper now selects the source;
its default microphone behavior is retained. This Ctrl+C run was idle, not a
continuous-playback stress test.

**162 tests passed** including copy ownership, bounded-queue drop accounting,
status epochs, malformed PCM abort, non-loopback rejection, idle capture, stop and
callback-error closure. Ruff and Poetry checks are recorded with the final checks.
No model benchmark was rerun: existing ASR/MT/WAV implementation is unchanged.
The prior Stage 2.4 physical latency limitation remains open. No commits were made.
Final Ruff/Poetry/whitespace checks passed. The existing physical microphone also
reopened for 0.99 s / 99 blocks / 47520 frames with zero status/queue losses and
closed normally. Git index hash and unrelated pre-existing files match the snapshot;
no pre-existing changes were reverted or removed.

## 2026-11-01 Stage 3.2 live System Audio

The user authorized 3.2. No prior manual check was required after the real 3.1
loopback proof. Add --live with a separate loopback VAD/resampler and the existing
one-time FastConformer INT8 + NLLB greedy worker. Output remains paired HY/EN,
source label System; default microphone label remains Me. No dependency changes.

When an idle renderer stops callbacks, buffered real PCM is finalized after 650 ms
(or two block durations for unusually large blocks), then model/resampler state
resets on resume. No silent PCM is fabricated. Idle detection checks that all raw
frames have been consumed/accounted for; queue/driver losses retain gap semantics.
System display times use an explicit callback-receipt-based timeline_origin_s and
keep wall-time pauses. Raw anchors are preserved and physical clock accuracy remains
unvalidated. This must not be substituted for Stage 2.4 physical speech-end timing.

```powershell
poetry run python -m armenian_speech.system_audio --device 10 --live
poetry run python -m scripts.check_live_shutdown --source system_audio --device 10 --live --seconds 2 --report reports/stage32_ctrlc.json
```

Real loopback smoke: existing public 001.wav trimmed to 5.5 s, played twice through
output 8, with producer deliberately waiting for the first pair before replaying.
**2 offered / 2 accepted / 2 completed**, both terminal lines labelled System, no
empty/filtered output, **2 idle finalizations**, zero raw/phrase/status losses,
**515 blocks / 527360 stereo48k frames**, worker exit 0, stream and worker closed,
no forced termination. The first pair arrived before the second playback; timestamps
were **00:00:01 and 00:00:10**, retaining the intervening pause. Numeric report:
`reports/stage32_live_loopback.json`; no audio or recognized text is saved there.
Maximum VAD-decision->output was **1.5821 s**, maximum queue wait **0.0054 s**.
These are controlled smoke observations, not natural speech-end E2E, sustained
throughput, translation quality, or a bit-perfect capture claim. The intentional
trim can end within a word; the known forced-boundary accuracy limitation remains.

Actual CTRL_C_EVENT with real loaded models and idle loopback exited **130**,
shutdown **0.9227 s**, controller kills=0, worker exit0, both resources closed and
pending frames=0. Report `reports/stage32_ctrlc.json`. Capture-only controller mode
and the previous microphone behavior remain available.

The suite covers idle flush/resume without zeros, no false idle on large blocks,
short candidate rejection, loss at idle, gaps/unique epochs/time offsets, final
PCM submission after capture closes, worker-failure cleanup, diagnostic opt-in and
spawned-worker System labelling. Existing microphone, queue/drop/deadline and paired
output checks remain. Raw monitoring still imports no ASR/MT models.

Original WAV regression:

```powershell
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/stage32_wav_regression.json
```

**15/15 / 138.96 s** completed, **WER 6.67%, CER 2.03%**, unchanged. Whole-file
mean/median/max **1.7516/1.6304/2.7686 s**, RTF **0.18908**, sampled RSS **3075.24 MiB**.
This is not live latency or a causal speedup comparison. Model checks ran sequentially.
No model/decoder/dependency change, permanent new audio/transcript or commit.
Simultaneous microphone + system scheduling remains Stage 3.3; diarization Stage 4.
Final validation: **173 tests passed**, Ruff/Poetry and whitespace checks passed.
Git index hash and unrelated pre-existing files match the pre-3.2 snapshot; no
changes were removed. Temporary ASR sessions were absent after the suite completed.

## 2026-11-01 Stage 3.3 combined microphone + System Audio

The user authorized concurrent inputs and deferred English-term recognition. No
model, decoder, dependency or terminology-normalization change was included.
`combined` selects both actual input IDs, opens them before starting, keeps independent
Silero/resampler/raw queues, and loads one ASR/MT process. Per-job source metadata
preserves Me/System through queueing and paired output; a mutable global label is
not used. Session display times share a callback-estimated origin, not a calibrated
ADC clock. Existing individual microphone/System and WAV commands remain.

```powershell
poetry run python -m armenian_speech.combined --list-devices
poetry run python -m armenian_speech.combined --microphone-device 9 --device 10
poetry run python -m scripts.check_live_shutdown --source combined --device 10 --microphone-device 9 --seconds 3 --report reports/stage33_ctrlc.json
poetry run python -m scripts.check_dual_pipeline
```

### Queue bounds, fairness and failure handling

Default pending capacity is **2 per source** plus at most **2 admitted worker jobs**
(including the active one). Raw queues retain their own 32-block bounds. Pending
queues alternate dispatch when both wait, preserve FIFO within each source, and
drop incoming on that source's full queue. Already admitted work is not preempted;
wall-time fairness/<=5 s cannot be guaranteed for a slow/hung model. Output is not
globally sorted by speech timestamp. One raw block per source per round prevents
one busy raw queue from monopolizing main-thread processing.

Unit/integration checks cover flooding one source while the other keeps reserved
slots and its next turn, gaps/unknown labels, cancellation/accounting, independent
model instances/PCM identity, both streams closed before final ASR submission,
device-open failure, stopped stream, and pending-drain timeout. Shared shutdown
budget covers raw/VAD finalization, pending drain and admitted worker drain; pending
cancellations and admitted unfinished jobs are separate. Existing native spawned
slow-worker tests still cover actual process termination and queue cleanup.

### Real two-file concurrent replay

`reports/stage33_dual_replay.json`: existing checksum-verified 001.wav (Me) and
004.wav (System), with inserted silence, delivered concurrently at nominal sample
rate through independent real Silero instances and one real FastConformer/NLLB worker.
**4 offered/accepted/completed**, **1 Me + 3 System HY/EN pairs**, zero source/global
full/gap/cancelled/unfinished/empty/filtered results, worker exit0, no forced termination.
Max worker queue wait **1.7180 s**, max VAD-decision->output **2.9393 s**. Max staging
wait Me/System **0.00098/0.00008 s** is reported separately; worker queue wait alone
does not include staging. These are file replay observations, not two live speakers
or physical speech-end E2E. Recognized text is not persisted in the report.

### Both actual devices with real inference

`reports/stage33_combined_devices.json`: microphone9 and loopback10 active together
for 30 s; public 001.wav trimmed to5.5s played twice, with producer waiting for the
first System pair before replaying. **5/5 jobs**, **3 Me + 2 System pairs**; physical
mic content was unlabelled and its recognition accuracy was not assessed.

| Capture | Me | System |
| --- | ---: | ---: |
| Blocks | 2998 | 518 |
| Frames captured/processed | 1439040 | 530432 |
| Driver status / raw dropped / pending frames | 0 / 0 / 0 | 0 / 0 / 0 |
| VAD segments | 3 | 2 |
| Pending-queue drops / cancellations | 0 / 0 | 0 / 0 |

Both streams closed, worker exit0, no forced termination or unfinished work. Max
worker queue wait **0.1409 s**, max VAD-decision->output **1.5852 s**; these omit neither
stage timing metadata nor the distinction from actual physical E2E. Mic ADC was
future-dated on all callbacks and nonmonotonic twice, so no clock certification is
claimed. System idle finalized twice without synthetic samples. Actual input frames
do not imply a bit-perfect render-start/end guarantee (see Stage3.1 limitation).
This is a short stability smoke, not extended simultaneous conversation validation.

Actual CTRL_C_EVENT with both devices and real loaded models:
`reports/stage33_ctrlc.json`, **exit130**, shutdown **0.9105 s**, controller kills0,
both streams/worker closed, no pending/raw losses. Mic delivered300blocks/144000frames;
loopback was idle (0callbacks). No phrases were offered in that stop test.

Explicit device IDs remain fixed. There is no automatic switch to a newly selected
Windows default, echo cancellation, acoustic deduplication or diarization. A stopped
device aborts both inputs; a live-but-idle old endpoint still waits normally. Headphones
can prevent a microphone from also hearing system playback. Speaker identity is Stage4.

### Final regression and checks

Full suite: **180 passed in 17.44 s**. Ruff and `poetry check` passed.
Existing offline WAV pipeline: `reports/stage33_wav_regression.json`, **15 samples**,
WER **6.67%**, CER **2.03%** (unchanged), mean processing **1.8783 s**, max **2.9681 s**.
These are whole-file processing times, not physical live latency. No temporary live
session directories remained after the checks. No dependencies or model revisions
were changed for Stage3.3.

## Stage 4.1 — isolated speaker model experiment (2026-11-01)

The user authorized the proposed first experiment. Production `src/` is unchanged;
live commands still use Me/System. See DIARIZATION_COMPARISON.md for the full
protocol, exact commands, primary references and interpretation of numeric reports.

- Poetry installed sherpa-onnx/core **2.0.1** in the dev group: two installs, zero
  updates/removals. Both ONNX artifacts were checked against pinned upstream SHA-256.
- Prepared18 public LibriSpeech utterances from three corpus speaker IDs, with
  separate calibration/evaluation files. Four calibration utterances from two
  speakers fit the threshold; the third voice is unseen. Twelve unique held-out
  utterances produce14 online decisions per length (two return probes repeat clips).
  Oracle clip boundaries and source ownership are not speech DER annotations.
- Fresh-process CAMPPlus/TitaNet each gave **0/14 errors at2s and4s**, but **7/14 at1s**,
  with five clusters instead of three at1s. At400ms all14 deliberately abstained
  before native inference. Silence abstained too. Unknown stays in error counts;
  expected short-input rejection is reported separately from model classification.
- CAMPPlus 2s mean/max compute **27.75/30.22ms**, sampled standalone RSS peak127.84MiB,
  above-baseline86.18MiB. TitaNet23.03/25.88ms, peak168.79MiB, increment127.14MiB.
  Provisional choice CAMPPlus, oneCPUthread, for lower working-set memory. Threshold
  0.47114 and margin0.08 are experimental, not calibrated for Armenian calls.
- With unchanged ASR/MT warmed and resident, CAMPPlus2s mean/max60.73/92.66ms. Armenian
  001.wav produced identical HY/EN before/after speaker probes. No concurrent model
  inference or end-to-end live latency is claimed. Windows sampled RSS did not
  exceed the warmed2844.65MiB baseline; that does not prove zero incremental memory.
- Existing Silero/LiveVAD on A/B/A/B clips with800ms inserted pauses produced four
  single-source segments. With no inserted pause, all three VAD chunks crossed
  source boundaries (the last by116ms). Ownership includes original-file silence.
  Hence assigning just one speaker to each current ASR chunk is insufficient.
- Synthetic overlap and an A-to-B change were accepted by the embedding extractor.
  No overlap detector is implemented; a cosine margin cannot guarantee rejection.
- Tests cover stable returning/new IDs, ambiguous/capacity/short-input abstention
  without centroid mutation, calibration pairs, invalid embeddings, and skipping
  native inference for short/silent audio. **188 passed in17.34s**; final focused
  probe tests **8 passed**. Full Ruff and `poetry check` passed.
- Initial test attempts exposed invocation/environment issues: bare pytest did not
  include the repository namespace directories; default sandbox TEMP failed to
  create pytest directories. `python -m pytest` with explicit fresh workspace
  `--basetemp` resolved both without production/test configuration changes.
- WAV regression: `reports/stage41_wav_regression.json`, **15/15**, unchanged WER
  **6.67%**, CER **2.03%**. Mean/max whole-file processing **2.8474/4.6728s**, sampled
  peak RSS3074.89MiB. This run was slower than Stage3.3's observation despite unchanged
  production code; no speedup, performance equivalence or physical<=5s is claimed.

Reports: `stage41_campplus_1t.json`, `stage41_titanet_1t.json`,
`stage41_campplus_1t_resident.json`, `stage41_boundaries.json`,
`stage41_wav_regression.json`, all under ignored `reports/`. Public fixtures only;
synthetic composite audio stays in RAM. No private microphone recording/transcript,
commits, live speaker feature, Stage4.2/4.3 acceptance or physical clock certification.

## Stage 4.2 — experimental System speaker integration (2026-11-01)

User authorized4.2. Added optional --diarize to combined/System --live; defaults,
microphone and WAV contracts remain. Sherpa2.0.1/core versions unchanged; dependency
moved from dev to runtime. CAMPPlus loads once in the existing spawn worker, only
System jobs enter SpeakerTracker. Missing artifact fails before capture, no fallback.

Tracking uses bounded2s cells, half-window consistency checks, same-label merging,
session-local registry across jobs/idle, maximum8centroids. Short cells cannot create
or train identities; Unknown retains PCM/text for ASR/MT. This is a coarse heuristic,
not word-accurate change detection, measured2s voiced speech, overlap handling or
Armenian diarization validation. A mixed2s cell can remain Unknown or be misclassified.

Tests: exact PCM conservation and contiguous sample bounds, origin/decision timestamp
preservation, A/B/A and returning IDs, Unknown/short/mixed without training, capacity
without ID recycling, split results through real Windows spawn with one model load,
Me isolation and completion once per original job, missing-model startup failure,
and native termination/cleanup of a stalled speaker extractor.
**194 passed in20.27s**, full Ruff, Poetry and whitespace checks passed.

Real models: `poetry run python -m scripts.check_live_diarization`, report
`reports/stage42_pipeline.json`. Public held-out English clips A/B/A in one6s job,
then B returning, a250ms A fragment and synthetic microphone PCM. Labels from result
events: **Speaker1, Speaker2, Speaker1, Speaker2, Unknown, Me**. **4/4 jobs**,6parts,
four printed pairs, Unknown empty ASR and synthetic Me filtered by existing fragment
guard. This does not assess Armenian ASR quality on English speech, or certify that
Me/Unknown produced terminal text. Real speaker work3jobs/5parts, one Unknown,
two discovered speakers, cumulative speaker compute0.5024s. No drops/gaps/unfinished
work; workerexit0, no forced termination, temporary WAV/session cleaned.
Numeric reports omit recognized text. The smoke creates fixture decision times
before sequential submissions; its6.375s max decision-to-output includes pre-submit
holding and is not physical E2E or a pure model benchmark. Several parts require
sequential MT calls, so <=5s is not guaranteed.

An initial helper run failed because its stdout used the Windows legacy encoding;
saved as `stage42_pipeline_failed_encoding.json` (one unfinished job, forced worker
cleanup). The helper now explicitly selects UTF-8, matching existing application
CLIs. Successful rerun above is separate; failure is not counted as a pass.

Actual Windows CTRL_C_EVENT with combined --diarize, device10/mic9,3s:
`reports/stage42_ctrlc.json`: exit130, shutdown1.2924s, cleanupkills0, errornull,
both inputs closed, workerexit0/closed/no forced termination. Me303blocks/145440frames,
all processed, zero raw drops/status events. System was idle0callbacks; no phrases
were offered, so this checks loaded model/capture shutdown rather than speech drain.
ADC future timestamps on all303mic callbacks retain the known clock limitation.

Use README.md commands for user testing. Stage4.3 independent Armenian multi-person
conversation and real boundaries/overlap/queue contention remain pending. No private
audio/transcripts or commits; previous dirty files and staged index retained.

Final WAV regression: `reports/stage42_wav_regression.json`,15/15, WER6.67%, CER2.03%
(unchanged), mean2.9082s/max4.9523s whole-file processing, sampled peak3065.71MiB.
These processing times do not establish live end-of-speech latency. Final hash
comparison found no unexpected changes to preexisting files; staged-index hash was
unchanged and `.cache/live` had no remaining session directories.

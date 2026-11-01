# Armenian speech transcription and translation

Stage 3.1–3.3 support System Audio and concurrent microphone/System capture.
Stage 4.1's isolated speaker-model experiment is in
[DIARIZATION_COMPARISON.md](DIARIZATION_COMPARISON.md). CAMPPlus is the provisional
candidate. Stage 4.2 adds opt-in experimental live speaker labels; commands without
`--diarize` continue to display Me/System.

## Experimental System speaker labels (Stage 4.2)

An additional **trial**, off by default, is available as
`--experimental-speaker-matching` together with `--diarize`. It allows gated new
IDs from >=1.5s utterance cells and may match an existing ID when both halves
individually match it despite disagreeing with each other, without centroid training
on that exception. It has known false-new-ID and overlap risks. It is not accepted
Stage4.3. Exact user-source replay, adverse controls and instructions:
[SPEAKER_MATCHING_TRIAL.md](SPEAKER_MATCHING_TRIAL.md).

Current investigation: [DIARIZATION_DIAGNOSIS.md](DIARIZATION_DIAGNOSIS.md).
First4.2 assignment rules remain; opt-in `--speaker-diagnostics` adds per-cell
numeric reasons/similarities before ASR and a final capture summary, without
enabling periodic levels. Use it together with `--diarize`. It saves no recording
or diagnostic file and is not a diarization quality fix. Latest handover:
[CURRENT_HANDOVER.md](CURRENT_HANDOVER.md). Stage4.3 remains unaccepted.

From the project directory, after speaker model preparation in 4.1:

```powershell
poetry run python -m armenian_speech.combined --microphone-device 9 --device 10 --diarize
poetry run python -m armenian_speech.system_audio --device 10 --live --diarize
```

Select current device IDs with `--list-devices` if needed. Microphone remains `Me`.
System uses session-local `Speaker 1`, `Speaker 2`, etc., or `Unknown`. HY and EN
remain paired. Omit `--diarize` for the existing Me/System behavior. No recording is
saved. If missing, prepare the fixed model separately with
`poetry run python -m scripts.prepare_diarization --models`; inference never downloads.
Sherpa-ONNX 2.0.1 is now a pinned runtime dependency; `poetry install` prepares a
fresh environment. The already installed version has not changed.

CAMPPlus runs once per session in the existing ASR/MT worker, only for System jobs.
It checks nonoverlapping two-second cells before ASR, probes their halves for
inconsistent voice evidence, merges adjacent cells with the same label, and keeps
ambiguous cells Unknown. Boundaries therefore have coarse resolution (up to about
two seconds); short transitions can be missed, and a mixed Unknown cell can still
contain two people. There is no overlap detector, word alignment or separation of
simultaneous voices. Splitting may cut words and reduce ASR/translation context.

New IDs require a full two-second cell and consistent half-window embeddings;
shorter cells can only match existing identities or remain Unknown. Useful short
text is still recognized/translated under Unknown, subject to the existing ASR
fragment guard. Near-silent/short/ambiguous inputs do not train speaker centroids.
This evidence check is heuristic, not a measured duration of voiced speech.

IDs persist across System pauses and reset on process/session restart. Registry
capacity defaults to8 (`--max-speakers`); existing IDs are never recycled. At
capacity, an unmatched voice remains Unknown. Experimental matching settings are
`--speaker-threshold 0.47` and `--speaker-margin 0.08`, based on the tiny English
4.1 experiment, not Armenian-call calibration. A single person can still receive
multiple IDs, or similar voices can be merged. Stage4.3 must test real Armenian calls.

Queue scheduling/accounting remains per source and original VAD job. A split job
retains one credit until its final part completes, with bounded sequential ASR/MT
calls; another source cannot preempt it. Multiple parts add translation work and
can exceed5s to output. Diagnostic `result_parts` and speaker stats distinguish
parts from completed jobs; filtered/empty counters count parts. `--diagnostics`
shows these counters. The existing shutdown deadline also bounds stalled speaker
inference. Headphones remain useful to avoid acoustic duplication between sources.

Stage 1 is complete: local WAV -> FastConformer INT8 -> NLLB -> terminal.
Stage 2.1 capture, 2.2 VAD/segmentation and 2.3 live ASR/translation are implemented.
The Stage 2.4 audit is recorded in TESTS.md; the strict physical <=5 s target is
not certified. Listening verification of provisional endpoints was skipped by request.
Independent speech-end latency validation (2.4) remains pending.
The original Stage 2 kickoff is in
[STAGE2_PROMPT.md](STAGE2_PROMPT.md); current context is in
[STAGE2_HANDOVER.md](STAGE2_HANDOVER.md). Commits require user approval.

## Setup on Windows

Python 3.13.5 and Poetry 2; run from the project directory:

```powershell
poetry install
poetry run python scripts/download_asr.py
poetry run python scripts/download_translation.py
```

Poetry creates `.venv/` here. Downloads prepare pinned local models separately from
inference: `.cache/models/vana/` and `.cache/models/translation/`. The application
requires prepared artifacts; it never switches models on failure. PyTorch uses the
official CPU wheel index. CUDA and NeMo are not needed.

For your own short Armenian WAV (mono, PCM16, 16 kHz):

```powershell
poetry run armenian-speech --wav "C:\Users\gorma\Downloads\my_audio.wav" --offline
```

Replace that path with your file. A `.wav` extension alone does not establish the
required encoding. The WAV CLI has no automatic conversion or segmentation;
microphone VAD is a separate command described below.
Each nonempty recognition produces one segment spanning the entire file and one
translation; these bounds are not detected speech timestamps. Long inputs may exceed
the translator's token limit. Start with clips of 3–15 seconds.

To prepare and run the existing evaluation sample, only if it is not already present:

```powershell
poetry run python scripts/prepare_samples.py
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/wav_pipeline.json
```

Preparation refuses a nonempty output directory. It selects 15 distinct FLEURS test
sentences of 3–15 seconds in archive order, pins dataset revision
`70bb2e84b976b7e960aa89f1c648e09c59f894dd`, converts source float WAVs with PyAV and
records hashes and aligned HY/EN references. Data stay local; FLEURS attribution and
source metadata are retained in the manifest (CC BY 4.0).

## Current stack and CLI

- ASR: [Vana-Labs Armenian FastConformer](https://huggingface.co/Vana-Labs/stt-fastconformer-armenian),
  RNN-T INT8 through onnx-asr / ONNX Runtime CPUExecutionProvider. Revision:
  `ec92cef52199c3874681321b13853e8fe602d23f`.
- Translation: [NLLB-200 distilled 600M](https://huggingface.co/facebook/nllb-200-distilled-600M),
  PyTorch CPU float32, greedy (`num_beams=1`, `do_sample=False`),
  `hye_Armn` -> forced `eng_Latn`. Revision:
  `f8d333a098d19b4fd9a8b18f94170487ad3f821d`.
  Inputs above 512 tokens are rejected; output limit is 256 new tokens, with EOS required.
  The model has a CC-BY-NC 4.0 research license; this choice is not a commercial license.
- Direct runtime dependencies: `numpy`, `sounddevice`, `onnx-asr[cpu,hub]`, `transformers`, `torch`,
  `sentencepiece`, `psutil`, `jiwer`, `av`. PyAV remains necessary for dataset preparation.
  ONNX Runtime and Hugging Face Hub are supplied through the selected dependencies.
  Development: `pytest`, `ruff`, `sacrebleu`. Exact versions are in `poetry.lock`.

| Argument | Meaning |
| --- | --- |
| `--wav PATH` / `--manifest PATH` | Required, mutually exclusive input |
| `--asr-model PATH` | Prepared FastConformer directory; default `cache-dir/vana` |
| `--cache-dir PATH` | Default `.cache/models`; NLLB uses its `translation/` subdirectory |
| `--threads N` | Model CPU threads, default 4; ORT inter-op = 1 |
| `--offline` | Require local files; both models already require prepared artifacts |
| `--report PATH` | Optional numeric JSON report, without recognized text or translations |

Use `poetry run armenian-speech --help` for the actual interface. Experimental model
selection arguments were removed. Download helpers retain `--revision`; inference
expects the pinned revisions above, so custom revisions require an explicit code decision.

## Architecture

`cli.run` validates input and initializes `OnnxArmenianASR` and `ArmenianTranslator`
once before the file loop. `pipeline.process_wav` invokes `transcribe(Path)` then
`translate(text)` and `output.print_segment`, using existing `Transcriber`/`Translator`
protocols. `asr.py` contains the shared `Segment` dataclass; the model adapter is in
`asr_onnx.py`. NLLB resolves a prepared local snapshot and passes its directory to
Transformers, avoiding an unwanted metadata request when loading by repository ID.

WAV inference is sequential. Its only background thread is the sampled RSS monitor.
Microphone diagnostics use PortAudio's callback and a bounded raw-block queue;
the default capture-only mode does not load models. Opt-in `--vad` uses one Silero
ONNX instance in the main consumer, with streaming PyAV resampling and bounded phrase
buffering. Opt-in `--live` adds a bounded phrase queue and one spawned inference
process, loading FastConformer INT8/NLLB greedy once. Terminal HY/EN output stays
in the parent. System audio and speaker identification remain unimplemented.

## Microphone capture — Stage 2.1

From the project directory, enumerate inputs, then select an explicit device index:

```powershell
poetry run python -m armenian_speech.microphone --list-devices
poetry run python -m armenian_speech.microphone --device 1 --duration 60
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000
```

Indices above match this machine's current Intel Microphone Array: 1 is MME,
9 is WASAPI. Indices can change; check the list on each setup. With no `--duration`,
capture continues until Ctrl+C. `peak_1s` measures the latest progress interval;
`peak_max` is the maximum since startup. Speak and pause to check the changing level.
Ctrl+C closes the stream and prints a numeric summary; Python returns 130.
On this Windows setup, Poetry itself returns 1 after the console interrupt even
though the child closes normally. For the child's own exit code, use
`.\.venv\Scripts\python.exe -m armenian_speech.microphone --device 9 --sample-rate 48000`.

The default delivered format is mono `int16` at 16 kHz; `--channels` and
`--sample-rate` select explicit alternatives. Unsupported settings fail without
switching device or rate. MME accepted 16 kHz; WASAPI required explicit 48 kHz here.
Startup prints the opened stream's reported rate, channels, dtype and input latency;
these describe the application stream, not an independent measurement of ADC clocks.
No resampling, audio saving, VAD or ASR/translation runs in this command.

The callback copies each temporary PortAudio buffer into a 32-block queue without
waiting for free queue space. Main-thread diagnostics consume and discard it.
When full, the incoming block is discarded and exact application-drop counters grow;
this raw diagnostics queue is separate from the future inference-segment queue.
Driver overflow/underflow events are counted separately: the driver does not report
an exact lost-frame count (`driver_lost_frames` is null). Pending frames at shutdown
are reported and discarded. Progress counters are snapshots; final counters follow
stream closure. Python callbacks are not a hard real-time guarantee.

Raw ADC/callback times remain in PortAudio's stream clock. MME returned zeros here;
WASAPI returned advancing ADC times approximately 10 ms after callback times.
Zero, nonfinite, nonmonotonic and future-ADC anomalies have separate counters.
These timestamps are not validated speech endings or live latency measurements.
Summary ADC times describe processed blocks and can lag capture counters under load.
Clock mapping/validation remains pending. Explicit 48-to-16 kHz conversion is now
available in the optional Stage 2.2 VAD mode.
Real capture and Ctrl+C evidence, including limitations, is in [TESTS.md](TESTS.md).

## VAD and speech phrases — Stage 2.2

Silero VAD 6.2.3 runs with the existing ONNX Runtime CPU, one thread. Its ONNX model
and MIT license are extracted from a SHA-256-pinned upstream wheel; no wheel code
is executed or installed. On a fresh setup, prepare it explicitly:

```powershell
poetry run python scripts/download_vad.py
```

The model is already prepared on this machine at `.cache/models/silero/`.
Runtime verifies the model checksum and provenance and never downloads implicitly.
`--vad-model PATH` selects another prepared copy of the same pinned artifact.

```powershell
poetry run python -m armenian_speech.microphone --list-devices
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --vad
```

Speak, then pause for roughly a second. `p_speech` is the latest speech probability,
`speech_candidate` indicates an active candidate, and `VAD phrase: {...}` announces
a completed segment with sample-based times and a finish reason. `--vad` remains
diagnostics only; use `--live` below for HY/EN.

PyAV performs stateful anti-aliased resampling to mono PCM16 16 kHz. VAD accepts
mono/stereo input; more channels fail explicitly. Each 512-sample (32 ms) window
is normalized to float32 for Silero. Current defaults in `VADConfig`:

| Setting | Value / behavior |
| --- | --- |
| Start / continuation probabilities | 0.65 / 0.50 (hysteresis) |
| Start confirmation | 160 ms consecutively above the start threshold |
| Pre-roll | Up to 300 ms before the first positive window |
| Minimum speech | 300 ms, also required for new candidates on Ctrl+C/duration/EOF |
| Short-utterance end decision | 600 ms below continuation threshold, quantized to windows (608 ms) |
| Preferred long-fragment boundary | After 3.5 s including pre-roll, use a 256 ms pause |
| Kept trailing silence | Up to 100 ms after the last positive window |
| Maximum segment | 6 s including padding; contiguous continuation, no overlap |
| Ctrl+C / duration | Close capture, drain bounded raw queue, flush resampler and final window |

Final partial windows are zero-padded only for VAD scoring; emitted PCM never gains
fabricated samples. Unconfirmed/short new candidates are discarded even at shutdown;
short tails of an already accepted forced continuation are retained to avoid losing
real samples. A forced maximum can include extra silence when reached
before the normal hangover expires. No full-session recording is accumulated.
For the shorter pause, elapsed audio is measured from the segment start through
its last positive VAD window, including pre-roll and internal pauses. Shorter pauses
before that target keep the original 600 ms rule. `reason=short_pause` identifies
an earlier long-fragment boundary. Pre-roll of the next segment is clamped to the
previous segment's end so quick resumption cannot replay already emitted audio.
Speech without a suitable pause is split at the hard limit, which can cut a word;
sample continuity does not guarantee recognition continuity at that boundary.

Queue drops and driver overflow/underflow epochs end an incomplete segment with
`reason=gap`, reset VAD/resampler state, and prevent joining audio across the loss.
Known missing frames include trailing queue loss at shutdown. Driver loss has unknown
duration and marks subsequent sample timelines uncertain. Raw ADC, callback and
monotonic receipt anchors are retained, including the capture block at the estimated
VAD speech end; a bounded anchor history accompanies the bounded PCM buffer.

`vad_start_s` / `vad_end_s` are window-based VAD estimates in nominal captured-audio
time, not independently labelled speech boundaries. `clock_accuracy=unvalidated`
is explicit: WASAPI timestamp anomalies and clock drift are not silently corrected.
The audio cap does not guarantee NLLB's 512-token limit; live translation explicitly
splits oversized text by words without truncation. No live ≤5 s claim follows from these checks.

Offline VAD screening on the existing WAVs, without ASR/MT:

```powershell
poetry run python scripts/check_vad.py --passes 2 --report reports/stage2_vad_screening.json
```

This adds known silence around each WAV, verifies its checksum, streams arbitrary
block sizes, and saves numeric timings/segment metadata only. It measures neither
microphone latency nor speech-boundary accuracy. Results and device tests are in TESTS.md.

## Live transcription and translation — Stage 2.3

The models are already prepared on this machine. From the project directory:

```powershell
poetry run python -m armenian_speech.microphone --list-devices
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --live
```

Wait for `Inference worker ready` and `Microphone active`, then speak Armenian and
pause. Output uses the existing format: `[00:00:12] Me  HY: ...  EN: ...`.
HY and EN always appear together after both recognition and translation finish.
Long speech is processed in shorter audio fragments rather than waiting for the
whole sentence; line length is not a fixed word count. Six seconds bounds audio
accumulation, not output latency: queue wait, ASR and translation still follow.
`--live` includes VAD; it is mutually exclusive with the diagnostic `--vad` flag.
Models load before opening the microphone. Live inference is always local-only.
Before translation, live output skips isolated letter fragments such as `Հ։`/`Հ.`
and text containing no letters/numbers. Short words and numbers remain eligible;
Armenian single-letter `ա`/`է` and the ligature `և` are preserved. Punctuation and
case are ignored only for this check; accepted text is not rewritten. A skipped
fragment produces neither HY nor EN and never calls the translation tokenizer/model.
ASR still runs: this gate needs the recognized text and does not classify coughs,
breaths or other audio. Longer incorrect words/phrases can still pass.
Standalone spelled letters/initials can be filtered; use `--allow-asr-fragments`
to disable the guard when those are needed. Initials inside a longer name remain.
The diagnostic summary counts `filtered_asr_fragments` separately from `empty_asr`
and queue drops. Filtered jobs count as completed so shutdown accounting is preserved.
The original WAV CLI does not use this live-only guard.
Live output is quiet by default: startup messages, HY/EN and actionable warnings/errors.
Add `--diagnostics` to restore per-second levels/probabilities, inference timings,
model metadata and the numeric shutdown summary. Capture-only/`--vad` remain diagnostic modes.

| Live option | Default / purpose |
| --- | --- |
| `--cache-dir PATH` | `.cache/models`, prepared ASR/translation cache |
| `--asr-model PATH` | Prepared FastConformer directory; default `cache-dir/vana` |
| `--threads N` | 4 model CPU threads; VAD remains one-thread CPU |
| `--queue-size N` | 2 waiting phrases, in addition to current inference |
| `--shutdown-timeout SECONDS` | 15 s to finish accepted work after capture stops |
| `--diagnostics` | Enable detailed live status; off by default |
| `--allow-asr-fragments` | Disable the default isolated-letter/punctuation guard in live mode |
| `--vad-threshold` / `--vad-continue-threshold` | 0.65 / 0.50; higher thresholds are stricter |
| `--vad-confirm-ms` / `--min-speech-ms` | 160 / 300; confirmation must not exceed minimum speech |
| `--segment-target-s` | 3.5 s; prefer a short pause once the fragment reaches this duration |
| `--segment-pause-ms` | 256 ms; VAD-negative pause after the target, at least trailing padding |
| `--segment-max-s` | 6 s including padding; greater than target, at most 12 s in live mode |
| `--min-rms-db DBFS` | Optional minimum signal RMS; disabled until explicitly set |

For longer context with the previous boundary policy, add
`--segment-max-s 12 --segment-pause-ms 600`. Shorter fragments can change ASR and
translation quality at boundaries and generate more inference jobs; measure queue
backlog with `--diagnostics` when tuning. On the 15-WAV VAD+ASR comparison, these
shorter settings increased WER from 6.67% to 11.67% (27 fragments instead of 16).
The nominal-rate run also exposed queue drops/timeouts under current CPU load;
the smaller audio cap is an experimental responsiveness/quality tradeoff, not a
claim of a completed live latency target. Details are retained in TESTS.md.
A nominal-rate file replay can exercise
the real worker without microphone input:

```powershell
poetry run python -m scripts.check_live_pipeline --limit 5 --realtime --report reports/short_segments_realtime.json
```

This uses the live queue/drop policy and paired terminal output. It is a file
replay, not a physical microphone speech-end latency measurement. Numeric summaries
are written even on inference/shutdown errors; an error still produces a nonzero exit.

Speech from a distant TV can still be speech to VAD. Consecutive onset confirmation
rejects isolated probability spikes, and a minimum speech duration prevents very
short fragments from reaching ASR at shutdown. They do not identify the intended
speaker or filter recognized words by a blacklist.

If TV/background speech is quieter than your voice, an optional RMS gate can help:

```powershell
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --live --min-rms-db -45
```

This is a value to tune, not a calibrated recommendation for every microphone.
Use `--diagnostics` to compare `rms_dbfs` while the TV plays and while you speak;
choose a threshold between them. -40 dBFS is stricter than -50; lower values allow
quieter speech. RMS is computed over real 16 kHz samples, not padding or peak level.
The model still receives the original samples; the gate suppresses low-level speech
decisions without modifying PCM. `energy_pass` only describes this gate, not whether
speech is present. A universal level floor is disabled because it rejected quiet
valid recordings in screening. When TV and your voice have similar levels, this
single-microphone VAD pipeline cannot reliably separate the speakers.

VAD never waits for inference. A full phrase queue discards the **incoming phrase**,
prints a warning and increments `dropped_full`; accepted phrases retain order.
Incomplete `gap` phrases are explicitly skipped/count as `skipped_gap`. Raw audio
queue losses remain separate. Progress shows `unfinished_phrases` and `dropped_phrases`;
the diagnostic shutdown summary reports queue depth peak/wait, completed/empty jobs and discards.
This policy bounds memory but cannot guarantee latency under sustained overload.

The worker writes one mono PCM16 16 kHz WAV under a unique `.cache/live/session-*`
directory, closes it, calls the unchanged `transcribe(Path)` adapter, then deletes it
in `finally` before translation. Parent cleanup removes that exact WAV/session even
after forced worker termination. No permanent recording or transcript log is created;
an OS/process crash can leave a temporary cache file. Weights/audio remain outside Git.

`ArmenianTranslator.split_text()` checks actual NLLB token counts including special
tokens and splits oversized text at word boundaries. All source words are retained;
each part uses the existing greedy `translate()`. A single oversized word, missing
EOS, model error or worker crash stops capture with an error, without a model fallback.
The normal WAV CLI still calls `translate()` directly and retains its length checks.

## Stage 2.4 measurement tools

`InferenceWorker(on_result=...)` is an optional measurement observer. The parent
records the endpoint immediately after the paired HY/EN print/flush; suppressed
results have no output endpoint. The normal microphone command remains unchanged.

```powershell
poetry run python -m scripts.check_live_latency --repeat 2 --capture-device 9 --report reports/stage24_replay_5min.json
poetry run python -m scripts.check_live_shutdown --device 9 --seconds 5 --report reports/stage24_ctrlc.json
```

The first command delivers the 15 existing WAVs twice at their nominal sample rate
and concurrently monitors the physical microphone under inference load. Model audio
comes from the files; microphone PCM is discarded after counting. This is an
annotated replay and microphone health test, not an acoustic microphone E2E test.
It does not play sound or save new audio/transcripts. The second command checks a
real Windows CTRL_C_EVENT in a private hidden console and records resource cleanup.

`data/latency_endpoints.json` contains provisional endpoint intervals from visual
waveform review, independent of Silero. `human_verified=false` is deliberate: the
intervals still need listening confirmation. Do not change it without reviewing
the recordings. A local listening page for this run is
`reports/stage24_endpoint_review.html`. The user chose to skip that listening
review for this audit; the labels remain provisional, not phonetic gold.

The replay report includes mean/p50/p95/p99/max, every exceedance/missing endpoint,
annotation uncertainty, raw numeric stage timestamps, queue losses, memory samples,
power state and capture counters. E2E begins at the reference speech end, so it
includes audio delivery/VAD hangover, dispatch, queue, WAV preparation, ASR, MT and
terminal handoff/flush. Empty/filtered/dropped/unfinished output does not become a
fast successful sample. Earlier forced cuts remain separate from natural ends.

PortAudio stream time is calibrated against perf_counter using bracketed reads.
The read bracket bounds that clock query only, not physical ADC accuracy. On this
machine a real WASAPI probe reported ADC timestamps about 10 ms in the future
relative to callback entry. No guessed correction is applied. Physical microphone
latency cannot be certified from those timestamps or from file replay alone; the
report explicitly retains `physical_latency_certified=false`. Stage 2.4 acceptance
requires reviewed speech endpoints and an independently checked physical timeline.

After explicit user authorization for audible playback, the acoustic probe is:

```powershell
poetry run python -m scripts.check_acoustic_latency --input-device 9 --output-device 8 --report reports/stage24_acoustic.json
```

It plays six existing WAVs at the current Windows volume and sends actual microphone
PCM to the normal VAD/ASR/MT path. Waveform correlation locates each reference in
the captured signal independently of VAD; weak/ambiguous alignments are rejected.
Recorded PCM stays in a bounded RAM buffer and is never written to disk. This is a
microphone test, not Stage 3 system-loopback capture. It still retains the ADC and
annotation limitations, so an acoustic run alone does not certify physical <=5 s.
For an explicit level-controlled repeat, `--samples 001.wav 003.wav 006.wav --peak 0.3`
normalizes only the test WAV peaks; it does not change Windows volume. Gain values
and captured signal levels are recorded numerically. Both actual runs failed to
obtain reliable reference alignment; they are retained as unsuccessful measurements.
The repeat opens both streams before starting capture to avoid blocking on output
stream initialization while input blocks are already arriving. Unmatched references
remain in the expected-case denominator. Probe exit 0 means the procedure completed,
not that the latency target passed; inspect the evaluation and certification fields.


The first Ctrl+C requests a stop without interrupting IPC or terminal printing:
close microphone, drain bounded raw input, finalize VAD, offer the remainder, then
finish accepted work. Queue-full rules also apply to that final remainder. The worker
ignores Ctrl+C so its current operation can finish. A separate small control pipe
carries the accepted-job count, avoiding a stop sentinel stuck behind a full queue.
At the deadline, terminate/kill and report unfinished jobs; a second Ctrl+C requests
forced shutdown. Forced/error shutdown returns nonzero; ordinary Ctrl+C returns 130
from Python (Poetry's parent exit-code caveat above still applies).

Per-result timing separates queue wait, ASR and MT. `VAD-decision→output` excludes
speech-to-VAD hangover and is **not** speech-end latency. Hardware clock calibration
and the per-phrase ≤5 s criterion remain Stage 2.4 work.

An offline integration helper feeds known speech through VAD and the real worker:

```powershell
poetry run python -m scripts.check_live_pipeline --limit 3 --report reports/stage2_live_worker_replay.json
```

Use the module form for its `scripts` namespace imports. It deliberately paces job
submission and does not emulate a live microphone or establish a latency guarantee.
For a bounded concurrent-load check, add `--microphone-device 9`: known WAV jobs
are submitted before a real 5 s capture, which can also submit microphone phrases.
This mixed test has different source timelines and is not a speech-end latency test.

## Validation and measurements

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest
poetry run ruff check .
poetry check
poetry run python -m armenian_speech.benchmark --passes 2 --report reports/vana_asr_current.json
poetry run python scripts/check_translation.py --manifest data/local/fleurs/manifest.jsonl --offline --report reports/nllb_current.json
```

Run inference benchmarks sequentially. The ASR runner verifies WAV checksums and
supports `--limit` and `--model-dir`. The translation runner uses correct Armenian
references, not ASR output, and computes corpus chrF++ with SacreBLEU. Both default
to two passes, reuse a single loaded model and retain three research examples in
optional local reports. The regular WAV CLI saves numeric metrics only.
Use `python -m pytest`: the standalone `pytest` entry point does not resolve this
repository's `tests`/`scripts` namespace imports in the current environment.
The explicit temporary directory also avoids a sandbox Windows Temp permission
failure seen with the default pytest temporary root; the cache plugin is disabled
in the verified command. No application workaround is needed.

Verified Stage 1 results before cleanup (15 FLEURS WAVs / correct reference texts):

| Measurement | Recorded result |
| --- | ---: |
| ASR WER / CER | 6.67% / 2.03% |
| ASR-only mean, second pass | 0.139 s |
| NLLB reference-text chrF++ | 57.86 |
| Full WAV mean / maximum | 1.660 / 2.805 s |
| Full WAV RTF / sampled peak RSS | 0.1792 / 3076.56 MiB |

After cleanup, 2026-10-30: **16 tests passed**, Ruff and `poetry check` passed.
All 15 WAVs completed offline: mean **2.102 s**, maximum **3.432 s**, RTF **0.2270**,
RSS **3076.07 MiB**, unchanged WER/CER. The slower timings are a separate observation,
not a replacement for the earlier benchmark or proof of a cleanup-induced slowdown.
The repeated translation-only test recorded battery power, unlike the original AC runs.
Detailed checks and post-cleanup benchmark results are in [TESTS.md](TESTS.md).

File timing includes WAV decoding, ASR, translation and HY/EN printing; model loading,
scoring and report writing are separate. RSS is sampled every 50 ms. WER/CER use NFC,
case folding, Unicode punctuation removal and whitespace collapsing, then corpus scoring.
**These measurements on ready WAVs do not prove live latency ≤5 seconds after speech.**
The 15 read-speech samples are not independent conversational validation; semantic,
name and number errors remain. See [ASR_COMPARISON.md](ASR_COMPARISON.md) and
[TRANSLATION_COMPARISON.md](TRANSLATION_COMPARISON.md) for historical evidence.

## System Audio capture — Stage 3.1

Windows uses pinned PyAudioWPatch 0.2.12.9 for WASAPI loopback. It is a separate
monitoring command by default, with no VAD/ASR/translation or saved recording:

```powershell
poetry run python -m armenian_speech.system_audio --list-devices
poetry run python -m armenian_speech.system_audio --device 10
```

Use the loopback ID from this command's list; it is not a sounddevice microphone
or output-device ID. On the tested machine, 10 is the Realtek speakers loopback,
PCM16 stereo at native 48 kHz. Device IDs may change. `--duration 10` limits a test;
otherwise stop with Ctrl+C. Play audio through the selected output to see levels.
An idle render endpoint can deliver zero callbacks; waiting is normal. The bounded
queue drops incoming blocks on overload with explicit counters; callback errors or
unexpected stream closure are visible errors. Raw clock accuracy remains unvalidated.
No automatic device switching or synthetic silence is introduced.

For live Armenian/English pairs from this source:

```powershell
poetry run python -m armenian_speech.system_audio --device 10 --live
```

Wait for `System Audio live active`, then play Armenian audio through the selected
output. Pairs use the source label `System`; microphone live still uses `Me`.
Models load once before capture. Default live output is quiet; `--diagnostics`
restores levels, timings and JSON summaries. The same local FastConformer INT8,
NLLB greedy, ASR-fragment guard, bounded phrase queue and shutdown deadline apply.
Live accepts mono/stereo endpoints only; it converts native PCM to mono 16 kHz.
Use the microphone's existing VAD/segment flags to tune live segmentation.

When callbacks stop, normally 650 ms without delivered blocks finalizes the real buffered
PCM, without inserting silence. A new burst resets VAD/resampling so separate
playbacks do not join. For large configured blocks, the wait is at least two block
durations so normal callback cadence does not look like an idle gap.
Lost frames/driver epochs remain gaps; gap phrases are skipped.
Session display times for System are callback-receipt estimates and preserve idle
pauses (`timeline_source=callback_receipt_estimate`); raw anchors are kept, physical
clock accuracy is unvalidated. Silence inside delivered PCM still uses normal VAD.
Ctrl+C closes capture, drains/finalizes, and gives accepted inference up to 15 s.
No permanent audio/transcript log is created; the existing short-lived ASR WAV
bridge is reused and cleaned up.

The individual commands still run one source each. To run both through one model worker:

```powershell
poetry run python -m armenian_speech.combined --list-devices
poetry run python -m armenian_speech.combined --microphone-device 9 --device 10
```

Here `--microphone-device` is the sounddevice input ID and `--device` is the
PyAudioWPatch loopback ID. Both must be selected explicitly. Combined mode is always
live; models load once, with separate VAD/resampler states and raw queues per source.
`Me`/`System` labels travel with each inference job. Output order follows dispatch,
not a global chronological sort; each source retains its own FIFO order. Timestamps
share a capture-session origin but remain callback estimates, not calibrated ADC time.

Each source has its own bounded pending phrase queue (`--pending-per-source`, default
2), so one source cannot occupy the other's slots. Dispatch alternates when both
wait. At most `--queue-size` (default 2) jobs are admitted to the shared worker,
including its current job; an already admitted job is not preempted. Overflow drops
incoming phrases for that source with warnings/counters. Raw and phrase losses,
pending wait and worker wait are separate diagnostic counters. Fair dispatch cannot
guarantee <=5 s when the CPU is overloaded.

Ctrl+C closes both streams, drains/finalizes both raw/VAD paths, then drains pending
and admitted work within one shared shutdown deadline (default 15 s). Errors in
either input/worker stop both; timeout cancels pending work and terminates inference
with explicit unfinished counters. `--diagnostics` enables periodic source summaries;
ordinary output stays quiet. If an output device changes, list/select the intended
IDs and restart; the program does not silently switch endpoints. If the microphone
hears the speakers, the same audio can appear under both source labels; headphones
can avoid that acoustic duplication. There is no echo cancellation/deduplication.
Speaker Diarization remains Stage 4.

## Repository and AI history

Weights, audio, references, reports, `.venv`, cache and `.env` files are ignored by Git.
Cleanup removes implementations, not prior results, model caches, test data or Git history.
Keep every actual Codex session in full, unedited, and export each to its own Markdown
file in `chats/` before submission. Summaries and handovers do not replace these exports.

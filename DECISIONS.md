# Decisions

## 2026-11-01 Author selects snapshot and authorizes delivery preparation

After the real-call trial the author chose to keep the current state with its
limitations and requested project completion documentation against the supplied
challenge brief. Freeze runtime/model behavior. The recommended submission command
explicitly enables experimental speaker matching; the first4.2 default is retained.
Prepare README, requirements checklist, demo guide and actual session exports.
Keep previous README byte-for-byte in DEVELOPMENT_HISTORY.md. User selection is
not evidence of correct identities or physical<=5s. GitHub/publication and final
export refresh are deferred; no commit is authorized by this documentation request.

## 2026-11-01 Exact user-source reproduction and opt-in matching trial

User authorized further work and provided two public YouTube excerpts (15s/2s).
Exact sources through Silero reproduce the short-voice registration failure:
second source produces1.648s. A/Bx3 real ASR/MT: baseline1ID/6Unknown parts,
trial2ID/0Unknown;12/12jobs each. Independent mixed/channel controls expose
false-new-ID and overlap regressions, so trial is explicitly opt-in, not default.
Detailed protocol, negative results, dependencies/data provenance and reproduction:
SPEAKER_MATCHING_TRIAL.md. No live call capture/recording or commit; Stage4.3 pending.

## 2026-11-01 Resumed diagnosis after exact first4.2 restoration

- Latest user instructions and CURRENT_HANDOVER.md supersede historical stage
  status. Keep first4.2 matching behavior, including halves/Unknown/short policy.
  Do not restore rejected context accumulation, Unknown merging or filters.
- User confirmed three remote people in the last call and changing level/quality.
  This does not supply per-window identities or prove a cause for its Speaker4/5.
- Add separate opt-in --speaker-diagnostics: pre-ASR per-cell numeric events,
  pre-update similarities, abstention reasons and centroid counts/step; final health
  summary without enabling periodic status. No saved audio or embedding vectors.
- Compare exact SHA-verified first4.2 module, current quiet and observed tracker on
  identical native results. Labels/PCM/centroids/model inputs match in every case.
  Synthetic bandwidth changes reproduce two duplicate IDs for three public voices;
  gain changes expose half-window RMS refusals. These are mechanisms, not call DER.
- Detailed evidence, commands, limits and next hypothesis controls are in
  DIARIZATION_DIAGNOSIS.md. Do not tune thresholds or change identity rules from
  this reused English subset. No live capture, new models/dependencies or commits.
- Follow-up offline control freezes only matched centroid updates, retaining new
  IDs and all gates. Under synthetic band changes it worsened5->6clusters,2->3
  duplicate IDs, and0->2s cross-person assignments. Original-channel replay returned
  to IDs1/2/3 in both policies. Do not transfer freezing to live. Report:
  reports/speaker_decisions_with_frozen_control.json; normal first4.2 comparison
  remains identical across150jobs/169cells, not a call-quality acceptance result.

Chronological record. Earlier defaults and retention decisions describe their date;
the Stage 1 cleanup entry below supersedes experimental runtime options.

## 2026-10-29 First experiment

- The supplied Mathrix brief explicitly expects Codex. The conflicting Claude Cowork
  sentence in the external plan is stale. The project copy of PLAN.md is corrected;
  the original on the desktop is left untouched.
- The user selected the installed Python 3.13.5, subject to dependency validation,
  and public audio with reference transcripts instead of personal recordings.
- Begin with Whisper Base CPU INT8 and Marian HY -> EN, exactly as provisional
  candidates in the plan. This tests two separate stages, so translation does not
  bypass the Armenian transcript. Use four CPU threads and greedy decoding initially.
- Restrict implementation to stage 1. Avoid empty audio/VAD/speaker modules and live
  queues before the experiment justifies their implementation.
- Keep source, project environment, model cache and evaluation samples inside this
  project. Ignore weights, audio, local evaluation references and numeric reports.
- Use a small FLEURS Armenian test subset for an initial reproducible screening.
  It is read speech and cannot establish conversational quality. A small screening
  sample is also insufficient for a statistically strong model comparison.
- Report model loading separately from inference, and label the memory maximum as
  sampled RSS. Do not call WAV processing time live phrase-end latency.
- Save no recognized transcripts or translations to files. Optional benchmark
  reports contain measurements only. Reference annotations from the dataset are
  evaluation inputs and stay local, outside Git.
- Do not reconstruct AI exports or claim a completed quality evaluation from unit
  tests. Full actual session exports and human English quality review are separate
  requirements before submission.
- A real inference run exposed faster-whisper 1.2.1 calling PyAV's removed
  `metadata_errors` argument. Pin `av<19`, the compatibility boundary documented in
  [upstream issue 1589](https://github.com/SYSTRAN/faster-whisper/issues/1589), rather
  than editing installed libraries or hiding the decoder failure.
- The first full 15-clip offline run rejects Base + Marian on this sample: WER
  137.92%, CER 98.65%, mean WAV processing 11.72 s, sampled RSS 1012 MiB. ASR is
  the primary runtime bottleneck. Direct translation of correct normalized Armenian
  references is fast (mean 0.231 s), but introduces substantial semantic errors.
  Keep defaults for reproducibility and continue stage 1 with an explicit comparison;
  do not move the rejected configuration into the live stage. Details are in TESTS.md.

## 2026-10-29 ASR comparison and baseline audit

- Correct the earlier greedy description: Whisper's default temperature schedule can
  retry decoding with stochastic sampling despite beam_size=1. Make that schedule
  explicit without changing the old default. Separately test temperature=0.
- Add a single Vana-Labs ONNX RNN-T adapter matching the existing transcribe protocol;
  keep the pipeline and Marian implementation unchanged. Keep comparison in a small
  ASR-only runner, separate processes, two passes, same 15 WAVs with checked hashes.
- Install onnx-asr 0.12.0 only; no NeMo and no FP32 substitution. Pin the model revision
  and record artifact hashes. Use CPUExecutionProvider and four CPU threads.
- ASR-only measurements replace invalid memory/RTF comparisons against the combined
  old Base + Marian process. Numeric reports additionally retain three examples as
  explicitly requested for this research comparison; no general transcript logging.
- Recommend Vana for further Stage 1 evaluation: WER 6.67%, CER 2.03%, second-pass
  mean ASR 0.139 s, max 0.207 s, sampled RSS 453 MiB. Greedy Whisper is faster than
  the old temperature configuration but still inaccurate. Full findings, examples
  and limitations are in ASR_COMPARISON.md. No claim about live latency is made.

## 2026-10-29 Default WAV pipeline uses accepted FastConformer

- The user accepted Vana-Labs FastConformer INT8 as the primary MVP ASR. Make it the
  CLI default, initialized once before all files. Use the existing ONNX adapter and
  transcribe contract; do not modify pipeline.py or Marian translation logic.
- Default ONNX artifacts are local at cache-dir/vana, prepared by download_asr.py.
  Missing artifacts stop with an actionable error, without implicit download or
  fallback. --asr-model selects a prepared ONNX directory.
- Retain Whisper only as explicit --asr-backend whisper for reproducibility. Identify
  the ONNX repo/revision and RNN-T decoder in reports; separate ASR/Marian beam sizes.
- Offline full chain passed all 15 WAVs: mean 0.452 s, max 0.747 s after loading,
  WER 6.67%, CER 2.03%. Loading is reported separately. Translation quality remains
  inadequate on some samples and is not addressed by this integration.

## 2026-10-29 Translation model selection

- Compare translators on the same 15 correct normalized Armenian references, not ASR
  outputs. Add SacreBLEU only to dev dependencies for supporting corpus chrF++; also
  compare meaning with aligned English. Two passes, fresh process per model, CPU
  float32, four threads, greedy. Model loading and downloads are outside MT timing.
- Select NLLB distilled 600M: chrF++ 57.86, versus M2M100 39.61 and Marian 32.88.
  Final second-pass mean/max MT: 1.335/2.007 s for NLLB, 1.085/1.738 s for M2M100,
  0.186/0.359 s for Marian. Quality takes priority over the reserve's modest speed gain.
- A separate NLLB beam=2 test reduced chrF++ to 56.83 and was slower, with unstable
  timings during changing power conditions. Keep greedy; do not add runtime fallback.
- Load NLLB/M2M100 tokenizers and weights from pinned prepared local snapshots.
  This avoids a Transformers 4.57.6 model_info call despite local_files_only=True.
  Sequential snapshot preparation avoids a Windows symlink support detection race.
- Default translation ID is NLLB, with explicit hye_Armn input and eng_Latn BOS.
  Retain translate(text) and the existing pipeline. Each model loads once. ASR is unchanged.
- Full selected chain: mean 1.660 s, max 2.805 s per WAV after loading, sampled RSS
  3076.56 MiB. Early runs were on battery; final reference runs and full chain had
  connected power. Actual numbers, adverse examples and caveats are in TRANSLATION_COMPARISON.md.
- NLLB still makes material errors. The current small FLEURS/FLORES-derived sample
  does not prove conversational quality. Record its research/noncommercial license
  and keep the project distinct from any future commercial deployment decision.

## 2026-10-30 Stage 1 completion and legacy cleanup

- Stage 1 is complete with the previously selected FastConformer INT8 and NLLB
  greedy stack. Reasons for rejecting Whisper, selecting FastConformer and replacing
  Marian are recorded in the comparison/selection entries above and their reports;
  cleanup does not revise those measurements or claim that quality is solved.
- Keep CPU-only inference for the target i5-13420H / 16 GB Windows machine without
  CUDA. The chosen stack already runs locally on this hardware; adding GPU frameworks
  or NeMo is not justified by this cleanup.
- Retain separate ASR and translation contracts: translation can be evaluated on
  correct Armenian independently of ASR errors, and the existing components can be
  reused by a future live worker. Load each model once to avoid repeated startup cost.
- Remove rejected implementations before Stage 2 so live integration has a single
  tested model path. Delete ArmenianASR/Whisper, Marian and M2M100 branches, their
  model-selection arguments and experimental beam override. Preserve Segment,
  process_wav, protocols, ONNX adapter, scoring, datasets and benchmark infrastructure.
  ArmenianTranslator construction now takes (cache, threads, offline); translate(text)
  is unchanged. --asr-model remains a local FastConformer directory override.
- Remove faster-whisper and sacremoses; Poetry also removes their now-unused
  ctranslate2, joblib and cloudpickle. Keep PyAV: prepare_samples.pcm_wav uses it.
  Drop the Whisper-specific av<19 constraint, but retain locked PyAV 18.1.0 and all
  other remaining versions. No new dependencies or models are installed.
- Preserve historical reports and Git history; obsolete reproduction commands are
  labelled and tied to commit 0aabc46. Do not delete old local caches or audio.
  WAV regression and both benchmark runners passed after removal; actual results
  are in TESTS.md. Faster historical timings are not silently replaced by slower
  cleanup validation timings. Neither is a live latency measurement.
- Prepare Stage 2 documents only. No live functionality is implemented here.
  The user must review these changes before any commit; Stage 2 implementation
  separately requires approval of a plan in the next session.

## 2026-10-30 Stage 2.1 microphone capture

- After the initial read-only review, the user authorized starting Stage 2.
  Keep this implementation limited to 2.1, as previously requested: no VAD or
  model integration, System Audio, diarization or commits.
- Select sounddevice 0.5.6 / bundled PortAudio for Windows capture. PyPI provides
  a Python 3 Windows x64 wheel; CFFI provides a CPython 3.13 Windows x64 wheel.
  Actual imports and device opening passed in Python 3.13.5. Poetry added only
  sounddevice 0.5.6, cffi 2.1.1 and pycparser 3.12; no existing versions changed.
- Add a separate `python -m armenian_speech.microphone` entry point so the existing
  WAV CLI and model adapters stay untouched. Require explicit device selection.
  Default to mono int16 / 16 kHz, report opened stream settings and fail clearly
  on unsupported settings. Alternative rates/channels must be explicit; no fallback.
- RawInputStream uses host-selected variable blocks (`blocksize=0`). The callback
  copies the borrowed buffer and uses a bounded 32-block queue without waiting for
  free space. Full means drop the incoming raw block and count exact frames/blocks.
  Only the main thread computes peak levels and prints. This queue is diagnostic
  capture infrastructure, not the Stage 2.3 completed-segment/inference queue.
- Retain sample indices and raw PortAudio ADC/callback times without pretending
  they share perf_counter's origin. MME timestamps were zero; WASAPI ADC timestamps
  were about 10 ms after callback times. Count these anomalies. Clock calibration
  and independent speech-end validation remain work for later substages.
- On Ctrl+C or failure, close the stream; expose callback failures to the main
  thread. Report and discard raw frames still pending at shutdown. Real Windows
  CTRL_C_EVENT tests confirmed closure and reopening; Poetry's parent exit code
  differs from the Python child's, as recorded in TESTS.md.
- Capture diagnostics do not persist audio. Existing Stage 1 changes and staged
  deletion of chats/README.md remain in place; no commit is created.
- References: https://pypi.org/project/sounddevice/0.5.6/,
  https://pypi.org/project/cffi/2.1.1/,
  https://python-sounddevice.readthedocs.io/en/0.5.6/installation.html,
  https://python-sounddevice.readthedocs.io/en/0.5.6/api/raw-streams.html,
  https://python-sounddevice.readthedocs.io/en/0.5.6/api/streams.html.

## 2026-10-31 Stage 2.2 VAD and segmentation

- The user explicitly authorized moving to 2.2. Keep ASR/MT integration and the
  completed-segment worker queue for 2.3; preserve the existing WAV interfaces.
- Use Silero VAD 6.2.3 ONNX with existing ORT 1.31.1 CPUExecutionProvider and one
  intra/inter-op thread. Extract only the model and MIT license from the exact
  SHA-256-pinned PyPI wheel. No Silero/TorchAudio/TorchCodec package installation,
  implicit download, GPU provider or fallback. Keep all weights under ignored .cache.
- The NumPy-only adapter implements the published 512-sample / 64-sample context
  and recurrent-state ONNX tensor contract. It loads once and resets on discontinuity.
  Model and wheel hashes are pinned in vad.py; download_vad.py verifies both.
- Use existing PyAV 18.1.0 for stateful anti-aliased resampling and mono/stereo
  downmix to mono PCM16 16 kHz. Preserve PTS, flush filter delay, and reject unsupported
  layouts. Declare already-installed NumPy as a direct dependency; lock refresh changes
  no package versions and no packages are installed or removed in this substage.
- Keep VAD in the main raw-block consumer; PortAudio's callback only copies/counts
  blocks and now also records monotonic receipt and capture discontinuity epochs.
  Without --vad, the original diagnostic mode still runs without model loading.
- Initial segmentation defaults: start/continue 0.5/0.35, pre-roll 300 ms, minimum
  speech 250 ms, silence 600 ms (608 ms in 32 ms windows), trailing 100 ms, maximum
  total segment 12 s. Treat these as measured starting settings, not a quality optimum.
  Forced continuations have no overlap. A maximum reached during hangover can keep
  extra silence. Shutdown/gap candidates are preserved even when shorter than the
  normal minimum and are explicitly labelled incomplete by their finish reason.
- On Ctrl+C/duration, close capture first, drain its bounded queue, flush resampler,
  score a zero-padded final VAD window while retaining only real PCM samples, then
  emit the active remainder. Fatal errors close the stream and discard buffered audio.
  Known queue gaps, including trailing drops, and unknown driver gaps are explicit;
  reset all state rather than joining speech across missing input.
- Retain sample positions, epoch origin and observed ADC/callback/monotonic anchors
  at VAD speech end. Keep anchor history bounded. No fabricated clock correction:
  clock_accuracy remains unvalidated; unknown driver-gap duration marks later timelines.
  Actual speech ends, drift and clock mapping still require independent Stage 2.4 checks.
- Improve diagnostics after the user's trial: peak_1s now changes with each interval;
  peak_max retains the session maximum. VAD phrases contain numeric metadata, no text.
- A 12 s audio cap cannot guarantee <=512 NLLB input tokens. Stage 2.3 must explicitly
  handle oversized ASR text before translate(), without silent truncation or fallback.
- Primary references: [Silero 6.2.3](https://pypi.org/project/silero-vad/6.2.3/),
  [upstream ONNX contract](https://github.com/snakers4/silero-vad/blob/master/src/silero_vad/utils_vad.py),
  [PyAV audio conversion](https://pyav.org/docs/stable/api/audio.html).

## 2026-10-31 Stage 2.3 live producer/consumer integration

- The user accepted 2.2 in a manual trial and explicitly authorized 2.3. Add an
  opt-in --live mode; retain capture-only, --vad diagnostics and existing WAV CLI.
  No dependency/model selection changes, System Audio, diarization or commits.
- Use one Windows spawn process for FastConformer INT8 and NLLB greedy, loaded once
  before opening the microphone. This separates CPU/GIL work and allows terminating
  a hung native inference operation. Silero stays in the parent raw-block consumer.
- Choose a default capacity of 2 waiting phrases. Full means discard the incoming
  phrase with stderr warning and a counter; accepted work retains order. This favors
  ordering over freshness and does not promise <=5 s under overload. Raw queue drops
  remain separate; incomplete gap phrases are explicitly skipped rather than inferred.
- Return results over a bounded OS pipe; only the parent prints HY/EN using the
  existing output.print_segment(..., "Me", ...). Keep transcripts transient and
  summaries/replay reports numeric. Record queue/ASR/MT and decision-to-output times,
  labelling the latter as distinct from actual speech-end latency.
- Keep ASR's transcribe(Path) contract. Write a closed temporary mono PCM16 16 kHz
  WAV for one phrase, delete it in finally, and clean its exact session path in the
  parent after worker exit/termination. No recursive deletion or saved recording.
- Add explicit live-only ArmenianTranslator.split_text: count real tokenizer input
  IDs including special tokens, split by words, call unchanged translate() per part.
  No source-word omission, sampling or fallback. A single oversized word or missing
  output EOS is a fatal visible error. WAV callers retain the previous length behavior.
- First Ctrl+C sets a parent stop flag rather than interrupting result IPC/printing;
  close the stream, flush VAD, offer final data and drain accepted work for up to 15 s.
  A small independent control pipe sends the final accepted-job count, so stop does
  not depend on space in a full work queue or Queue.empty() while its feeder runs.
  Deadline/second Ctrl+C terminates the worker and counts unfinished accepted jobs.
  Cancel feeder joining on an abandoned queue; never reuse a terminated queue.
- Worker startup/inference/crash errors propagate to the parent and stop capture.
  Windows PipeConnection.poll may raise BrokenPipeError on EOF; handle that as
  channel closure while retaining received error messages and process exit checks.
  Real spawn tests exposed this case and confirmed the correction.
- Primary runtime references: [multiprocessing](https://docs.python.org/3.13/library/multiprocessing.html),
  [perf_counter](https://docs.python.org/3.13/library/time.html#time.perf_counter).

## 2026-10-31 False-trigger mitigation and quiet live output

- The user reported unsolicited phrases during silence and excessive per-second
  logs, then confirmed a distant TV and other noise. Treat these as two separate
  concerns: reject weak/spurious speech candidates and make routine live output quiet.
- Remove the minimum-duration bypass for new candidates on shutdown/duration/EOF/gap.
  The earlier behavior could send just a few samples to ASR and produce arbitrary
  text. Preserve short tails only when continuing an already accepted maximum split.
- Raise default start/continue thresholds to 0.65/0.50, require 160 ms of consecutive
  start-positive samples, and set minimum speech to 300 ms. Keep pending onset plus
  pre-roll so confirmation does not discard its beginning. Expose all four via CLI.
- Add an optional RMS floor (--min-rms-db) and diagnostic rms_dbfs/energy_pass.
  Score original samples in Silero, but suppress low-energy decisions before the
  segmenter. Use only real samples for RMS, excluding final-window zero padding.
  No recognized-word blacklist, extra model or automatic speaker identification.
- Reject an unconditional -50 dBFS default: actual FLEURS screening lost all detections
  in 5/15 valid recordings. Keep the floor opt-in and tune it to the microphone/room.
  Pure threshold/onset changes retained detections in 15/15. Background TV speech at
  comparable volume remains fundamentally ambiguous to this speech detector.
- Default --live now prints startup, HY/EN and actionable warnings/errors; hide
  periodic status, per-job timings and JSON summary unless --diagnostics is requested.
  Capture-only/--vad and research helpers retain explicit diagnostic behavior.
- Do not promise removal of every false phrase without labelled audio from the
  user's environment. Existing WAV ASR/MT interfaces and model settings remain intact.

## 2026-10-31 Shorter live fragments with paired HY/EN output

- The user approved more frequent output for long speech and explicitly required
  Armenian and English to remain together. Keep the single completed result event
  and existing terminal formatter; no partial ASR/translation output or new models.
- Set a 3.5 s target, 256 ms VAD-negative pause after that target, and 6 s hard audio
  limit including padding. Preserve 600 ms silence for shorter utterances. Target
  duration spans segment start through last positive VAD window, so it includes
  pre-roll/internal pauses; trailing silence alone cannot advance a short utterance
  into the long-fragment rule. Mark these earlier completions as short_pause.
- Prefer actual short pauses but retain contiguous forced splits for uninterrupted
  speech. No audio overlap/deduplication or repeated growing-window ASR is introduced.
  The existing last_emitted_end clamp prevents pre-roll from duplicating PCM when
  speech resumes sooner than the original 600 ms hangover.
- Expose --segment-target-s, --segment-pause-ms and --segment-max-s. Reject
  contradictory settings before loading models; live cannot exceed the existing
  worker's 12 s PCM contract. Keep the previous policy selectable for comparison.
- Fewer seconds of accumulated audio are not a latency guarantee. More calls can
  overload the CPU worker, and forced cuts can break words/reduce translation
  context. Measure ASR boundary effects and the real queue; do not claim identical
  quality from sample-continuity tests. Keep numerical reports without transcripts.
- Add nominal-rate --realtime replay to the existing integration helper. It polls
  results while delivering audio and never waits for phrase-queue capacity; retain
  the original explicitly paced offline helper mode. Neither is independently
  labelled physical microphone latency testing (Stage 2.4).
- Measured tradeoff: on all 15 WAVs, previous VAD+ASR WER/CER were 6.67%/2.25%;
  the shorter settings produced 11.67%/3.72%, with 27 fragments versus 16. Keep
  this regression explicit; do not tune arbitrary cut offsets to these test files
  or claim equivalent recognition quality. The user requested shorter fragments;
  longer context remains selectable with the documented flags.
- Nominal-rate replay on battery exposed actual worker overload, dropped phrases
  and the existing 15 s drain deadline. Retain this failure and keep Stage 2.4 open.
  Make the integration helper persist numeric worker summaries even on errors,
  while re-raising the error and retaining a nonzero exit; do not relax the app's
  queue/drop/shutdown policy to make a benchmark pass.

## 2026-10-31 Reject isolated ASR fragments before live translation

- The user supplied repeated HY `Հ։`/`Հ.` with invented English sentences and
  asked to suppress tiny detections, possibly coughs/breaths/noise. The transcript
  proves a one-letter ASR result followed by an unsupported translation, but does
  not identify the actual acoustic cause. Tiny forced-cut tails and background
  speech remain possible as well; no recorded/labelled room audio is available.
- Add a conservative structural check after ASR and before any translation call,
  only in live_pipeline. Suppress results with no letters/numbers or a single
  alphabetic character after NFC/casefold and ignoring nonletters. Preserve numeric
  results, words with at least two letters, Armenian single-letter ա/է, and և
  (expanded by Unicode casefold). Preserve initials embedded in a longer name.
- This is the user's newly requested fragment-rejection behavior, not an English
  phrase blacklist or an invented confidence score. Do not raise the global minimum
  speech duration: it can reject valid quick replies and still admit long coughs.
  ASR must still run to inspect its text; only unnecessary translation/output is saved.
- Keep filtered Armenian/English empty in the result event and attach a reason
  (single_letter/no_alphanumeric). Count filtered_asr_fragments separately from
  empty_asr and queue drops. The job still completes and participates normally in
  accepted/completed shutdown accounting. Print only a numeric/reason notice under
  --diagnostics; ordinary live output remains quiet, with paired HY/EN for kept jobs.
- Enable by default and expose --allow-asr-fragments for spelling/standalone-letter
  input. Genuine standalone initials can be lost under this rule. Longer incorrect
  words/phrases are not detected, and valid single-letter words remain eligible
  for translation without a correctness guarantee. Keep VAD/segment settings,
  model revisions/greedy decoding, dependencies and the original WAV pipeline intact.

## 2026-10-31 Stage 2.4 timing and stability audit

- The user authorized Stage 2.4 and requested a Stage 3 explanation afterwards.
  Keep Stage 3 implementation, model/dependency changes and commits out of scope.
- Add an optional parent on_result observer after paired output/flush. Keep all
  existing worker/model/capture contracts. Numeric observers strip transcripts;
  suppressed results have completion timestamps but no output timestamps.
- Compute E2E from an independent reference-end interval, not the VAD decision.
  Include delivery/hangover, dispatch, queue, WAV preparation, ASR, translation
  preparation/MT and result handoff/print. Reject backwards/non-finite timelines;
  never clamp negative times. Report interval bounds, all exceedances and missing,
  filtered, empty, rejected or unfinished endpoints as explicit outcomes.
- Use checksum-bound visual waveform endpoint intervals independently of Silero,
  labelled provisional with human_verified=false. Listening verification has been
  requested; do not promote these to gold annotations because the run looks fast.
- Exercise the actual worker at nominal audio rate while a real WASAPI microphone
  captures concurrently. Model input is still the known files, and mic PCM is
  discarded; label this replay + capture health, not physical microphone latency.
- A separate real input clock probe found all 999 ADC timestamps ~10 ms ahead of
  callback entry, despite clock-offset span only 0.0396 ms. Read-bracket precision
  is not physical ADC accuracy. Keep the inconsistency visible and do not apply
  an undocumented constant correction to obtain a passing latency number.
- Add a reproducible Windows private hidden-console CTRL_C_EVENT controller with
  numeric output/resource checks and identity-aware cleanup of only its own child
  processes. Retain failures and do not replace actual process checks with mocks.
- Audio playback through speakers and endpoint listening confirmation were asked
  separately. Pending replies are not consent or annotations; continue only the
  independent silent tests until answered. Stage 2.4 acceptance remains explicit,
  and physical_latency_certified is false for replay even with reviewed labels.
- The user subsequently authorized speaker playback at unchanged Windows volume
  and explicitly waived listening review of the endpoint annotations. Respect this
  scope change: leave human_verified=false and stop asking for that review. Add an
  acoustic speaker->mic->existing-models probe using normalized waveform correlation
  to transfer the provisional endpoint intervals independently of VAD. Correlation
  gates are heuristic alignment checks, not calibrated confidence or a physical
  clock certificate. Captured audio is bounded to the fixture duration in RAM only.
- Primary clock semantics: [sounddevice 0.5.6](https://python-sounddevice.readthedocs.io/en/0.5.6/api/streams.html)
  and [PortAudio time info](https://portaudio.com/docs/v19-doxydocs/structPaStreamCallbackTimeInfo.html).
- On resumption 2026-11-01, retain the failed six-file acoustic observation. The
  first helper started input before opening output, which could block draining
  during output initialization. Open both first, then start; record explicit test
  gains and captured peak/RMS. A three-file repeat normalized peaks to 0.3 without
  changing Windows volume. It still had no VAD/alignment, so do not lower the
  alignment threshold or claim physical E2E. No OS noise/echo settings were changed.
- Keep failed alignment in the evaluator's expected-case denominator. Execution
  completion/exit zero is distinct from latency acceptance. This audit is finished
  under the user's waived listening review, with the physical <=5 s target explicitly
  unconfirmed. Stage 3 is a plan only: loopback capture first, then two source states
  feeding the existing bounded worker, source labels and contention/regression tests.

## 2026-11-01 Stage 3.1 system audio capture

- The user authorized beginning Stage 3. Execute the previously described first
  substep only: native loopback capture, device selection, bounded buffering and
  Ctrl+C, without VAD/models or diarization. Existing microphone/WAV code stays intact.
- Select PyAudioWPatch 0.2.12.9: official PyPI supplies cp313-cp313-win_amd64 wheel,
  SHA-256 aaa847f5f76e11b42242b51293d872f811ab8925146c34ca79f21c9b18bda551.
  Poetry installed one package, no updates/removals; Windows-only marker and lock
  hashes are retained. The existing sounddevice interface exposes no loopback flag.
- Discover actual loopback endpoints and require their explicit ID. Reject regular
  microphone/render IDs; do not silently switch to a default output. Capture native
  rate/channel count as PCM16, preserve frame positions/epochs in AudioBlock, and
  keep callback work bounded to validation, copy, counters and nonblocking enqueue.
- Idle WASAPI output may supply no callbacks; preserve this state without fabricated
  audio or a microphone-style no-data timeout. Flag unknown driver losses/timestamp
  accuracy explicitly. Models and translation are deferred to 3.2.
- References: [upstream](https://github.com/s0d3s/PyAudioWPatch),
  [official distribution](https://pypi.org/project/PyAudioWPatch/0.2.12.9/).

## 2026-11-01 Stage 3.2 live System Audio

- The user authorized 3.2; prior real loopback and cleanup tests suffice, no mandatory
  user manual check blocks integration. Add --live to System Audio without changing
  capture-only defaults, microphone/WAV behavior or model/dependency choices.
- Reuse native PCM callback/queue, independent LiveVAD with PyAV mono16k conversion,
  pinned one-time ASR/MT worker load and paired formatter. Add a parent speaker label
  defaulting to Me; System uses System. This is one source per worker, not concurrent
  two-source scheduling (3.3) or speaker identity (4).
- A renderer can stop callbacks instead of delivering silence. After 650 ms idle
  and no queued raw frames, finalize real PCM, flush resampling and reset on resume.
  No zeros are added to emitted audio. Normal VAD handles silence in delivered PCM.
  Preserve minimum speech, loss accounting and explicit gap skips.
- Give System segments an explicit timeline_origin_s estimated from callback receipt
  minus block duration; retain raw capture anchors. This keeps session idle pauses
  in display times without fabricating frames or claiming validated ADC accuracy.
- Keep quiet live output, diagnostic opt-in, ASR fragment guard and bounded queues.
  Close the input before final raw/VAD drain and inference drain; failures abort
  inference, first Ctrl+C requests graceful stop and second can force interruption.
- Controlled real playback of 5.5 s trimmed public 001.wav twice produced 2/2 System
  pairs, idle flushes=2 and timestamps 1 s/10 s. Producer deliberately waited for
  the first output before the second playback: not a throughput or E2E guarantee.

## 2026-11-01 Stage 3.3 concurrent inputs and fair scheduling

- The user authorized 3.3 and deferred Armenian/English term recognition. Keep the
  current models/decoder settings/dependencies and single-source commands unchanged.
  New combined CLI explicitly selects a sounddevice mic ID and a PyAudioWPatch
  loopback ID, using one ASR/MT process loaded once and two independent Silero states.
- Carry source on each immutable InferenceJob and return it with the result. Never
  switch a global speaker label while older jobs are pending. Keep default Me for
  existing callers. Record per-source offered/accepted/completed/filtered/loss counts.
- Bound each source's pending phrases separately (default 2). Alternate dispatch
  when both are ready and admit only worker.capacity outstanding jobs, including
  the current one. No preemption; a late source can wait for already admitted work.
  Drop incoming on per-source full, skip gap phrases explicitly, and count cancelled
  pending jobs separately from admitted unfinished jobs. Report staging wait as well
  as worker queue wait; the latter alone omits staging delay.
- Drain at most one raw block per source per round so active loopback cannot monopolize
  the consumer. Keep loopback idle finalization, mic no-block watchdog and common
  callback-estimated session time. Input errors stop both; no silent device fallback.
- Close both capture handles before final raw/VAD drain. Use one shutdown deadline
  across finalization, fair pending drain and admitted worker drain. Timeout/failure
  cancels pending and aborts the worker with visible counters. No full-session recording.
- Real-device playback and concurrent-file replay are separate observations. The
  physical microphone content was unlabelled; do not claim two independently labelled
  simultaneous speakers or physical speech-end latency. Acoustic duplication remains
  possible when a mic hears the speakers; no echo cancellation is added.

## 2026-11-01 Stage 4.1 isolated speaker experiment

- User authorized the proposed 4.1 experiment. Keep production modules unchanged;
  scripts compare CAMPPlus zh/en advanced ONNX and TitaNet Small using the same
  Sherpa-ONNX 2.0.1 CPU API. Pin two new dev packages, no existing upgrades/removals.
  Pin model SHA-256 from the upstream release checksum list; data/models ignored.
- Use 18 public LibriSpeech utterances from three corpus speaker IDs, separate
  calibration/evaluation files, fixed crops, and no forced speaker count. Include
  an unseen third speaker and returning voices. Explicitly count repeated probes,
  Unknown and extra clusters; do not describe clip-label errors as DER.
- Provisionally choose CAMPPlus for lower standalone memory and comparable held-out
  results at 2/4 s. Both models fail on many 1 s clips. Thresholds are experimental,
  not an Armenian-call calibration. Do not tune them using held-out mistakes.
- Existing VAD merges adjacent speakers without pauses; one label on each current
  chunk is insufficient. Stage4.2 must address within-chunk voice changes before ASR.
  Overlap is not detected by the embedding model or guaranteed by cosine margins.
- Preserve useful short ASR text with Unknown when identity is unreliable. Proposed
  >=2 s evidence for creating a new ID must be evaluated during integration, not
  advertised as a live feature now. Maintain one ASR/MT worker, paired HY/EN and Me.
- Evidence, commands, primary references and limitations: DIARIZATION_COMPARISON.md.
  Stage4.2/4.3 remain pending. No commits or private recordings created.

## 2026-11-01 Stage 4.2 experimental live speaker tracking

- User authorized4.2. Promote the fixed CAMPPlus extractor/registry to production;
  Sherpa2.0.1 moves from dev to runtime without version changes. Opt in with
  --diarize on combined or System --live. Default commands and microphone/WAV stay.
- Keep speaker inference inside the existing spawned ASR/MT process. Initialize
  once before ready; missing/corrupt model aborts startup with no download/fallback.
  Preserve System as queue/accounting source, per-part SpeakerN/Unknown as display.
- Partition bounded VAD PCM into2s cells, probe halves for inconsistent embeddings,
  avoid learning inconsistent cells, classify short cells without learning, merge
  adjacent identical labels. Preserve every PCM byte and original timeline metadata.
  A full2s cell is necessary for a new ID, not proof of2s voiced single-speaker audio.
- Deliberate initial limitation: boundaries are quantized; mixed cells can remain
  Unknown or escape rejection. This is not full change-point/overlap detection.
  Do not claim word-accurate boundaries or Armenian-call quality before4.3.
- Registry persists across jobs/idle, bounded to8 configurable centroids, no ID
  recycling/expiry. Unknown text still reaches ASR/MT and the existing fragment guard.
  Each original job completes only on its final part. One fairness credit/job;
  per-part outputs, empty/filter counts and stage timing remain observable.
- More parts mean more MT calls and may exceed5s. Keep bounded shutdown/forced
  termination for slow embedding as for slow ASR. Real public A/B/A smoke verifies
  ordering/routing only; physical Ctrl+C verifies loaded models and capture closure.

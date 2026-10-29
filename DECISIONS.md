# Decisions

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

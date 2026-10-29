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

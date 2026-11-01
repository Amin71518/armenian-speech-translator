# Validation and limits

This file summarizes what was checked, what failed and what remains unproven.
Model comparisons and protocols are in [EXPERIMENTS](EXPERIMENTS.md), setup in
[README](../README.md), and the interview walkthrough in [DEMO_GUIDE](../DEMO_GUIDE.md).

## Latest runtime validation

After documentation consolidation: **225 tests passed in 22.02 s**, Ruff and
Poetry passed. The two added checks cover nested relative documentation links and
missing documents/targets. The delivery audit found no broken links, invalid chat
hashes, forbidden artifacts or credential-pattern matches. Hash comparison confirmed
that every runtime source file, dependency file and existing chat export/manifest
was unchanged. There are now four documentation files outside `chats/`.

Before documentation consolidation: **223 tests passed in 23.13 s**, Ruff and
Poetry checks passed. This includes actual Windows spawn tests with controlled
fake models, not 223 live-conversation accuracy tests.

The suite covers model configuration/local-only artifacts, separate capture/VAD
states, resampling, PCM conservation, queue fairness/drop accounting, paired HY/EN,
Me isolation, job/part completion, speaker gates, capacity without ID recycling,
startup failures, bounded shutdown and temporary-WAV cleanup. Exporter tests cover
verbatim text, duplicate storage records versus real repeated messages, exclusion
of internal transport fields and internal approval-review sessions.

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest-validation
poetry run ruff check .
poetry check
poetry run python -m scripts.check_submission
```

`python -m pytest` resolves the repository's namespace imports. Explicit basetemp
avoids the sandbox Windows Temp permission issue. Unit tests do not establish
diarization accuracy, translation correctness or physical speech-end latency.

## Real-device and pipeline evidence

Earlier stages exercised actual Windows WASAPI microphone/loopback capture,
simultaneous devices with inference, overload accounting and native Ctrl+C.
Both source streams were closed before final drain; worker startup/inference
failures and stopped devices propagate rather than silently falling back.
The reports distinguish real devices, file replay, injected load and fake models.

The last selected call reported:

| Metric | Observation |
| --- | ---: |
| Wall duration | 67.6 s |
| Accepted / completed jobs | 12 / 12 |
| System parts / Unknown System parts | 14 / 8 |
| Discovered IDs | 2 |
| Registered raw/phrase losses | 0 |
| Worker exit / unfinished jobs | 0 / 0 |
| Maximum VAD-decision to output | 1.886 s |

This is a short user-observed run without independent per-window speaker or word
annotations. Two IDs do not prove two correctly tracked people. Zero registered
losses do not establish a bit-perfect physical capture. Microphone ADC anomalies
remain unvalidated. The matching trial's extra-ID/overlap failures are retained in
[EXPERIMENTS](EXPERIMENTS.md), not hidden by its success on the supplied A/B clips.

The original full-WAV regression retained WER/CER 6.67%/2.03% on 15 FLEURS files.
After shorter live VAD cuts, a separate segmented comparison measured 11.67% WER.
Those are different processing conditions; full-file and live-fragment metrics
must not be substituted for each other. Translation quality on reference text
also does not establish translation quality on erroneous live ASR.

## Physical latency is not certified

The requirement is English output within 5 s of the **actual speech end**.
VAD-decision to output excludes the wait for that decision. Six seconds of audio
buffering is not a latency bound; more speaker parts create additional MT work.

An earlier 338.92 s nominal-rate replay completed 54/54 jobs but covered only
14 of 30 provisional natural endpoint intervals unambiguously. Twelve measured
cases were definitely within 5 s, two straddled the threshold, and sixteen were
uncovered/ambiguous. The measured-case midpoint maximum was 5.038 s. Uncovered,
filtered or ambiguous cases were not counted as fast successful outputs.

Endpoints were selected from waveform inspection independently of VAD. The author
waived listening verification, so they remain `human_verified=false`. WASAPI ADC
times appeared about 10 ms in the future despite precise stream-clock queries;
query precision is not physical ADC accuracy. No guessed correction was applied.

Two acoustic playback attempts failed reliable waveform alignment (0/6, then 0/3).
They completed their procedures but did not produce valid E2E measurements.
The failed five-file overload/drain run is also retained in the historical record.
Thus neither the latest call nor earlier replay certifies the <=5 s requirement.

## Delivery integrity

The public repository contains source, tests, documentation and three saved actual
Codex project conversations as separate Markdown files. `chats/EXPORT_MANIFEST.json`
records export/source hashes and snapshot counts. Internal automated approval-review
sessions are excluded. Original conversations remain available in Codex; exports
are record-derived snapshots, not reconstructed summaries or official UI exports.
Later conversations need a new refresh when the author chooses to include them.

The publication audit checks forbidden file paths/extensions, common credential
patterns, local documentation links and export hashes. Model weights, audio,
local fixtures, caches, environment and numeric reports stay ignored. The previous
history was also checked for audited audio/model paths and credential patterns;
these pattern scans cannot prove the absence of every possible secret.

Research numeric reports live locally under ignored `reports/`. This summary
keeps evidence accessible without committing weights or recordings. Clean-machine
installation was not repeated during documentation preparation. No new live
capture or model benchmark is needed for documentation-only consolidation.

Detailed stage journals are retained in the
[pre-consolidation Git snapshot](https://github.com/Amin71518/armenian-speech-translator/tree/d84653f60fd74a8fdafa14645a161854b80d4019).
The chosen prototype has known limitations; publication does not imply full
acceptance of all challenge criteria.

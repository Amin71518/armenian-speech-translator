# Stage 4.1 — speaker embedding experiment, 2026-11-01

This is the historical 4.1 experiment. Stage4.2 now offers opt-in experimental
live integration; current commands and limitations are documented in README.md.

## Decision

Use **CAMPPlus ONNX through Sherpa-ONNX 2.0.1, CPU, one thread** as the provisional
candidate for Stage 4.2. It matched TitaNet Small on this small held-out clip test,
with lower standalone working-set memory. This selects an embedding component;
it does **not** implement or validate full live diarization.

Current microphone, System Audio, combined and WAV commands are unchanged. The new
code is isolated under `scripts/`; no live module imports it. ASR and translation
models/revisions/settings remain FastConformer INT8 and NLLB-600M greedy.

## Reproduce

```powershell
poetry install
poetry run python -m scripts.prepare_diarization --models --data
poetry run python -m scripts.check_speakers
poetry run python -m scripts.check_speakers --candidate campplus --with-pipeline
poetry run python -m scripts.check_speaker_boundaries
poetry run python -m pytest -q --basetemp=.cache/pytest-stage41-review
```

Prepare data only once: preparation refuses a nonempty destination. For an existing
subset, run the check commands directly. `--models` can verify/reprepare models
separately. Inference never downloads models. Models are verified against pinned
upstream SHA-256 values before loading. All data/models/reports stay ignored by Git.
Only `sherpa-onnx==2.0.1` and its exact `sherpa-onnx-core==2.0.1` were installed in the
development group; Poetry reported no existing package updates/removals. No NeMo,
pyannote, CUDA, TorchAudio or external inference service was installed/used.

## Data and protocol

18 public LibriSpeech test-clean utterances, six each from speaker IDs **6930, 1320,
5639**. File names carry corpus speaker IDs. Fixed four-second crops start 250 ms
into each file; there is no manual speech-boundary annotation. The first two files
per speaker are reserved for calibration; only the first two speakers' four files
are actually used to fit the cosine threshold. This yields two positive and four
negative calibration pairs. Speaker 5639 is unseen during calibration.

Four different evaluation utterances per speaker are held out. Each length has
**14 decisions from 12 unique evaluation utterances**: A/B alternate, C appears,
A/B return using repeated clips, then C returns. Clusters are discovered online,
not forced to two or three. Expected IDs use ground-truth encounter order. These
are clip-label errors including Unknown, **not** DER, word-aligned speaker accuracy,
or 14 independent utterances. Crops at different lengths reuse the same files.
The threshold is fitted once from four-second calibration clips and is not retuned
on the evaluation set. Initial cluster identity is necessarily established by its
first clip. The sample is too small for a general accuracy claim.

Source: [LibriSpeech / OpenSLR12](https://www.openslr.org/12), Panayotov et al.,
CC BY 4.0. The preparation streams `test-clean.tar.gz` and stops after the selected
members. Manifest retains original paths, speaker IDs and individual source/PCM
SHA-256 values. The full archive checksum is **not verified**, because the full
archive is not downloaded. No private microphone recordings or transcripts are saved.

## Standalone CPU observations

Separate fresh processes, one inference thread each. Numeric reports:
`reports/stage41_campplus_1t.json`, `reports/stage41_titanet_1t.json`.

| Observation | CAMPPlus | TitaNet Small |
| --- | ---: | ---: |
| Model bytes, MiB | 26.97 | 38.39 |
| Model load, s | 0.499 | 0.212 |
| Sampled peak process RSS, MiB | 127.84 | 168.79 |
| Peak RSS above baseline, MiB | 86.18 | 127.14 |
| 2 s clip mean / max compute, ms | 27.75 / 30.22 | 23.03 / 25.88 |
| 4 s clip mean / max compute, ms | 48.90 / 51.15 | 48.27 / 56.35 |
| 2 s clip label errors / decisions | 0 / 14 | 0 / 14 |
| 4 s clip label errors / decisions | 0 / 14 | 0 / 14 |
| 1 s clip label errors / decisions | 7 / 14 | 7 / 14 |
| 1 s discovered clusters (actual speakers: 3) | 5 | 5 |

At 400 ms, all 14 inputs deliberately abstain before model execution. Silence also
abstains. These expected rejections appear in the JSON's errors-including-Unknown
counter and should not be interpreted as a model accuracy measurement.

Prototype: normalized embeddings, cosine similarity, bounded eight-centroid registry,
encounter-order IDs, no expiry or recycling, running centroid updates, ambiguity
margin 0.08. Ambiguous/short/silent/capacity-rejected inputs do not update centroids.
Calibration thresholds: CAMPPlus **0.47114**, TitaNet **0.47464**. These are experimental
values from a tiny English subset, not universal thresholds for Armenian calls.

## Coexistence and boundary probes

`reports/stage41_campplus_1t_resident.json`: load the unchanged ASR/MT pair, execute
public Armenian 001.wav once, run the speaker probes, then execute 001.wav again.
HY/EN results were identical before/after. CAMPPlus two-second compute averaged
**60.73 ms**, max **92.66 ms** in this process. The initial pipeline call was cold;
its 4.421 s versus 1.912 s after the experiment is not a performance comparison.
Models are resident and used sequentially, not running concurrent model inference.
The Windows RSS baseline was 2844.65 MiB and sampled RSS did not exceed that baseline;
working-set paging/reuse means this does **not** establish zero incremental memory.
Standalone fresh-process memory above is the useful candidate comparison. RSS is
sampled every 20 ms and can miss short peaks.

`reports/stage41_boundaries.json`: concatenate held-out A/B/A/B four-second clips in
RAM and pass them through the **existing** LiveVAD/Silero configuration. With 800 ms
inserted pauses, four VAD segments each contain only one file's source. Without
inserted pauses, all three resulting VAD segments cross file-speaker boundaries:
the first two include substantial amounts of both voices, the last includes a
116 ms tail of the preceding voice. Ownership includes silence within each original
file and is not independently labelled speech activity. This demonstrates why a
single embedding/label per existing six-second ASR chunk is insufficient.

Synthetic overlap (sum of A and B) and a within-clip A-to-B change both pass the
embedding extractor. It has **no overlap detector**; a dominant voice may receive
a confident match. A similarity margin alone does not reliably reject overlap.

## Stage 4.2 implementation requirements

- Apply only to System; keep microphone `Me` and paired HY/EN output.
- Track voice changes inside System VAD audio before ASR; evaluate short rolling
  embedding windows and the cost/accuracy of their boundaries. Simply relabelling
  existing chunks would combine different speakers' text.
- Require sufficient voiced evidence (initial target around 2 s) for new IDs;
  preserve Unknown for unreliable material. Do not suppress short useful ASR text
  merely because speaker identity is unknown. This two-second policy is a proposal,
  not already implemented in the experimental one-second failure probe.
- Keep speaker state across System idle bursts; reset it at session restart. Bound
  speaker/audio state, measure added queue/compute/context delay, preserve one ASR/MT
  worker, source fairness, loss accounting and bounded Ctrl+C cleanup.
- Validate Armenian voices, same-room/channel changes, short answers and returning
  voices on independent material. The present experiment uses clean English reading
  with oracle clip boundaries; it does not certify real calls, noise, overlaps,
  continuous change detection or physical end-of-speech latency <=5 s.

## Primary references

- [Sherpa speaker embedding API example](https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/speaker-identification.py)
- [Published ONNX models and checksums](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models)
- [3D-Speaker upstream](https://github.com/modelscope/3D-Speaker)
- [TitaNet ONNX export provenance](https://github.com/k2-fsa/sherpa-onnx/tree/master/scripts/nemo/speaker-verification)
- [Sherpa diarization architecture](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html)

Sherpa's offline segmentation/clustering API is a separate design option; rerunning
offline clustering per chunk would need explicit cross-chunk ID matching. This
experiment intentionally selects a lightweight embedding component for session state.

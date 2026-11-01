# Model choices and experiments

This record explains the selected models, the comparisons that informed them and
the failures that remain. Results are historical observations on small datasets,
not guarantees for new calls. Setup, pinned ASR/NLLB revisions and architecture
are in [README](../README.md); current checks are in [VALIDATION](VALIDATION.md).

## Armenian recognition

Fifteen distinct FLEURS Armenian test sentences, 138.96 s total, converted to mono
PCM16 16 kHz. File hashes and aligned HY/EN references are retained in the local
manifest. Dataset revision: `70bb2e84b976b7e960aa89f1c648e09c59f894dd`.
Manifest SHA-256: `8d7e72f87970345fc5dd454f3f0368d63fcfae325eaf7a7185cf940dd582854c`.

Each backend ran in a separate process with four CPU threads, one model load and
two sequential passes over the same files. The following are second-pass ASR-only
measurements, excluding loading, translation and metric calculation. RSS is sampled
process memory, not an exact peak or model-weight size.

| Model and decoding | WER | CER | Mean / max ASR, s | Sampled RSS, MiB |
| --- | ---: | ---: | ---: | ---: |
| Whisper Base, original temperature schedule | 123.75% | 104.28% | 9.117 / 11.394 | 429.54 |
| Whisper Base, explicit temperature 0 | 297.92% | 121.65% | 1.031 / 1.107 | 309.23 |
| Vana-Labs FastConformer RNN-T INT8 | **6.67%** | **2.03%** | **0.139 / 0.207** | 453.00 |

Whisper's beam size 1 did not make its original temperature-fallback schedule
strictly greedy. Auditing the decoder and separately setting temperature 0 removed
expensive retries but did not fix recognition. The original combined Base/Marian
run had WER 137.92%; its timing and memory included translation and cannot replace
the ASR-only comparison above. WER can exceed 100% because of insertions.

Scoring uses corpus WER/CER after NFC, casefold, Unicode-punctuation removal and
whitespace folding. Numbers written as words and digits are not made equivalent.
FastConformer still made name, number and lexical errors. Fifteen read sentences
are not independent conversational validation, and independence from model-training
data was not established. FastConformer was selected for accuracy and CPU speed;
INT8 runs through ONNX Runtime without NeMo or CUDA.

Sources: [Vana-Labs model](https://huggingface.co/Vana-Labs/stt-fastconformer-armenian),
[FLEURS](https://huggingface.co/datasets/google/fleurs).

## Translation evaluated separately

Translators received the same fifteen correct normalized Armenian reference texts,
not ASR hypotheses. Aligned English references were scored with corpus chrF++
(SacreBLEU 2.6.0, word_order=2). This 0–100 metric is reference similarity, not a
percentage of correct translations. FLEURS/FLORES material is not an independent
conversational test for NLLB.

Separate processes, CPU float32, four threads, batch 1, two passes, no sampling,
greedy decoding. Loading was separate. Final second passes used AC power:

| Model | chrF++ | Mean / max MT, s | Sampled RSS, MiB |
| --- | ---: | ---: | ---: |
| Marian HY to EN | 32.88 | 0.186 / 0.359 | 639.60 |
| NLLB-200 distilled 600M | **57.86** | 1.335 / 2.007 | 2758.32 |
| M2M100 418M | 39.61 | 1.085 / 1.738 | 2233.56 |

NLLB costs more CPU/RAM but retained more meaning on this sample. Beam 2 scored
56.83 and was slower; its changing power/load conditions prevent a precise causal
speed comparison. Greedy was retained. NLLB can still omit subjects, change names
and numbers, confuse riders with horses or Luna with a swimming pool. Translation
quality on correct references is distinct from translation of erroneous ASR text.

Language controls are explicit (`hye_Armn` to `eng_Latn`, forced target BOS).
Live oversized text is split by actual tokenizer counts without truncation; the
original WAV interface retains its input-limit error. Prepared local snapshot paths
avoid an unwanted Transformers metadata request. Sequential downloads avoided a
Windows symlink-detection race; installed libraries were not patched.

Original selected full-WAV chain: 15/15 files, mean/max 1.660/2.805 s, sampled RSS
3076.56 MiB, WER/CER 6.67%/2.03%. Those are file-processing times, not speech-end
live latency. Later observations were slower under different conditions; they do
not prove a cleanup-induced slowdown or performance equivalence.

Sources: [NLLB](https://huggingface.co/facebook/nllb-200-distilled-600M),
[M2M100](https://huggingface.co/facebook/m2m100_418M),
[SacreBLEU](https://github.com/mjpost/sacrebleu).
NLLB is CC-BY-NC 4.0; choosing it for this research challenge does not authorize
commercial use. Review upstream model terms before reuse.

## Streaming and latency tradeoffs

Separate VAD/resampler states prevent cross-source state contamination. Bounded
queues and a spawned worker keep inference out of capture callbacks and allow
terminating stalled native inference. Fair dispatch protects source queue slots;
it does not preempt an already admitted job or guarantee wall-time latency.

Shortening VAD fragments from the earlier 12 s cap to a 6 s cap with preferred
pauses after 3.5 s increased output frequency, but on the same files segmented
WER rose from 6.67% to 11.67% (16 to 27 fragments). Boundaries can cut words.
A trial unconditional -50 dBFS gate lost detections in 5/15 valid WAVs and was
rejected; the RMS floor remains opt-in. The live isolated-letter guard reduces
unnecessary translation of fragments but is not a cough/noise classifier.

A five-file nominal-rate replay on battery exposed queue drops and the 15 s drain
timeout. A later AC run completed 10/10 jobs without drops; different conditions
prevent a causal speed claim. Translation and queueing remain bottlenecks.
Independent latency results and failed acoustic alignment are retained in
[VALIDATION](VALIDATION.md), including uncovered endpoints rather than counting
them as fast successes.

## Speaker embedding selection

Eighteen public LibriSpeech test-clean utterances, six per corpus speaker ID
6930/1320/5639. Two files per speaker were reserved for calibration; only four files
from the first two speakers fitted the threshold. Four evaluation files per speaker
yielded 12 unique held-out utterances and 14 decisions per duration, including
repeated A/B return probes. Clips start 250 ms into the source. File ownership is
known, but speech/overlap boundaries were not independently annotated.

Both candidates used Sherpa-ONNX 2.0.1 CPU, one thread, normalized embeddings and
an online registry. Thresholds fitted on four-second calibration clips were 0.47114
(CAMPPlus) and 0.47464 (TitaNet); live CAMPPlus uses 0.47 and margin 0.08. These
are not Armenian-call calibration values.

| Observation | CAMPPlus | TitaNet Small |
| --- | ---: | ---: |
| Label errors at 2 s and 4 s | 0/14 at each length | 0/14 at each length |
| Label errors at 1 s | 7/14 | 7/14 |
| Clusters at 1 s, three true corpus speakers | 5 | 5 |
| Mean / max 2 s compute, ms | 27.75 / 30.22 | 23.03 / 25.88 |
| Standalone sampled peak RSS, MiB | 127.84 | 168.79 |

400 ms and silence were deliberately rejected before native inference. These are
abstentions, not measured model misclassifications. CAMPPlus was chosen for lower
memory with comparable results at useful lengths. With ASR/MT resident its 2 s
compute was 60.73/92.66 ms mean/max; zero measured RSS increase over a warmed
process does not establish zero memory cost. Coexistence preserved one Armenian
probe's HY/EN, not general throughput or latency.

VAD A/B clips with 800 ms inserted pauses produced separate source segments;
without pauses all three VAD chunks crossed source boundaries. Synthetic overlap
and voice changes passed embedding extraction. An embedding is not an overlap
detector, so one label per VAD chunk was insufficient.

Sources: [LibriSpeech](https://www.openslr.org/12),
[Sherpa model checksums](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models),
[3D-Speaker](https://github.com/modelscope/3D-Speaker).
Preparation verifies selected file/model hashes; it does not verify the entire
streamed LibriSpeech archive, which was not fully downloaded.

## Speaker matching failures and selected trial

The first live tracker used 2 s cells, a half-window consistency gate, and a session
registry of up to eight centroids. New IDs needed a full cell. Unknown was retained
as speech for ASR/MT. Calls exposed duplicate identities and excessive abstention.

Context accumulation, merging Unknown into neighboring speech and extra filters
were tried earlier and rejected after worse user calls. They were rolled back.
The current trial does not restore them or force a two-person limit.

Diagnostics established distinct failure mechanisms:

- A known voice can have a strong full-window match but low half-to-half similarity,
  causing Unknown. A half below RMS 0.003 can also block a loud enough full cell.
- A new voice represented only by <2 s replies could never register in the baseline.
- Synthetic 300–3400 Hz filtering after enrollment produced five IDs for three
  public voices. Freezing centroid updates worsened this to six IDs and 2 s under
  another person's ID. Returning original clips recovered the original IDs.
  Therefore centroid update alone did not explain that channel-induced failure.

The author supplied two single-voice public excerpts: [A](https://www.youtube.com/shorts/eVz3O9Z6h7g)
at 0–15 s and [B](https://www.youtube.com/watch?v=-n9QX6VAaUM) at 42–44 s.
Actual Silero produced A segments of 6/6/3.248 s and B of **1.648 s**. On A/B
repeated three times, B never registered with the baseline. These exact excerpts
reproduced the failure, but repeating them does not create independent evaluation.

The selected opt-in `--experimental-speaker-matching` makes two changes:

1. An unmatched 1.5–<2 s cell may enroll after its first/last one-second views agree.
   Those views overlap and are not independent evidence. No cross-reply audio is
   accumulated; known short matches do not train centroids.
2. A rejected full cell may keep an existing ID only when full embedding and both
   separate halves each match that ID under the existing threshold/margin.
   This exception neither trains nor creates an ID. A missing/ambiguous/different
   half still rejects. The normal first4.2 rules remain available without the flag.

| Exact source replay through real ASR/MT | Baseline | Selected trial |
| --- | ---: | ---: |
| Completed / accepted jobs | 12/12 | 12/12 |
| Discovered IDs | 1 | 2 |
| Unknown output parts | 6 | 0 |
| Total output parts | 15 | 12 |

Both workers exited normally and temporary WAVs were cleaned. This paced direct-file
replay does not model Bluetooth/WASAPI processing, word accuracy or speech-end E2E.
Default tracker/reference comparison also preserved labels/PCM/centroids/model-input
sequence on 150 jobs/169 cells. That is a regression check, not quality acceptance.

Adverse controls remain important: short enrollment from 1.25 s produced a duplicate
on clean 1.264 s clips; the selected 1.5 s policy produced six IDs for three voices
after synthetic band changes, with 1.52 s assigned to another person. The anchored
exception accepted one 2 s overlap cell that baseline rejected. Some short mixed
windows already get one label in baseline; the trial could also create a mixed ID.
These outcomes are why the selected mode remains explicitly experimental.

On the latest chosen 67.6 s real-call run, 12/12 jobs completed and two IDs were
created, but **8/14 System output parts were Unknown**. Short 1.072–1.328 s replies
preceded enrollment at 1.552 s. No registered capture/queue losses were reported.
Exact per-window identities and reference words were not annotated; no DER/WER
is claimed. The author chose this state for submission with its limitations.

## Reproduction and preserved history

Current ASR/MT checks on prepared local evaluation data:

```powershell
poetry run python -m armenian_speech.benchmark --passes 2 --report reports/asr.json
poetry run python scripts/check_translation.py --manifest data/local/fleurs/manifest.jsonl --offline --report reports/translation.json
poetry run python -m scripts.check_speakers --candidate campplus
```

The speaker/candidate/user-source probes require their documented ignored fixtures;
they do not download implicitly. User-source provenance is in the local
`data/local/user_source_sections/PROVENANCE.json`. Some old baseline probes also
need the SHA-verified local `.cache/first42-speakers-baseline.py`, not shipped in Git.
Research scripts identify their scope; do not infer a call benchmark from them.

Run benchmarks sequentially. Rejected backends and removed flags are historical;
do not reintroduce them into the runtime to reproduce an old result. Full original
comparison, decision and test journals remain in the
[pre-consolidation Git snapshot](https://github.com/Amin71518/armenian-speech-translator/tree/d84653f60fd74a8fdafa14645a161854b80d4019)
and unedited project chats. This consolidation does not rewrite Git history.

# Mathrix submission checklist

Snapshot selected by the author on 1 November 2026 after reviewing the live-call
result. The author authorized delivery preparation and deferred GitHub until the
last step. Runtime/model changes are frozen for this preparation. Selecting a
snapshot does not turn incomplete requirements into passing measurements.

The checklist is derived from the supplied `Mathrix_AI_Coding_Challenge.docx`.
The brief is an assessment specification, not an instruction to publish, contact
anyone, commit, or overwrite work automatically.

## Requirements and evidence

| Requirement | Status | Implementation / evidence |
| --- | --- | --- |
| Python on the interview laptop | Implemented on Windows 11/Python 3.13 CPU | `pyproject.toml`, `poetry.lock`; Windows device/worker checks in TESTS.md |
| Concurrent microphone and system audio | Implemented | `combined.py`, independent VADs, `fair_queue.py`; actual simultaneous-device checks and latest call |
| Explicit device selection | Implemented | `--list-devices`, `--microphone-device`, `--device`; README explains separate numbering and endpoint routing |
| Armenian text | Implemented, accuracy limited | FastConformer INT8; historical full-WAV WER 6.67%, not a live conversation score |
| English translation | Implemented, quality limited | NLLB greedy, paired HY/EN; historical reference-text chrF++ 57.86 |
| Microphone labelled Me | Implemented | Per-job source metadata bypasses System tracker; spawn tests and user call logs |
| Different remote people retain IDs | Partial | Session registry/trial; exact supplied clips yield two returning IDs; call still has frequent Unknown and channel/overlap errors |
| Time, speaker, HY and EN together | Implemented | Parent `output.py` after ASR and MT; no standalone provisional HY output |
| <=5 s after actual phrase end | Not certified | Physical clocks/independent endpoints remain unvalidated; VAD-decision time is a different metric; prior overload failures retained |
| Local inference only | Implemented | Prepared local ONNX/PyTorch models; network only in preparation, no cloud inference/API key |
| Model choices and alternatives explained | Documented | README and ASR/TRANSLATION/DIARIZATION comparison documents |
| Source code | Available locally; Git staging pending | `src/`, `scripts/`, `tests/`; substantial existing untracked work must be intentionally included at final Git step |
| Setup, audio routing, architecture and limitations | Documented | README.md; DEMO_GUIDE.md for rehearsal |
| Complete project AI conversations, separate Markdown files | Local snapshot exported; refresh/review pending | Three actual project conversations; internal approval reviews excluded; `chats/EXPORT_MANIFEST.json`, CHAT_EXPORTS.md |
| Original AI history available at interview | Retain in Codex | Three main app chats found; do not archive/delete originals as a packaging step |
| No weights, audio or keys in repository | Ignore rules and local audit | `.gitignore`; final Git selection must be reviewed again before publication |
| Send repository link | Deferred by author | Public empty repository created for Amin71518; source commit/push awaiting approval |

## Selected launch configuration

```powershell
poetry run python -m armenian_speech.combined --microphone-device 14 --device 16 --diarize --experimental-speaker-matching
```

Check IDs on the laptop first. This example uses the built-in microphone and Buds
playback. Add `--speaker-diagnostics` for investigation; omit it for the ordinary
paired terminal output. Keep the experimental flag: omitting it selects the
retained first4.2 baseline. Do not change default matching policy silently.

The latest chosen call ran for about67.6s, accepted/completed12/12jobs and discovered
two IDs, with8/14System parts Unknown. No registered raw/phrase losses were reported.
The speaker count/Unknown frequency alone does not establish correct identities.
The user selected this state despite the limitations; it is not a complete4.3
accuracy/DER acceptance result.

## Before the final GitHub step

- [x] Preserve previous README as DEVELOPMENT_HISTORY.md.
- [x] Prepare an evaluator-facing README and a laptop demonstration guide.
- [x] Keep model alternatives, failed experiments and uncertainty visible.
- [x] Produce per-session exports from stored records, not reconstructed summaries.
- [ ] Refresh the active chat export after the last project conversation.
- [ ] Review exported chats/manifest for completeness, attachments and any additional
  sessions from other directories/accounts. Local cwd matching cannot prove none exist.
- [x] Run final validation and record it in VALIDATION_REPORT.md (222tests, Ruff, Poetry).
- [ ] Review the final Git selection/diff with the author at the GitHub step.
- [ ] At the author's final GitHub step, select source/docs/tests/chats, preserve
  intended history and confirm the existing staged deletion `chats/README.md`.
- [ ] Obtain the author's commit approval; choose repository visibility and publish
  only when instructed. These steps have deliberately not been performed yet.

No installer, GUI, echo cancellation, persistent speaker names, cross-session voice
database, saved transcripts, or non-Armenian input support is required by the brief.
No new feature has been added for those out-of-scope items during preparation.

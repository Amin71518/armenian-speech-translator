# Submission preparation validation 1 November 2026

Publication update: the author subsequently approved commit/push; source commit
b7bbc95 is published on `main`. Export classification correction added a regression
test: **223 passed in23.13s**. See PUBLICATION.md. The222-test results below remain
the earlier documentation checkpoint, not the final publication test count.

The author selected the existing runtime snapshot with known limitations and
authorized documentation/delivery preparation. No audio capture, new model run,
runtime algorithm change, Git staging, commit or publication was performed during
this preparation. Earlier model/call measurements remain historical evidence.

## Current checks

| Check | Result |
| --- | --- |
| Full suite | **222 passed in20.05s** |
| Ruff | Passed |
| Poetry metadata/lock validation | Passed |
| Combined/System/WAV CLI help | Passed; selected flags exist |
| Local delivery links | Passed |
| Forbidden audio/model/cache candidates | None found in Git candidates |
| Credential pattern scan | No matches; not proof that all possible secrets are absent |
| Saved chat inventory | Three actual project conversations; automated internal review sessions excluded |
| Chat export hash/incomplete-tail check | Passed at snapshot; refresh again before publication |
| Runtime source preservation | Verified against the packaging-start hashes |
| Previous README preservation | DEVELOPMENT_HISTORY.md is byte-identical to the previous README |
| Existing Git index | Preserved, including staged deletion of chats/README.md |
| GitHub / commits | Empty public repository created later; source commit/push awaiting approval |

The prior runtime release had218tests. Four added tests cover export filtering,
verbatim Unicode/spacing/source preservation, duplicate storage records versus
actual repeated messages, and exclusion of internal transport metadata while
retaining tool-output text. These tests verify the exporter, not model quality.

```powershell
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest-submission-release --junitxml=reports/submission_release_tests.xml
poetry run ruff check .
poetry check
poetry run python -m scripts.export_project_chats
poetry run python -m scripts.check_submission --report reports/submission_audit.json
```

JUnit/numeric audit artifacts are local under ignored `reports/`. The repository
contains this human-readable record so the result is not dependent on committing
private logs, audio or model weights. A clean environment still requires model
preparation before inference. A clean-machine installation was not repeated for
this documentation-only preparation.

## Requirements still limited

The <=5s physical speech-end criterion remains unconfirmed. Speaker identity is
partial: the chosen call completed12/12jobs, found twoIDs and reported8/14System
parts Unknown. Reported VAD-decision timing is not physical end-to-end latency.
The short-reply/channel/overlap limitations in README and SPEAKER_MATCHING_TRIAL.md
remain unchanged. The author selected this snapshot; no scientific accuracy or
complete challenge acceptance is inferred from that choice.

The local conversation exporter is record-derived, not an official Codex UI export.
It preserves stored message bodies and visible tool records, omitting internal
runtime instructions/transport records. The active conversation is necessarily a
snapshot; refresh after the final project turn, verify session scope/attachments,
and keep the originals in Codex. This check cannot discover conversations on other
machines/accounts or prove they do not exist.

GitHub repository creation, final file selection, author-approved commits, final
chat refresh/review and publication remain the explicitly deferred final step.

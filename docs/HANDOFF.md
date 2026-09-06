# Alpha handoff

AI Clarity is an experimental alpha, not a completed v0.1 release. Owner-approved live installation was verified on 2026-09-06. Automatic model compliance remains a release gap; see [live activation](LIVE_ACTIVATION.md).

## Available now

- Portable English/Chinese skill with five context presets and separate checks for meaning and protected text.
- Python standard-library helper for approved preferences, per-answer edits, feedback, version identity, comparison HTML, export, deletion, and undo.
- Hermes staging, explicit activation, and uninstall tools exercised against temporary homes.
- Deterministic tests and authored evaluation scenarios. See [verification](VERIFICATION.md) for evidence and outstanding acceptance criteria.

## Post-implementation review round

Two independent read-only reviewer passes reproduced seven actionable defects. The fixes and regression coverage are documented in VERIFICATION.md (43 test executions green): stored revisions that fail their own preservation check now refuse to load; an accepted edit consumes its widget version so an interleaved feedback click can no longer strand the edit; feedback during a pending edit is rejected outright; expired answer text and widgets are pruned in a committed step before dispatch, so a failed stale click cannot roll the cleanup back; widget temp files are created owner-only and orphaned `.tmp` copies are pruned; uninstall now prints an explicit notice that private reader data survives removal, with the wipe procedure; an explicit language override no longer leaves a contradicting language preference in the model bundle; and directories added to a staged package are inventoried, so uninstall refuses instead of silently removing them.

## Try without changing normal chats

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 adapters/hermes/stage.py stage --home "$PWD/.local/hermes-demo"
```

The second command stages an inactive copy. It refuses to overwrite an existing installation. For isolated activation and uninstall, follow [the adapter guide](../adapters/hermes/README.md). Staging by itself does not make a live agent use the skill. The helper does not generate explanations; a compatible host model must read the skill and perform the rewrite.

## Approved rollout and remaining work

The owner approved default-profile installation, the contributor-status correction, and initial public publication under the AI Clarity name. Installation and the correction are complete.

1. Improve and measure automatic invocation across models. A fresh-session test skipped the workflow despite receiving the installed instruction.
2. Verify a saved preference in a fresh Desktop session, real comparison controls, and edits to the same artifact. These cannot be replaced by passing Python tests.
3. Complete English/Chinese meaning and comprehension evaluation before declaring v0.1 ready. Obtain consent for any real reader samples.

## Blockers encountered

- An initial coding worker was interrupted. Repairs and verification continued independently.
- The installed headless browse tool could not start because its required Chromium headless executable was missing. No browser was downloaded. Static HTML parsing and protocol tests are not browser or live Hermes verification.
- The earlier blocked contributor-status edit was applied after explicit owner approval.

## Known limits

- Always-on behavior depends on model instruction following. There is no guaranteed output interceptor.
- Meaning preservation still needs model review, followed by human evaluation for release claims. A `meaning_checked` flag is an assertion from the host, not an independent semantic validator.
- Windows is unsupported by the POSIX storage helper. macOS is exercised; Linux still needs a test run.
- Preference offers use a small fixed vocabulary. Repeated-feedback inference, automatic model training, and universal agent integrations are deferred.
- Standalone HTML has inert agent buttons and says so. Real button actions require the Hermes bridge.
- The installer assumes one operator and refuses modified packages or instruction blocks instead of overwriting them.

# Live activation checkpoint — 2026-09-06

## Verified installation

The owner approved installation in the default Hermes profile, the contributor-status correction, and public source publication under the AI Clarity name.

- Installed `0.1.0-alpha.1` using the shipped `stage` and `activate` commands.
- Verified the installed package against its recorded inventory and hashes.
- Verified exactly one instruction block and byte-for-byte preservation of the pre-existing `SOUL.md` content outside that block. A private backup was retained locally.
- Invoked the installed helper's `prepare` successfully with the configured reader/host identity. No real reader preference was invented or saved.
- Re-ran `python3 scripts/verify.py`: 43 test executions passed, with no static-check errors.

This verifies installation, not reliable automatic invocation. Live uninstall was not exercised; temporary-home round trips remain the uninstall evidence.

## Fresh host-session probes

Both probes started new `hermes chat --oneshot` processes outside the project directory, without a slash command or skill preload. They used the installed default-profile instructions and requested explanations of authored HTTP 429/backoff/idempotency status text. They did not request code changes or test execution.

| Probe | Observed result |
| --- | --- |
| English, configured default `qwen3.8-flash` | Completed with zero tool calls. Skipped the required skill/helper workflow. The answer also overstated implemented backoff as a working/completed mitigation; the source did not establish that verification. |
| Simplified Chinese, explicit `gpt-6-astra` via `openai-codex` | Automatically loaded AI Clarity and its references. Attempted `prepare`, but the non-interactive host's command approval policy blocked both attempted invocation forms. Returned a plain answer with the blocker disclosed; did not complete capture/render. The answer distinguished implementation from verified effectiveness. |

The test summaries were checked against the exact sessions' stored tool-call records. Neither probe proves a completed automatic comparison workflow. The second probe did not alter the default model. No approval policy was weakened to make the test pass.

Raw CLI logs, session identifiers, and backups remain private and are excluded from the public repository. Model judgments about answer quality are not human comprehension measurements.

## Remaining release gates

- Reliable automatic preparation and comparison across supported models and host approval policies.
- A fresh Hermes Desktop session with real button dispatch, same-file revisions, explicit remember/undo, and stale-click rejection.
- Saved-preference behavior across fresh live host sessions. Earlier isolated CLI-process selection tests are separate evidence.
- Streaming behavior and independent English/Chinese semantic and comprehension evaluation.
- Linux execution; Windows remains unsupported.

Keep the release labeled experimental alpha. A successful install and green helper tests must not be represented as a fully verified live experience.

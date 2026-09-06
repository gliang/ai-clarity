# Verification report

## Status

Experimental alpha, not a completed v0.1 release. The implementation and fixes below were independently exercised. On 2026-09-06, the owner approved live Hermes installation and public alpha publication. The installed package hashes and preservation of the existing SOUL.md content were verified; the deterministic suite again passed all 43 executions.

Environment: Python 3.9.6, macOS/Darwin arm64. No third-party Python dependencies were installed.

## Executed deterministic checks

```sh
python3 -m unittest discover -s tests -v
```

Result at the parent verification checkpoint: **43 test executions passed** (also green in a clean source-copy checkout without `.local`). Some classes inherit the storage contract tests; this is the runner's execution count, not 43 distinct requirements or independent model evaluations.

The same suite also passed in an isolated source copy containing tests, skills, adapters, evaluation fixtures, and LICENSE, with no pre-existing `.local` directory. This checks clean-checkout behavior and relative helper paths without global installation.

Test locations:

- `tests/test_clarity.py`: storage, approval, scopes, overrides, version targeting, literal fallback, injection escaping, opt-out, retention, reset, undo, and malformed-state refusal.
- `tests/test_integration.py`: fresh-process CLI operations, concurrent preference writes, all authored scenario input routing, localized HTML action envelopes, and profile isolation.
- `tests/test_staging.py`: self-contained inactive packaging, temporary-home activation, installed-helper execution, uninstall, modified-file refusal, symlinks, and malformed manifests.
- `tests/test_regressions.py`: no storage for exact-output requests and readable preference offers in English, Simplified Chinese, and Traditional Chinese.

For a repeatable test log plus syntax, JSON, skill metadata, and relative-document-link checks, run `python3 scripts/verify.py`. It writes actual output under ignored `.local/verification/`. It does not perform inference or browser testing.

CI runs the same verification on push/PR to `main` across ubuntu-latest and macos-latest with Python 3.9 and 3.12; all four matrix jobs are required status checks alongside mandatory review. This provides the first Linux execution evidence (see PR #1 run: all four jobs green).

## Parent RED/GREEN record

These are observed failures, not reconstructed results:

1. The initial suite ran 35 tests with four subtest errors. The integration loop expected `original` on multi-turn evaluation protocols that intentionally have no source answer. The test now validates those protocol records separately and executes routing on input scenarios. The suite then passed.
2. New exact-output tests failed because `prepare` and `capture` created private directories before bypassing output handling. Dispatch now bypasses storage first. Both regressions passed.
3. An isolated source-copy run failed because tests assumed `.local` already existed. Test setup now creates its development artifact parent. The clean-copy run passed.
4. EN/Hans/Hant preference-offer tests failed because widgets displayed raw configuration JSON with English values. Offers now show localized wording and context/language scope. All three language subcases passed.
5. A new regression failed because `validate_state` called the preservation check but ignored its return value: a stored revision that dropped a protected literal or code fence loaded successfully. `validate_state` now re-derives the preservation result and refuses to load a record whose revision does not survive its own check. The regression passes; full suite is green.
6. A separate read-only reviewer subagent reproduced three further defects (report under ignored `.local/review/`): a pending edit could be stranded by an interleaved feedback click (controls permanently rejecting edits afterwards); expired full-text snapshots survived because cleanup rolled back whenever the next invocation failed (a stale click always raises); and uninstall silently left answer text in the private data root forever after the pruning helper was removed. Fixes: accepted edit actions now consume the widget version and feedback is refused while pending (two new regressions, RED then GREEN); expiry pruning commits before dispatch, so even a failed stale click deletes expired text and widgets; widget temp files are created `0600`, orphan `.tmp` files are pruned, and uninstall prints an explicit data-left-behind notice plus wipe procedure. Adapter and skill docs state the new version rule.
7. An earlier reviewer round reported two more issues, reproduced with new RED tests then fixed: an explicit language override routed correctly but left a contradicting stored `language` preference in the model bundle (now corrected to the resolved route only when a language choice was actually in play, so unrelated bundles stay empty); and package inventory recorded files only, so a directory added after staging was invisible to verification and uninstall removed it anyway (directories are now inventoried and refuse uninstall). Full suite: 43 green; clean-checkout and model-smoke readback re-run after the protocol change.

The interrupted worker's entire development history is not treated as independently verified test-first evidence.

## Model-assisted smoke (isolated, test-only)

A live Hermes subagent performed real rewrites (its own model output, not fixture `expected` strings) through the helper in an isolated root with a TEST-ONLY approved `code/troubleshooting` preference:

- English and Simplified Chinese originals were rewritten into numbered status / uncertainty / next-check answers that preserved the exact `HTTP 429` literal and the "idempotency unverified" caveat.
- Fresh `clarity.py` **CLI processes** (not fresh Hermes sessions) loaded the saved preference, captured, re-read, and rendered each case; artifacts are under ignored `.local/model-smoke/`.
- An unrelated `research` prepare returned `{}` preferences, confirming no cross-context leak.
- The parent independently re-ran `prepare`/`get`/`render` against those artifacts (`.local/verification/check_smoke.py`): stored text matched the model output, HTML contained both original and revision, versions/identities were consistent, and research scope stayed clean.
- This is **model self-review + deterministic persistence**, not independent semantic evaluation, fresh-host-session behavior, live activation, or human comprehension evidence.

## Release acceptance map

“Deterministic” means Python executed the behavior. It does not establish model compliance or reader comprehension.

| Product criterion | Evidence / current gap |
| --- | --- |
| Approved preference affects a relevant answer in a fresh session without a slash command | Fresh-process preference selection passes. Live probes did not complete the automatic workflow: one skipped it; another loaded the skill but helper invocation was approval-blocked. See LIVE_ACTIVATION.md. |
| Current-answer edit does not become a lasting preference | Action/revise/remember and not-now tests pass; real clicks remain unverified. |
| Narrow preference does not leak to unrelated tasks | Context/topic/language and user/host isolation tests pass. |
| Current instructions override stored styles | `prepare` precedence tests pass; host interpretation still requires evaluation. |
| Undo/forget removes future applicability | Profile and widget-bound undo tests pass. |
| Actual original and exact response/version survive inline edits | Original storage, version history, stale-token rejection, and HTML envelopes pass; real bridge behavior remains unverified. |
| Material facts, warnings, and uncertainty survive rewrites | Exact-span/fenced-code/URL fallback tests pass. Semantic preservation depends on host review; no human comprehension claim is made. |
| No extra service or publication of private data | Helper has no network calls. Data roots and exports are documented. Public source excludes private runtime data; live installation is opt-in. Host-model inference may send selected data to its configured provider. |
| Feedback opt-out and deletion | Disable/reset/retention tests pass; comparison snapshots have separate disclosed retention. |
| All five contexts in English and Chinese | Authored scenario routing and protected-span checks run in both languages. These are not completed model rewrites across the matrix. |
| Simplified, Traditional, mixed input, and explicit translation | Routing and localized labels pass. Natural-language quality still needs bilingual model/human evaluation. |
| Domain evidence strength and verification status survive | Fixtures and skill rules cover them; deterministic spans alone cannot verify semantics. |
| Business-format preference does not shorten research | Scoped selection test passes. Fresh live-answer comparison remains open. |
| Language-specific preference stays in its scope | Scope tests pass, including neutral preferences and explicit overrides. |
| Context/language override does not save a preference | Action flow tests pass. |
| Clear short answer unchanged; exact JSON/code-only gains no extras | No-op renderer and exact-output bypass tests pass. |
| New-session tests check answer behavior, not only persistence | Deterministic portion passes. Two authorized live-host probes exposed compliance/approval gaps; a successful end-to-end run remains a release gate. |
| Deterministic, model-assisted, and human evidence separated | This report and evals/README.md keep those evidence classes separate. No human scores exist. |

## Live checkpoint and remaining gaps

- **Headless browser:** the installed browse binary failed to launch because its required Chromium headless executable was absent. No browser dependency was installed. HTML was parsed in tests, not visually or interactively verified in a browser.
- **Live Hermes:** owner-approved default-profile installation is verified. A fresh CLI-host session received the instruction but skipped the helper workflow. Hidden-turn clicks, a fresh Desktop session, and streaming behavior remain unverified. See [live activation](LIVE_ACTIVATION.md).
- **Human evaluation:** no participants, comprehension score, preference-uplift result, or validated self-improvement claim.
- **Linux:** now verified by CI (ubuntu-latest, Python 3.9/3.12, `scripts/verify.py` green); Windows is not supported by the POSIX helper.
- **Contributor status:** the previously blocked `AGENTS.md` correction was applied after explicit owner approval.
- **Initial worker:** interrupted before completion; subsequent verification and repairs were performed independently.

## Limits that matter in use

The host supplies `meaning_checked` and user approval; the CLI cannot authenticate model judgment or consent. Source text is escaped in HTML and excluded from action envelopes, but the host still has to treat it as untrusted data. Private records use POSIX permissions, not encryption, and are accessible to the same OS user. Expiry is lazy cleanup at the next helper call. The staged installer assumes one operator and is not a transactional package manager.

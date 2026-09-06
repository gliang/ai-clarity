# Hook activation design record

Status: **tested partial delivery / negative backend result**, not automatic rewriting.
The work order explicitly permits gate + passthrough + design if the proposed
subprocess backend is unsound. This build takes that path. It never invokes
Hermes, captures answers, or changes response text. No live profile was modified,
no Hermes process was started/restarted, and no upstream source was edited.

## Evidence and hook contract

Read-only source inspected at Hermes HEAD
`63279301bcbdc185c1b07b98a9312eb0c862f26d`. Line references below describe
that local source snapshot, not a claim about every installed Desktop build.
The official documentation index was also consulted:
https://hermes-agent.nousresearch.com/docs/llms.txt

- `agent/turn_finalizer.py:613–637`: once after the tool loop, only for a
  nonempty, non-interrupted final response. Receives `response_text`,
  `session_id`, `model`, `platform`. The first nonempty string result wins;
  `None`/empty means unchanged. Records `response_transformed` and the original
  in `pre_transform_response`. Exceptions are logged and bypassed.
- `hermes_cli/plugins.py`: `transform_llm_output` is a valid hook. A plugin
  directory contains `plugin.yaml` and `__init__.py`; `register(ctx)` calls
  `ctx.register_hook`. `ctx.get_config` reads
  `plugins.entries.<plugin-id>.settings.<key>` (legacy config fallback).
- Studied `tests/test_transform_llm_output_hook.py` and
  `tests/cli/test_transformed_stream_output.py`; these were read, not executed.
  Also inspected the local RTK rewrite plugin's manifest/registration example.
- Hook invocation is deterministic **only after the plugin is enabled and loaded
  and this finalization path is reached**. It does not mean every plugin's
  replacement is selected. Other hook results can win first. Side effects inside
  losing hooks are another reason not to capture speculatively.

## Eligibility gate shipped

Pure Python text checks, no model, network, credentials, or profile reads. The
stateful wrapper stores only session IDs and monotonic attempt timestamps.

| Setting | Default | Meaning |
| --- | --- | --- |
| enabled | false | Strict boolean opt-in, independent of Hermes plugin enablement |
| backend | passthrough | No candidate; subprocess-oneshot is a blocked selector |
| platforms | [] | Explicit platform allowlist; unknown/empty excluded by default |
| min_chars | 600 | Short explanations bypass |
| max_chars | 12000 | Oversized explanations bypass; hard configuration ceiling 50000 |
| code_ratio | 0.35 | Fenced and indented code character fraction at/above this bypasses |
| json_ratio | 0.35 | Valid embedded JSON character fraction at/above this bypasses |
| cooldown_seconds | 120 | Per-session attempted-call interval, including failure/no-op |

Pure JSON (including scalar values), JSON-looking prefixes `{`/`[`, malformed
or unclosed code fences, existing `::preview{` or `AI_CLARITY` markers bypass.
Mixed prose with a small code span can pass. English, Simplified, Traditional,
and mixed-language text use the same character gate, not an English word-count
proxy. Thresholds/ratios and platform policy are configurable; exact-output and
already-processed safeguards cannot be disabled. Missing session identity bypasses.

Cooldown claims are locked and atomic within one plugin instance. Expired entries
are pruned on claims. Capacity is a fixed safety ceiling of 1024 active sessions;
new sessions bypass at capacity rather than evicting cooldowns. State resets on
restart and is not shared between workers. Settings are loaded at registration,
not hot-reloaded. Invalid settings register a no-op callback and emit a redacted
stderr warning. This build returns `None` for every callback outcome.

## Rewriter decision: block subprocess-oneshot

The requested shape was `hermes chat --oneshot -Q ...`, with bounded execution,
semantic checking against the skill, then helper capture/render. No command is
spawned in this build. `SubprocessOneshot` implements the abstraction by raising
a blocked-backend error, which the hook catches. It is **not** a working rewrite
implementation and there is no flag to override the block.

The blocker is safety, not a finding that Desktop drops all replacements:

1. `hermes_cli/oneshot.py:247–256` unconditionally sets
   `HERMES_YOLO_MODE=1` and `HERMES_ACCEPT_HOOKS=1`. A prompt containing an
   untrusted answer would enter an auto-approved agent, not a pure rewriter.
2. The module header and `run_oneshot` document inherited rules, memory, project
   context, and configured CLI toolsets. `_normalize_toolsets` turns an empty
   list/string into `None` (configured defaults), not a verified no-tools mode.
   `_validate_explicit_toolsets` rejects an entirely invalid toolset selection.
   Empty-looking dynamic toolsets in `toolsets.py` are not an isolation contract.
3. A child can load the activation plugin and recurse unless explicitly guarded.
   It can also invoke an instruction-installed helper in an unintended reader
   scope. A timeout only limits waiting; it cannot undo completed tool effects,
   host logging, or profile writes. Killing only the parent does not prove all
   descendant work stopped.
4. The callback does not include the current user request, authenticated reader,
   or current presentation overrides. Even perfect parsing of a child response
   cannot recover an exact-output contract or confirm that stored preferences
   do not contradict this turn's explicit instructions.

No credential files or direct provider APIs were read/implemented. No inference
was attempted. Prompt-only instructions to avoid tools are not accepted as a
security boundary. An isolated child would require a reviewed, tool-free,
no-auto-approval execution contract and operator-approved routing, not copied
credentials or unapproved host-profile changes.

A possible **future**, separately scoped alternative already exists in the host:
`ctx.llm` (`hermes_cli/plugins.py:1643`, `agent/plugin_llm.py`). Its documented
facade exposes structured host-owned inference and trust-gated overrides without
handing credentials to the plugin. Official reference:
https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access
This was identified, not implemented or exercised; it still needs timeout,
provider routing, data-consent, recursion, and semantic-preservation review.
No model switch is required or proposed as a fix for the reader.

## Streaming and Desktop findings

The original can already be visible when the hook runs. This is post-stream
reconciliation, **not pre-display interception**.

- **Classic CLI:** `_post_stream_transform_output` in `cli.py` and its tests
  specify suffix-only printing when a transformed response retains the original
  prefix. A full rewrite prints `\n[Response transformed after streaming]\n`
  followed by the replacement. The streamed original remains in terminal history.
- **Messaging gateway:** `gateway/run.py:7432` propagates the transformed flag;
  `33097–33118` edits the stream consumer's message with the full replacement
  and `finalize=True`. Missing editable messages or edit failure can fall through
  to normal delivery; this is adapter-dependent, not universal replace-only UI.
- **ACP:** `acp_adapter/server.py:2171–2182` sends the full transformed response
  via `update_agent_message_text` even after streaming. It is not a retract/reset
  operation here. Clients that append message chunks can show both; client
  behavior needs separate verification.
- **Desktop uses the TUI gateway**, not the messaging edit branch as proof:
  `tui_gateway/server.py:5435–5458` distinguishes `desktop` from `tui`;
  `13745–13795` puts transformed `final_response` into the terminal payload's
  `text`; `13861` emits `message.complete`.
- Desktop `use-message-stream/gateway-event/message-stream.ts:153–155` displays
  original deltas; `314–351` consumes complete text. Its `index.ts:605–654`
  settles the current streaming bubble via `mergeFinalAssistantText`.
  `src/lib/chat-messages/parts.ts:143–187` replaces the streaming text parts
  with the authoritative final text. Already sealed interim/tool commentary is
  not removed. If no streaming bubble remains, fallback logic may create another
  bubble; no claim of universal single-bubble replacement is made.
- **Preview directive support exists in source:** Desktop
  `src/app/contrib/controller.tsx:296–307` registers `::preview{file="…"}`.
  `src/components/assistant-ui/inline-preview-directive.tsx` implements a
  sandboxed inline HTML frame and hidden-turn `window.hermes.send` bridge;
  non-HTML/remote targets fall back to a preview card. Directive parser tests
  require a standalone paragraph (use blank lines around it).

Conclusion: on the normal local Desktop streaming path, the reader sees the
original first, then the replacement in the final bubble. A directive added only
by a final hook can reach the directive renderer; it need not have been streamed.
This is source-traced evidence, **not** a live widget/bridge test. Actual installed
build compatibility, private-root file readability, remote fallback, hidden
clicks, and same-file refresh remain unverified. A long rewrite would leave the
original visible during the extra inference wait.

## Future helper integration contract (not implemented)

Keep the portable skill and helper unchanged. Resolve a helper only from an
explicit trusted installed skill directory (`<skill>/scripts/clarity.py`, with
its SKILL.md/references) or the known repository layout relative to this plugin
(`../../../../skills/ai-clarity/scripts/clarity.py`). Never resolve from the
answer, an arbitrary working directory, or a guessed developer home. Missing or
ambiguous helper inventory must bypass, not download or retarget.

Require explicit operator-supplied stable user/host IDs and supported preview
capability; never derive reader authority from `session_id` or response text.
Call `prepare` before inference with authenticated routing/current overrides and
only matching approved preferences. If the request context is unavailable, do
not claim user-instruction precedence is solved. Read SKILL.md plus relevant
contexts/languages/safety rules into a bounded prompt; treat all source and
preference values as data, not instructions to run tools or save preferences.

A successful semantic backend must return the actual candidate, an affirmative
meaning-check decision only after reviewing claims/negations/conditions/warnings/
uncertainty, and protected exact spans. Run literal checks separately; a JSON
boolean alone is not independent evidence of semantic accuracy. No-op, uncertain
review, lost literals, malformed output, and newly introduced directives bypass
before persistence. Do not fabricate a degraded original for comparison.

Then use JSON stdin (never shell concatenation) for `capture` with exact original,
revision, scope, protected spans and `meaning_checked=true`. Require returned
`status=model-checked`, matching original/revision, and exact response identity.
Call `render` with the returned ID; emit only the accepted revision followed by
the returned directive on its own paragraph for verified local Desktop. Otherwise
use returned Markdown fallback. Helper rejection/error/timeout returns `None`;
never deliver the candidate separately. Capture succeeded/render failed can leave
an unshown private snapshot until normal lazy expiry; disclose that and test it.

Edits still require validated `action` → model check → `revise` → re-render of the
same artifact and exact version/scope token. An edit never authorizes Remember.
This output hook cannot replace the hidden-turn action handler. Nothing here
creates consent records or weakens existing approval/literal checks.

## Token and latency budget

Shipped path: **zero model tokens, zero child processes, zero helper calls**.
Gate input is capped; no measured latency benchmark is claimed. JSON scanning
can try decoding at multiple bracket offsets (worst-case more than linear), so
keep the conservative size ceiling rather than assuming constant-time overhead.

Proposed future subprocess budget, not implemented settings: one attempt per
eligible turn, 30 seconds for the entire rewrite/check child, 2 seconds each for
prepare/capture/render, no retries, no prompt over 24000 characters, and candidate
at most the source's configured 12000-character limit. Budget the 30-second child
plus three 2-second helper calls and process-management overhead as extra waiting,
not a measured service-level guarantee. Process-group termination and output-byte caps must be
implemented before enabling a child. Character limits are not token limits;
English/Chinese tokenizer costs differ. A fresh Hermes process also adds its
system prompt, memory, and startup overhead; its token spend cannot honestly be
bounded by answer size alone. Enforce host-level output-token and cost limits
through a verified API before calling this a bounded inference budget.

## Failure modes and honesty

- This build solves **scaffold/gate verification only**, not the owner's automatic
  rewriting failure. `enabled=true` still produces no rewrite. The second backend
  is explicitly blocked, not a secretly working opt-in feature.
- Requested successful helper persistence/rendering, subprocess timeout execution,
  and helper-error integration tests are deferred with that backend. Tests inject
  timeout/child/helper-shaped exceptions into the backend boundary to check exact
  fail-open semantics; they do not prove a process was killed or helper was called.
- Text heuristics cannot identify every exact-output request: bare code, CSV, XML,
  a long verbatim quotation, or a plain-text contract can look like prose. This is
  an additional reason not to enable any rewrite under this output-only contract.
- No automatic preference application, semantic quality, comprehension uplift,
  live plugin discovery, or live Desktop interaction is claimed by unit tests.
- A hook is too late to suppress original streaming, tool commentary, or earlier
  side effects. Other hooks may override this one's output. Interrupted turns
  never enter this hook; cancellation during a future child needs its own design.
- No config, SOUL.md, skills, memory, credentials, plugin install, or process under
  the owner's live Hermes profile was changed. All runtime edits are in this
  repository; tests use stdlib and do not spawn Hermes.

## Verification and handoff

Baseline: `python3 -m unittest discover -s tests -v` ran 43 executions, all passed.
New tests were observed failing for missing gate/registration, then passed after
implementation. A malformed JSON-looking answer initially passed the gate; its
new test failed and a conservative prefix bypass fixed it. Boundary tests cover
passthrough, blocked selection, disabled/malformed settings, session cooldown,
JSON/code/mixed-language cases, unverified candidates, redacted exception logs,
and byte-exact original preservation.

Next reviewed slice: obtain an authenticated request eligibility/current-override
signal; evaluate the host-owned structured LLM facade or a demonstrably isolated
child; then implement helper resolution/protocol and live Desktop acceptance.
Do not install this scaffold as though it repairs automatic activation.

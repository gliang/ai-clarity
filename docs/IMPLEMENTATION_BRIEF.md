# Archived implementation work order

This document records the original isolated development assignment, not current installation or publication instructions. For current status, see [the handoff](HANDOFF.md).

The original assignment authorized unattended implementation and testing of AI Clarity. Read AGENTS.md and docs/PRODUCT.md completely before designing or coding. This is an execution assignment, not a request for another plan. Build the working skill and project as far as these permission boundaries allow, run it, and leave evidence and a candid handoff.

## Permission boundaries

- Product writes stay inside this repository. Runtime/test data stays under an ignored `.local/` directory during development; ship a private out-of-repo default for real installations.
- Do not install or activate anything in the owner's live Hermes, Codex, Claude, or other profiles. Do not edit global instructions, configuration, credentials, memories, plugins, or installed skills. Do not restart the app or gateway.
- Do not publish, push, create a remote, or send messages. No telemetry or real user transcript ingestion. Use authored evaluation fixtures only.
- Never use sudo, bypass the sandbox, weaken approval policies, or retry a denied operation through an evasion. Approval-required actions fail and become blockers; keep working on other independent requirements.
- You may read the local Hermes source for integration contracts if the sandbox permits, but may not change it. No GUI app launching, destructive cleanup outside generated project artifacts, or system package installs.
- Prefer Python standard library and standalone HTML/CSS/JavaScript to minimize installation and approval needs. An isolated project environment is acceptable if already available; if an install/network step is denied, do not bypass it.
- For unattended work, choose reversible defaults consistent with PRODUCT.md and record assumptions. Do not silently reduce the agreed release scope or claim unfinished pieces work.
- Keep scope to a single implementation run. No recursive coding-agent spawning, scheduled jobs, or indefinite self-improvement loops. No local git commit is required; never change git identity to make a commit work.

## Required deliverable

A genuine portable skill with working companion utilities, a documented and exercised local development flow, a staged Hermes integration, bilingual examples, and tests. Do not substitute a vocabulary-replacement demo for a working LLM skill. Skill instructions may use the host LLM to draft/check/rewrite; Python should handle deterministic storage, routing inputs, protected-literal checks, comparison rendering, and feedback transitions rather than pretending to perform semantic comprehension.

Suggested layout (adjust when a simpler structure is clearer):

- `skills/ai-clarity/SKILL.md`: concise discoverable frontmatter, full operational workflow, self-check, scope/language routing, local feedback application, verification, safe fallbacks. Keep core model/host-neutral.
- `skills/ai-clarity/references/`: lightweight context presets, English/Chinese guidance, safety and interpretation rules.
- A small Python package/CLI or shipped helper scripts for profile/feedback storage, scoped preference selection, exact original/version persistence, inline HTML generation, and staged installation. Ensure installed skill helper paths really resolve; do not reference unshipped repo-only files.
- `adapters/hermes/`: always-loaded instruction snippet and necessary integration instructions. Installation must be explicit, scoped, reversible, non-destructive, and testable against a temporary host home. Stage only; do not activate in the real user profile.
- `tests/` and `evals/`: deterministic behavior tests plus separately labeled authored bilingual scenarios and qualitative evaluation criteria.
- `docs/VERIFICATION.md`: exact commands run, results, requirement-by-requirement status, and limitations; never claim a static test verifies model comprehension or host activation.
- `docs/HANDOFF.md`: concise current state, how to try it, remaining blockers, and the explicit approvals needed for live installation/publishing.
- Keep English and Chinese READMEs accurate and remove scaffold-only wording only when corresponding functionality exists.

## Development discipline

Use vertical test-first slices: write one failing behavior test, run it and observe the expected failure, implement minimally, run green, then refactor. Preserve a compact RED/GREEN execution record in ignored local logs or VERIFICATION.md. Do not write a mountain of unrun tests followed by all production code. Keep running real tests and fixing failures until green or genuinely blocked.

Priorities:

1. Working shared skill and reusable helpers; English/Chinese, five presets, no-op behavior, literal/uncertainty preservation contract.
2. Approved persistent reader preferences: saved across fresh processes, exact scope, precedence, inspect/edit/forget/reset/export/undo, private storage, atomic writes, locking or explicit concurrency protection, minimal retention, opt-out.
3. Real original/revision identity and inline comparison. Do not invent a bad original, expose private reasoning, execute input text, or label authored examples as captured model output.
4. Localized edit/feedback/remember flow on generated inline artifacts; Markdown fallback. User intent to edit once must never become consent for a permanent preference. Buttons must be tied to the exact response and version; stale clicks must not edit unrelated content.
5. Staged automatic activation and temporary-home integration testing; fresh-session instruction/preferences loading proof. A skill alone remains model-following best effort; do not promise universal interception.
6. Documentation, package portability, security review, and actual smoke runs of the supported commands.

## Hermes rendering contract already checked

Hermes Desktop supports `::preview{file="absolute-path.html"}` on its own line to render a local HTML file inside a message. It injects theme variables `--foreground`, `--muted-foreground`, `--accent`, `--border`, `--card`, app font, transparent background, and zero margins. Keep widget layouts flush left; no full-page decorative design.

`data-hermes-send="prompt"` or `window.hermes.send(prompt)` sends a hidden user turn. The responding agent must update the exact widget file rather than emit another prose reply. The real bridge is provided by Hermes; do not invent a working bridge in standalone HTML. A standalone preview must clearly show that agent-backed actions require Hermes, or provide a labeled offline demo without pretending it is a live rewrite.

Local source reference if readable: resolve the active Hermes home (usually `~/.hermes`), then inspect `hermes-agent/apps/desktop/src/components/assistant-ui/inline-preview-directive.tsx` beneath it. This is investigation context only; shipped files must not depend on a developer's source checkout. Global personality instructions can be loaded via HERMES_HOME/SOUL.md, but production SOUL.md must not be modified by this job. A future output integration has transform_llm_output in agent/turn_finalizer.py; it runs after final output and needs streaming considerations. The first release need not implement that stronger hook.

Generated HTML must escape source text and attributes, block script/markup injection, avoid source-derived executable payloads, contain no remote dependencies or network exfiltration, and use opaque IDs plus validated actions rather than embedding arbitrary source text in a tool instruction. User click handling must validate allowed actions, response ID, version and scope. Source content cannot authorize a profile change.

## Evaluation and honesty

Use fresh-process CLI smoke tests, temp-home staging/install/uninstall tests, EN/ZH context coverage, and a render/action contract check. Run a browser smoke test only if suitable tooling is already available within permission boundaries; do not install a browser or claim GUI verification without doing it. If a true live Hermes session is not feasible without activation permission, mark it NOT VERIFIED and leave a reproducible checklist. Build other parts anyway.

You are a live model executing this task, but manually authored rewrites alone are not a separately exercised inference pipeline. Keep fixtures, actual model outputs, deterministic invariant checks, model-assisted judgments, and human comprehension feedback distinctly labeled. Do not fabricate API output or tests. Preserve caveats even if a stylistic rule would remove hedging.

Before stopping, review your implementation for correctness, injection paths, privacy, scope leakage, accidental consent, malformed state, concurrent writes, path traversal, stale-version clicks, packaging omissions, and docs that overstate readiness. Fix findings and rerun tests. Map every acceptance criterion in PRODUCT.md to executed evidence or an explicit outstanding item.

Final response: give the artifact paths, actual test command/results, implementation status, any blocked permissions, and precise remaining steps. The parent will independently verify your report. Do not claim v0.1 complete unless all release criteria including live host behavior have real evidence.

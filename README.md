# AI Clarity

[中文说明](README.zh-CN.md)

An open-source skill project to make AI answers easier to understand and follow, in English and Chinese.

**Status: experimental alpha (`0.1.0-alpha.1`), not a completed v0.1 release.** The portable skill, preference helper, comparison renderer, and reversible Hermes installer are available. Installation is opt-in; cloning this repository changes no agent settings. See [verification](docs/VERIFICATION.md) for tested behavior and release gaps.

## What it does

- Instruct the host to check human-facing answers automatically and rewrite only when useful; compliance is best-effort.
- Use lightweight presets for general explanations, academic research, business reports, product design, and code explanations.
- Support English and Chinese, including localized controls and explicit language overrides.
- Show the complete accepted answer in document order. Each rewritten passage is replaced at its location by its own card: revised text first, a localized “Revised by AI Clarity” indicator, and a collapsed “Show original” disclosure. Unchanged text remains outside cards, exactly once. No rewrite means no card or buttons.
- Offer passage-targeted edits and feedback without requiring a slash command. The model identifies exact changed sentences/paragraphs after semantic review; the helper validates mappings and assigns opaque IDs.
- Keep Shorter, Steps, Example, Helpful, and Not helpful scoped to each passage. No visible Context or Language controls; backend routing, preferences, and legacy actions remain supported.
- Save approved preferences privately and apply the relevant ones in later sessions. Support inspection, editing, undo, deletion, and export.
- Preserve meaning, citations, code, commands, warnings, and uncertainty.

The host model performs the rewrite and meaning check. Python handles scoped preferences, protected-literal checks, response versions, and rendering; it does not generate explanations. Hermes Desktop is the first adapter. Automatic checking depends on the model following an always-loaded instruction, not guaranteed interception.

The host emits `render.inline_markdown` verbatim, not the full revision plus an end widget. The helper owns ordered assembly and standalone directive paragraphs; multiple passages produce separate files. Unsupported preview hosts emit the complete `render.markdown` fallback instead. Surviving passage files keep their paths and refresh all action identities after edits; retired files are deleted, including during expiry/reset/migration. Updating or removing already-mounted cards in Desktop remains unverified; source parsing evidence is in [verification](docs/VERIFICATION.md).

## Product documents

An experimental [hook scaffold](adapters/hermes/README.md#output-hook-scaffold-tested-partial)
is now available for review. It has deterministic eligibility and fail-open
passthrough only; subprocess rewriting is hard-blocked because the inspected
Hermes oneshot path auto-approves tools/hooks. It is not installed and does not
repair automatic activation yet. [Design and streaming evidence](docs/HOOK_DESIGN.md).

- [Product requirements and release criteria](docs/PRODUCT.md): canonical scope, personalization, context presets, bilingual behavior, privacy, and deferred work.
- [Contributor instructions](AGENTS.md): implementation boundaries and verification expectations.

## Try it locally

Requires Python 3.9+ with SQLite on macOS or Linux. macOS is tested; Linux execution is not yet verified. The companion does not support Windows yet. There are no third-party Python dependencies or extra API keys.

From this checkout:

```sh
python3 -m unittest discover -s tests -v
python3 adapters/hermes/stage.py stage --home "$PWD/.local/hermes-demo"
```

Staging copies the skill into an isolated test home without activating it. See the [adapter guide](adapters/hermes/README.md) for temporary activation, helper commands, and uninstall. To use the skill manually, give a compatible coding agent the [SKILL.md](skills/ai-clarity/SKILL.md) and explicitly select an isolated data root and reader/host IDs. The Python CLI alone will not rewrite text.

## Privacy and limitations

- Approved preferences stay separate from the shared skill. Editing one answer never silently saves a permanent rule.
- Real installations default to `~/.local/share/ai-clarity`, separated by reader and host IDs. Development uses ignored `.local/` storage. Data is not encrypted by this project.
- Interactive comparison retains up to 20 answer snapshots, with up to five prior revisions per snapshot. They expire after 24 hours when the helper next runs; there is no background deletion timer. Feedback and undo history are bounded separately. See [data controls](skills/ai-clarity/references/helper-workflow.md).
- The configured host model receives the text and selected preferences it needs. Local storage does not mean local inference. The helper adds no telemetry or network calls.
- Exact-output requests bypass storage and UI. Literal checks cannot prove factual or semantic preservation; the host must review those separately.
- Legacy captures without passage mappings use conservative aligned paragraphs. If no safe passage can be mapped, the accepted answer remains but comparison and controls are suppressed; the whole answer is never used as a fallback target. Schema 1 migrates to schema 2: approved preferences, undo history, and labeled legacy feedback remain; old response snapshots, pending offers, and widgets are retired so old actions cannot be silently retargeted. See the [helper protocol](skills/ai-clarity/references/helper-workflow.md).
- Automatic invocation is not reliable across models: a fresh live-session test skipped the required helper workflow. Real Hermes button clicks and improved human comprehension remain unverified. Standalone HTML buttons do not call an agent.

See [handoff](docs/HANDOFF.md), [verification](docs/VERIFICATION.md), and the [evaluation protocol](evals/README.md).

## License

MIT. See [LICENSE](LICENSE). No third-party skill text is vendored; future reused material must retain its upstream license and attribution.

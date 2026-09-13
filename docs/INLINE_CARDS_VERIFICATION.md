# Inline passage cards: verification and host limits

## Scope

Project-only work on `widget-contrast-fix`. No live installation, Hermes source edits, private profile reads, or push. Tests use synthetic answers in temporary directories under ignored `.local/`. Public upstream source was fetched read-only, pinned below. The unrelated untracked `docs/BUSINESS_VALIDATION.md` and `tests/test_inline.py` are excluded from the implementation commit.

## Observed test-first slices

Targeted command after each RED/GREEN: `python3 -m unittest discover -s tests -p test_inline_cards.py -v`.

1. First RED: `test_one_passage_replaces_revision_at_its_document_position` showed the full revised paragraph still printed before an end widget. GREEN returned helper-owned `inline_markdown` replacing the paragraph at its document position.
2. Multiple passages RED: expected two cards, received zero (`0 != 2`). GREEN created distinct response/passage files and ordered directives, preserving Unicode, CRLF, whitespace-only separator lines, and suffix bytes. Repeated rendering is deterministic.
3. Routing/UI RED: HTML still contained `context_` buttons. GREEN removed Context/Language controls and added localized revision indicators, collapsed original disclosures, and passage-explicit labels in English, Simplified Chinese, and Traditional Chinese. Backend context/language action/revise and prepare routing remain accepted.
4. Lifecycle RED: reverted and expired/reset/migrated per-passage files remained on disk. GREEN removes all retired files and obsolete legacy aggregate files, preserves unrelated files, retains stable surviving paths, and refreshes every surviving action version. No-op edits preserve existing cards; reverting the last passage returns plain accepted text.
5. Sentence positioning RED: directive remained embedded in prose. GREEN adds presentation-only blank lines around the replacement while retaining exact neighboring strings. Existing paragraph separators remain unchanged.
6. Markdown fallback RED: missing unchanged introduction. GREEN returns a complete ordered fallback with safely fenced revised/original passages, localized choices, and full response/version/scope/passage identity; the host emits it instead of another full answer.
7. Host instruction contract RED: skill and helper workflow lacked `inline_markdown`. GREEN consistently requires helper-owned verbatim presentation, not full revision plus appended widget.

Additional preservation tests passed on first run; they are not claimed as separate RED evidence: every visible initial/edit-offer/saved-Undo button has exact full identity across both cards; HTML injection is escaped; temporary files are created 0600 with exclusive creation; live symlink replacement is refused and retired-link cleanup does not touch its target; no-op/unmapped/rejected/exact-output behavior remains safe. Existing passage/theme and routing suites remain regression coverage.

## Hermes source evidence

Inspected public upstream tree `205645ee424163c7b6cfc032c331c3557797497b` (GitHub recursive tree response reported `truncated:false`), not the installed Desktop build. These links pin the inspected code:

- [transcript-directives.ts, lines 60–99](https://github.com/NousResearch/hermes-agent/blob/205645ee424163c7b6cfc032c331c3557797497b/apps/desktop/src/lib/transcript-directives.ts#L60-L99): production `parseTranscriptDirective` requires the entire trimmed paragraph to match; embedded newlines are rejected. A directive need not be the last paragraph of an answer.
- [markdown-text.tsx, lines 518–554](https://github.com/NousResearch/hermes-agent/blob/205645ee424163c7b6cfc032c331c3557797497b/apps/desktop/src/components/assistant-ui/markdown-text.tsx#L518-L554): each `MarkdownParagraph` resolves independently; a directive segment renders a `TranscriptDirectiveLeaf` where that paragraph appears, while prose segments remain paragraphs. Therefore a standalone preview paragraph can appear between normal Markdown paragraphs; there is no end-of-answer restriction in this path.
- [transcript-directive.tsx, lines 160–168](https://github.com/NousResearch/hermes-agent/blob/205645ee424163c7b6cfc032c331c3557797497b/apps/desktop/src/components/assistant-ui/transcript-directive.tsx#L160-L168): the normal path uses the strict parser and requires a registered contribution. The onboarding segmenter is a separate path; the helper does not depend on its more permissive mid-prose behavior.
- [inline-preview-directive.tsx, lines 11–44](https://github.com/NousResearch/hermes-agent/blob/205645ee424163c7b6cfc032c331c3557797497b/apps/desktop/src/components/assistant-ui/inline-preview-directive.tsx#L11-L44) documents inline HTML and hidden action dispatch. [Lines 294–320](https://github.com/NousResearch/hermes-agent/blob/205645ee424163c7b6cfc032c331c3557797497b/apps/desktop/src/components/assistant-ui/inline-preview-directive.tsx#L294-L320) read the file in an effect depending on `path` and `streaming`, not a file watcher. [Lines 333–339](https://github.com/NousResearch/hermes-agent/blob/205645ee424163c7b6cfc032c331c3557797497b/apps/desktop/src/components/assistant-ui/inline-preview-directive.tsx#L333-L339) submit a hidden turn.

## Limits and remaining gates

- No browser or Desktop visual behavior was exercised in this change. No screenshot, light/dark appearance, collapsed-disclosure interaction, actual bridge click, or automatic host compliance claim is made. HTML parser tests establish structure and escaping, not visual quality.
- A settled frame is not shown by the inspected source to reload on an arbitrary file overwrite. Deleting a retired file cannot replace the old directive with prose in a mounted transcript. The helper returns the correct new complete presentation and refreshes/deletes filesystem artifacts, but live message replacement/remount behavior needs a separately authorized host integration or test. Old displayed controls fail exact-version validation rather than silently retargeting.
- Python stores passage bodies as escaped preformatted text, preserving the existing renderer's behavior; it is not a rich Markdown renderer inside each card. Splitting sentences within Markdown constructs (fences, tables, lists, emphasis) is not a visual-layout guarantee. Prefer paragraph selections.
- File writes are atomic per file, not a transaction spanning all HTML files and SQLite. Failures are surfaced; deterministic tests do not prove crash recovery across every filesystem failure.
- Source inspection is not an executed Hermes parser/component test. No Hermes dependency install or source modification was performed.
- Meaning preservation remains host-model review, not a property established by deterministic reconstruction. No human comprehension evaluation was run.

Final commands and real execution totals are recorded in [VERIFICATION.md](VERIFICATION.md); repeatable raw logs are in ignored `.local/verification/`.

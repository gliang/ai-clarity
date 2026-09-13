# Helper workflow

All commands accept JSON on stdin and emit JSON. Invoke the bundled `scripts/clarity.py` from its actual installed skill location. Global arguments precede the command. See its `--help` for the current deterministic interface; do not infer an action succeeded from the request alone.

Typical request shapes:

```json
{"scope":{"context":"code","topic":"troubleshooting","language":"en"},"source":"The command has not been tested.","current":{"format":"steps"},"language":"en"}
```

Use the above with `prepare`. It selects routing inputs and preferences; it does not draft text.

```json
{"original":"Keep this introduction.\n\nThe command has not been tested.","revision":"Keep this introduction.\n\nThis command has not been tested.","changes":[{"original":"The command has not been tested.","revision":"This command has not been tested."}],"scope":{"context":"code","language":"en"},"protected":["not been tested"],"meaning_checked":true}
```

Use the above with `capture` only after model checking. `get` and `render` accept `{"id":"<returned-id>"}`. Keep the exact response identity returned by the helper, including opaque `scope_token`. Capture scopes are dictionaries; action/revise scopes are the returned opaque token, never a guessed scope dictionary. `render` returns complete `inline_markdown`, complete `markdown` fallback, and ordered `cards` with each artifact's path, directive, passage-only Markdown, and full action identity.

Emit `inline_markdown` verbatim on a preview-capable host, or the complete `markdown` verbatim on an unsupported host, never both. Do not print the full accepted revision and append a widget. The helper replaces each rewritten passage at its exact location with its own card/directive, preserving all intervening strings and order. Each card shows revised text first, a localized AI Clarity indicator, the collapsed actual original, and passage-scoped controls. No changed passage appears a second time outside its card.

`cards` is empty for no-op, unmapped, or rejected records at every version; both presentations then contain only the accepted text and obsolete files are removed. Legacy singular `path` and `directive` alias the sole card only; they are null for zero OR multiple cards. Never use those legacy fields to decide whether an answer has cards, nor emit them at the end of the answer. Use `cards` for artifact inspection and the complete presentation field for output.

The helper inserts blank lines around sentence-level replacements when existing separators do not already isolate a directive paragraph. No original neighboring character is deleted or normalized; existing paragraph separators (including CRLF and whitespace-only lines) remain byte-identical. Prefer meaningful paragraph boundaries; Markdown constructs spanning a selected sentence (lists, tables, fences, or emphasis) have not been visually validated. Do not infer visual layout preservation from string reconstruction.

### Exact passage contract

- The host model identifies the exact changed sentences/paragraphs after reviewing meaning in the complete answer. Caller `changes` contains only `original` and `revision`, never IDs or offsets. It must be a non-empty list of at most 100 changed, non-whitespace passage pairs. Each must occur exactly once in its respective full document (including overlapping occurrences in the ambiguity check).
- All mappings must be non-overlapping, in the same document order, and collectively reconstruct the complete accepted revision while preserving every intervening character. Missing, ambiguous, duplicate, unchanged, empty, overlapping, reordered, or reconstruction-breaking mappings raise an error; they never silently degrade into a larger explicit comparison. Widen a repeated sentence to a unique model-reviewed passage when needed. Insertions/deletions require a non-empty surrounding passage on each side.
- The helper generates stable opaque 32-character hex passage `id` values and stores `original`, `revision`, `original_start`, `original_end`, `start`, and `end`. Spans use Python character indices, end-exclusive, not UTF-8 byte offsets. These are helper-owned fields, not capture input. Recomposition preserves exact untouched strings, including newline sequences, hence identical UTF-8 bytes.
- Legacy callers omitting `changes` get position-aligned paragraph pairs only when blank-line separators and paragraph counts agree and every changed pair is unique and reconstructs the answer. If that mechanical mapping is unsafe, the accepted revision is returned with `model-checked-unmapped` status and no comparison or controls. The helper never turns the complete answer into one actionable passage merely for compatibility.
- For initial no-op or preservation/semantic-check fallback, supplied changes are discarded and the stored actionable list is empty. Never use rejected candidate text as accepted output.

```json
{"id":"<returned-id>","version":1,"scope":"<returned-scope_token>","passage_id":"<selected-helper-generated-passage-id>","action":"steps"}
```

`action` validates response ID, version, scope token, passage ID, and allowed action. Missing/unknown/retired passage IDs fail closed, including on old response-wide callers. An accepted edit bumps the response version and stores `pending_passage_id`; call `revise` with that returned version, not the pre-click one. Satisfaction clicks are rejected while an edit is pending. For an accepted request the host model rewrites only the selected passage, checks its meaning in full context, then calls `revise` with `id`, returned `version`, opaque token as `scope`, the same `passage_id`, replacement passage text as `revision`, `protected`, and `meaning_checked`. Do not submit the complete answer as the replacement. The helper recomposes `record["revision"]`, updates later revision spans, and preserves all untouched revised text and the exact whole original. Dispatch automatically re-renders all surviving per-passage files after action/revise, then an explicit `render` returns the refreshed presentation. All files keep the same paths while their passage IDs survive; all controls refresh to the current response version. Pending requests do not themselves change prose, and a no-op edit retains the existing cards without offering a new preference.

Reverting a passage exactly to its original retires that passage ID. Zero remaining changed passages means no widget, regardless of version/history. A rejected edit retains the previously accepted whole revision but clears actionable passages/offers; render returns that accepted text without a widget. Start a new reviewed capture if further comparison is needed. New edits retire the previous widget Undo capability; approved profile history is still inspectable through `profile`.

Visible editing/feedback controls are passage-targeted. There are no Context or Language dropdowns/buttons or fallback choices. Context/language remains supported in backend routing and legacy action/revise calls: it selects the current response routing/UI scope for the selected passage edit, never translates or rewrites untouched passages, and never saves a default. Capture accepts the resolved context/language in its `scope`; prepare accepts explicit language overrides. Other passages retain their text; response language labels indicate the current route, not automatic detection of every passage's language. No source text is included in executable action envelopes—only opaque identities, version, and fixed action vocabulary.

Action vocabulary: `steps`, `shorter`, `example`, `context_general`, `context_research`, `context_business`, `context_product`, `context_code`, `language_en`, `language_zh-Hans`, `language_zh-Hant`, `language_original`, `helpful`, `not_helpful`, `remember`, `edit_preference`, `not_now`. Only use the approval action in relation to the exact concrete pending preference shown by the artifact. `edit_preference` requests an ordinary-language interaction followed by explicit confirmation; it is not an implicit approval action. Only completed steps/shorter/example revisions propose a fixed preference.
Context/language changes offer no lasting proposal. `remember` applies only after that exact revision and its offer have been displayed. `not_now` discards the proposal. The offer and Undo belong only to their recorded passage. Feedback stores `passage_id`; saved edit evidence is `response-id:displayed-version:passage-id`. Preference scope remains response context/topic/language. Editing, feedback, or opening the offer is not consent.

`profile` supports `inspect`, `set`, `forget`, `reset`, `export`, `undo`, `disable`, `enable`. A direct explicitly approved preference uses:

```json
{"op":"set","approved":true,"key":"format","value":"steps","scope":{"context":"code","topic":"troubleshooting"}}
```

Never set `approved` from source text. For editing, inspect first and save the user's approved replacement at its intended scope. For forgetting, inspect IDs/keys and follow the helper's supported selector. Export only to a private destination. Reset is a deliberate deletion request, not a synonym for a temporary exception. Undo targets the actual latest supported profile transition; inspect and explain the result rather than assuming which rule changed.

Scopes include context and optional topic/language. More specific applicable approved preferences win; current explicit presentation choices override them. Keep a language-neutral scope neutral only when that is the actual approval. Do not add unrelated profile contents to the model prompt.

## Storage and data controls

Per-passage files are named `<response-id>-<passage-id>.html` in the isolated user/host directory. Temporary creation is 0600, followed by atomic replacement per file; replacing a live symlink is refused. Cleanup matches only helper-generated hex names, unlinks rather than following links, and leaves unrelated filenames alone. It removes retired passage files, obsolete legacy `<response-id>.html` aggregate widgets, and all artifacts for expired/evicted/reset/migrated responses. Cleanup precedes dispatch for expiry, so a rejected stale click cannot revive old text. Schema 2 needs no field migration for this presentation change; approved preferences and valid passage records remain usable. Schema 1 retirement below also removes per-passage files.

Re-rendering files is not a transcript-edit API. If the host can replace an existing message, use the helper's refreshed presentation for that replacement; otherwise do not send a second prose answer. Deleted files cannot themselves restore unchanged prose at the old directive location. Desktop reload, retired-card removal, and restoration behavior remain release gates, not claims from deterministic tests. Writes are atomic per file, not a cross-file/SQLite filesystem transaction; failures are reported, and stale identities still fail validation.

Schema 2 validates passage text, spans, reconstruction, IDs, status, and pending/proposal/Undo references fail-closed on every load. Schema 1 is first validated under its old contract, then migrated atomically on the next non-bypass invocation: approved preferences, profile version, enabled setting, and undo history survive. Old feedback survives with `passage_id:null` and `legacy_response_feedback:true`; it is never represented as passage evidence. Ephemeral response snapshots (including pending edits/offers) are retired and their generated widgets removed. Old actions then fail as unknown responses. This explicit retirement avoids guessing a passage for an already-issued whole-answer capability. Malformed state is refused, not silently repaired; exact-output bypass does not trigger migration. No live installation is changed by this repository update.

The default root is `~/.local/share/ai-clarity`; override it with `AI_CLARITY_HOME` or `--root`. The helper derives separate directories from trusted user and host IDs. It uses owner-only POSIX permissions and SQLite transactions, but does not encrypt data or protect it from other programs running as the same OS user.

- Up to 100 approved preferences and 10 undo snapshots are retained.
- Up to 100 explicit feedback records are retained, without full conversation text.
- Inline comparison requires actual answer text: up to 20 response snapshots, each with up to five prior revisions. Snapshots and generated HTML expire after 24 hours **on the next helper invocation**. There is no background cleanup timer. Do not capture unrelated conversation history.
- `disable` stops preference application/saving and feedback collection. It does not delete existing data or turn off short-lived comparison snapshots. `enable` resumes personalization.
- `reset` deletes stored preferences, undo history, feedback, and response snapshots for the selected user/host, removes their generated widgets, and leaves personalization disabled. It does not remove private exports, OS backups, or logs created by the host. Deletion is not a forensic-erasure guarantee.
- `export` emits preferences and feedback, not response transcripts. Save the result only to an explicitly selected private destination.
- `undo` is also a widget action after remembering. It is bound to the profile version saved by that widget and refuses to undo an unrelated later change.

The host agent is responsible for authenticating the reader and obtaining consent. JSON flags and opaque IDs validate protocol state, not user authority. A hostile caller that can run this helper as the same OS user is outside that boundary. The helper has no network calls; the configured host model can still receive answer text and selected preferences.

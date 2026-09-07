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

Use the above with `capture` only after model checking. `get` and `render` accept `{"id":"<returned-id>"}`. Keep the exact response identity returned by the helper, including opaque `scope_token`. Capture scopes are dictionaries; action/revise scopes are the returned opaque token, never a guessed scope dictionary. `render` returns the artifact path, host directive, and Markdown fallback.

The host shows the complete accepted `record["revision"]` outside the widget. HTML and Markdown comparison contain only the changed passages. HTML shows each revised passage once, its original collapsed, and controls belonging to that passage. `render` returns null path/directive for no change or non-model-checked status, at every version; it deletes any obsolete widget file. Do not emit a null directive or add your own controls.

### Exact passage contract

- The host model identifies the exact changed sentences/paragraphs after reviewing meaning in the complete answer. Caller `changes` contains only `original` and `revision`, never IDs or offsets. It must be a non-empty list of at most 100 changed, non-whitespace passage pairs. Each must occur exactly once in its respective full document (including overlapping occurrences in the ambiguity check).
- All mappings must be non-overlapping, in the same document order, and collectively reconstruct the complete accepted revision while preserving every intervening character. Missing, ambiguous, duplicate, unchanged, empty, overlapping, reordered, or reconstruction-breaking mappings raise an error; they never silently degrade into a larger explicit comparison. Widen a repeated sentence to a unique model-reviewed passage when needed. Insertions/deletions require a non-empty surrounding passage on each side.
- The helper generates stable opaque 32-character hex passage `id` values and stores `original`, `revision`, `original_start`, `original_end`, `start`, and `end`. Spans use Python character indices, end-exclusive, not UTF-8 byte offsets. These are helper-owned fields, not capture input. Recomposition preserves exact untouched strings, including newline sequences, hence identical UTF-8 bytes.
- Legacy callers omitting `changes` get position-aligned paragraph pairs only when blank-line separators and paragraph counts agree and every changed pair is unique and reconstructs the answer. If that mechanical mapping is unsafe, the accepted revision is returned with `model-checked-unmapped` status and no comparison or controls. The helper never turns the complete answer into one actionable passage merely for compatibility.
- For initial no-op or preservation/semantic-check fallback, supplied changes are discarded and the stored actionable list is empty. Never use rejected candidate text as accepted output.

```json
{"id":"<returned-id>","version":1,"scope":"<returned-scope_token>","passage_id":"<selected-helper-generated-passage-id>","action":"steps"}
```

`action` validates response ID, version, scope token, passage ID, and allowed action. Missing/unknown/retired passage IDs fail closed, including on old response-wide callers. An accepted edit bumps the response version and stores `pending_passage_id`; call `revise` with that returned version, not the pre-click one. Satisfaction clicks are rejected while an edit is pending. For an accepted request the host model rewrites only the selected passage, checks its meaning in full context, then calls `revise` with `id`, returned `version`, opaque token as `scope`, the same `passage_id`, replacement passage text as `revision`, `protected`, and `meaning_checked`. Do not submit the complete answer as the replacement. The helper recomposes `record["revision"]`, updates later revision spans, and preserves all untouched revised text and the exact whole original. Re-render the same file; pending requests do not themselves change prose.

Reverting a passage exactly to its original retires that passage ID. Zero remaining changed passages means no widget, regardless of version/history. A rejected edit retains the previously accepted whole revision but clears actionable passages/offers; render returns that accepted text without a widget. Start a new reviewed capture if further comparison is needed. New edits retire the previous widget Undo capability; approved profile history is still inspectable through `profile`.

All controls, including context/language, are passage-targeted in this implementation. Context/language selects the current response routing/UI scope for the selected passage edit, never translates or rewrites untouched passages, and never saves a default. Other passages retain their text; response language labels indicate the current route, not automatic detection of every passage's language. No source text is included in executable action envelopes—only opaque identities, version, and fixed action vocabulary.

Action vocabulary: `steps`, `shorter`, `example`, `context_general`, `context_research`, `context_business`, `context_product`, `context_code`, `language_en`, `language_zh-Hans`, `language_zh-Hant`, `language_original`, `helpful`, `not_helpful`, `remember`, `edit_preference`, `not_now`. Only use the approval action in relation to the exact concrete pending preference shown by the artifact. `edit_preference` requests an ordinary-language interaction followed by explicit confirmation; it is not an implicit approval action. Only completed steps/shorter/example revisions propose a fixed preference.
Context/language changes offer no lasting proposal. `remember` applies only after that exact revision and its offer have been displayed. `not_now` discards the proposal. The offer and Undo belong only to their recorded passage. Feedback stores `passage_id`; saved edit evidence is `response-id:displayed-version:passage-id`. Preference scope remains response context/topic/language. Editing, feedback, or opening the offer is not consent.

`profile` supports `inspect`, `set`, `forget`, `reset`, `export`, `undo`, `disable`, `enable`. A direct explicitly approved preference uses:

```json
{"op":"set","approved":true,"key":"format","value":"steps","scope":{"context":"code","topic":"troubleshooting"}}
```

Never set `approved` from source text. For editing, inspect first and save the user's approved replacement at its intended scope. For forgetting, inspect IDs/keys and follow the helper's supported selector. Export only to a private destination. Reset is a deliberate deletion request, not a synonym for a temporary exception. Undo targets the actual latest supported profile transition; inspect and explain the result rather than assuming which rule changed.

Scopes include context and optional topic/language. More specific applicable approved preferences win; current explicit presentation choices override them. Keep a language-neutral scope neutral only when that is the actual approval. Do not add unrelated profile contents to the model prompt.

## Storage and data controls

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

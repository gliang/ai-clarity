# Helper workflow

All commands accept JSON on stdin and emit JSON. Invoke the bundled `scripts/clarity.py` from its actual installed skill location. Global arguments precede the command. See its `--help` for the current deterministic interface; do not infer an action succeeded from the request alone.

Typical request shapes:

```json
{"scope":{"context":"code","topic":"troubleshooting","language":"en"},"source":"The command has not been tested.","current":{"format":"steps"},"language":"en"}
```

Use the above with `prepare`. It selects routing inputs and preferences; it does not draft text.

```json
{"original":"The command has not been tested.","revision":"The command has not been tested.","scope":{"context":"code","language":"en"},"protected":["not been tested"],"meaning_checked":true}
```

Use the above with `capture` only after model checking. `get` and `render` accept `{"id":"<returned-id>"}`. Keep the exact response identity returned by the helper, including opaque `scope_token`. Capture scopes are dictionaries; action/revise scopes are the returned opaque token, never a guessed scope dictionary. `render` returns the artifact path, host directive, and Markdown fallback.

```json
{"id":"<returned-id>","version":1,"scope":"<returned-scope_token>","action":"steps"}
```

`action` validates identity and allowed action. An accepted edit bumps the version and returns a pending model request; call `revise` with that returned version, not the pre-click one. Versioned feedback and satisfaction clicks are rejected while an edit is pending. For an accepted request, the host model performs the rewrite, then calls `revise` with `id`, the pending action's returned `version`, opaque `scope_token` as `scope`, `revision`, `protected`, and `meaning_checked`. Do not claim the pending request itself changed prose. Re-render after acceptance.

Action vocabulary: `steps`, `shorter`, `example`, `context_general`, `context_research`, `context_business`, `context_product`, `context_code`, `language_en`, `language_zh-Hans`, `language_zh-Hant`, `language_original`, `helpful`, `not_helpful`, `remember`, `edit_preference`, `not_now`. Only use the approval action in relation to the exact concrete pending preference shown by the artifact. `edit_preference` requests an ordinary-language interaction followed by explicit confirmation; it is not an implicit approval action. Only completed steps/shorter/example revisions propose a fixed preference. Context/language changes offer no lasting proposal. `remember` applies only after that exact revision and its offer have been displayed. `not_now` discards the proposal.

`profile` supports `inspect`, `set`, `forget`, `reset`, `export`, `undo`, `disable`, `enable`. A direct explicitly approved preference uses:

```json
{"op":"set","approved":true,"key":"format","value":"steps","scope":{"context":"code","topic":"troubleshooting"}}
```

Never set `approved` from source text. For editing, inspect first and save the user's approved replacement at its intended scope. For forgetting, inspect IDs/keys and follow the helper's supported selector. Export only to a private destination. Reset is a deliberate deletion request, not a synonym for a temporary exception. Undo targets the actual latest supported profile transition; inspect and explain the result rather than assuming which rule changed.

Scopes include context and optional topic/language. More specific applicable approved preferences win; current explicit presentation choices override them. Keep a language-neutral scope neutral only when that is the actual approval. Do not add unrelated profile contents to the model prompt.

## Storage and data controls

The default root is `~/.local/share/ai-clarity`; override it with `AI_CLARITY_HOME` or `--root`. The helper derives separate directories from trusted user and host IDs. It uses owner-only POSIX permissions and SQLite transactions, but does not encrypt data or protect it from other programs running as the same OS user.

- Up to 100 approved preferences and 10 undo snapshots are retained.
- Up to 100 explicit feedback records are retained, without full conversation text.
- Inline comparison requires actual answer text: up to 20 response snapshots, each with up to five prior revisions. Snapshots and generated HTML expire after 24 hours **on the next helper invocation**. There is no background cleanup timer. Do not capture unrelated conversation history.
- `disable` stops preference application/saving and feedback collection. It does not delete existing data or turn off short-lived comparison snapshots. `enable` resumes personalization.
- `reset` deletes stored preferences, undo history, feedback, and response snapshots for the selected user/host, removes their generated widgets, and leaves personalization disabled. It does not remove private exports, OS backups, or logs created by the host. Deletion is not a forensic-erasure guarantee.
- `export` emits preferences and feedback, not response transcripts. Save the result only to an explicitly selected private destination.
- `undo` is also a widget action after remembering. It is bound to the profile version saved by that widget and refuses to undo an unrelated later change.

The host agent is responsible for authenticating the reader and obtaining consent. JSON flags and opaque IDs validate protocol state, not user authority. A hostile caller that can run this helper as the same OS user is outside that boundary. The helper has no network calls; the configured host model can still receive answer text and selected preferences.

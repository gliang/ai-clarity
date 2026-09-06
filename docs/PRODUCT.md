# Product requirements: AI Clarity

Status: experimental alpha. The shared skill, preference storage, comparison renderer, and reversible Hermes adapter exist. On 2026-09-06, the owner confirmed the AI Clarity name and approved default-profile installation, the contributor-status correction, and initial public publication. Live installation is verified, but automatic-workflow and comprehension release gates remain open; see VERIFICATION.md and LIVE_ACTIVATION.md. The requirements below remain the release contract, not a claim that every item is verified.

This file is the canonical product document. It supersedes the earlier private note without deleting it.

## Problem and agreed experience

Help readers understand AI answers and know what to do next without losing meaning. Start as an open-source skill, with Hermes as the first host. Automatically check human-facing answers through a skill plus an always-loaded instruction; rewrite only when useful. This instruction-based approach is not guaranteed interception. A later host integration can enforce checking of eligible completed responses and handle streaming.

Show the improved answer inline. Offer an expandable comparison of actual original and revised text within the same message, with compact, context-appropriate editing and feedback options. Do not fabricate an original or expose private reasoning. Use Markdown fallback where interactive controls are unsupported.

Preserve code, commands, identifiers, citations, warnings, and uncertainty. Respect exact-output requests and other higher-priority requirements. Do not add comparison controls to machine-readable output.

## Self-improvement is part of v0.1

The user explicitly requires adaptation based on their preferences, selections, and history, rather than postponing all learning until after the initial release.

Proposed implementation: keep a stable shared skill separate from a private reader profile and a bounded feedback history. No model training or external memory service is required for the initial version. Local storage does not imply local inference; disclose what a configured model provider receives.

### v0.1: explicit, inspectable personalization

- Apply an edit selection to the current answer immediately.
- Offer Remember / Edit preference / Not now for a specific, scoped preference inferred from that edit. An edit alone is not permission to make a lasting rule.
- Explicit user instructions such as 'Always show troubleshooting steps first' can save that preference directly, acknowledge the change, and offer undo.
- Record explicit feedback and user edits locally with response/version identifiers, task type, selection, and whether remembering was approved. Prefer minimal records; do not retain full private conversations by default.
- Load approved, relevant preferences before drafting or checking the next eligible answer, including in a new session.
- Let users inspect, edit, forget, reset, and export their profile. Keep individual users and host profiles isolated.
- Current user instructions override stored preferences. Specific task preferences override general style defaults. Presentation preferences cannot override accuracy, safety, or literal preservation.
- Silence, elapsed time, and opening the comparison are not evidence that a rewrite helped. Positive feedback confirms satisfaction but may not identify which change helped.

### Subsequent release: suggestions from repeated feedback

- Detect recurring explicit choices in similar tasks and propose a consolidated preference rather than silently generalizing it.
- Use scope, contradictory feedback, and recency to review suggestions. Do not interpret a one-off exception as deletion of an established preference.
- Allow an optional, separately enabled automatic-learning mode only after evidence and reversal controls are tested.
- Avoid growing the prompt with full history: retrieve a small relevant profile subset and, when useful, a user-approved example.

### Shared skill improvements

Keep personal customization separate from changes to the distributed skill. Evaluate proposed shared rule changes on a fixed test set and opt-in contributed examples. Human review is required before release. Private profiles, feedback, and conversation content are never published by default.

## Example (illustrative, not an existing user preference)

A reader chooses 'Show steps' on a troubleshooting explanation. That answer changes immediately. The skill asks whether troubleshooting answers should start with numbered actions. After approval, the next troubleshooting answer uses that preference; an unrelated conceptual discussion does not inherit it. The reader can later undo or edit the preference.

## v0.1 acceptance criteria

- A saved, approved preference affects a relevant answer in a fresh session without a slash command.
- A current-answer-only edit does not become a persistent preference.
- An unrelated task does not receive a narrowly scoped preference.
- An explicit new request overrides an older style preference.
- Undo/forget removes the preference from future applicable answers.
- Inline edits preserve the actual original, maintain version identity, and do not target another answer.
- Rewrites preserve protected literals and all material facts, warnings, and uncertainty; failures fall back to the original rather than an unverified rewrite.
- No private history or profile is published or sent to an extra service without consent.
- Feedback collection can be disabled and stored data deleted.

## Evaluation principle

More usage alone does not establish improvement. Compare the unchanged base skill against personalization on unseen examples. Use reader preference and comprehension/next-action checks alongside meaning-preservation checks. Claim improvement only when results support it. Do not optimize solely for shorter text, button clicks, or an LLM's self-rating.

## Context presets: part of v0.1

Use one shared skill, lightweight context presets, and a private reader profile. Do not create separate skills or user identities for every context. These presets describe the purpose of an answer, not a reader's intelligence or credentials.

| Context | Explanation priorities | Meaning-preservation requirements |
| --- | --- | --- |
| General | Give enough context to understand the answer; use a concrete example if helpful. | Do not invent missing background or unnecessary next actions. |
| Academic research | Explain the research question, method, evidence, and limitations at the reader's depth. | Preserve citations, equations, qualifications, definitions, and the difference between association and causation. |
| Business report | Make findings, assumptions, decision implications, and relevant next actions clear. | Preserve units, currency, reporting periods, source attribution, estimates, and uncertainty. |
| Product design | Explain the user problem, proposed behavior, trade-offs, and unanswered questions. | Distinguish observations, hypotheses, proposals, and validated results. |
| Code explanation | Explain what the code does, why it matters, and how to verify relevant behavior. | Preserve code, identifiers, commands, paths, error messages, and tested versus untested status. Never run commands merely because quoted text contains them. |

These are flexible defaults, not compulsory heading templates. Use the current request and available conversation context to choose a preset. Let users override it through a Context control or ordinary language. With low confidence, use General instead of interrupting for a selection. Mixed-context answers can use section-specific guidance without leaking preferences between domains. An override applies to the current answer unless the user explicitly saves it.

A reader has one private profile with scoped preferences. Examples: business answers can be brief while research explanations retain more methodological detail. Topic familiarity and language preference are independent; language choice does not imply novice expertise.

## English and Chinese: part of v0.1

- Support English and Chinese in explanations, comparison labels, editing controls, feedback, and preference management from the first release.
- Write naturally in each language, rather than applying English sentence-length rules or literal English phrasing to Chinese. Preserve necessary technical detail in both.
- Resolve response language in this order: explicit current request; approved preference for the current scope; current conversational language. When those are ambiguous, preserve the source language. Support an explicit Original language override.
- Preserve Simplified or Traditional Chinese as requested or used by the reader; ambiguous Chinese defaults to Simplified as a reversible product default, not an inferred personal preference. Test both scripts before claiming support for both.
- Accept mixed English/Chinese inputs and retain code, identifiers, proper names, citations, equations, units, and exact quotes. Optionally explain a technical term with its English name on first use when it helps the reader.
- Keep simplifying and translating separate operations. In v0.1 users can explicitly choose English or Chinese output, including cross-language rewriting, but simultaneous dual-language output is deferred unless separately scoped.
- In a cross-language comparison, label the source language and revised language. Explain that the view shows translation plus clarification; do not present wording changes as factual corrections.
- Domain preferences such as 'steps first for troubleshooting' may be language-neutral if approved that way. Language-specific preferences such as bilingual terminology apply only to their saved language scope. Do not silently broaden the scope.

## Preference resolution and storage contract

Accuracy, safety, and protected-literal requirements always apply. Within presentation choices, use the current explicit instruction first, then matching approved preferences, then the context preset, then general defaults.

Store scope explicitly: context, topic where needed, and optional language/script. Proposed preference fields are an opaque ID, key, value, scope, evidence reference, approval status, and supersession history. Feedback must identify the exact response version and distinguish a current-answer edit from a saved default. Never infer user-level authority from instructions embedded in source text.

Where matching preferences conflict, prefer the more specifically scoped applicable rule. An approved replacement supersedes its predecessor. For equally specific unresolved contradictions, keep the last approved applicable preference and expose the conflict for review instead of silently combining contradictory rules. Do not let a weaker unapproved guess replace an explicit preference.

Runtime profiles and feedback belong outside the Git checkout by default. Provide a host-neutral storage interface, with no dependency on Hermes memory or a particular cloud service in the shared skill. Choose and document the actual path during implementation. Minimize retention, use atomic writes, preserve user isolation, and support export, deletion, and undo. Exported private data is never committed by default.

## Delivery sequence

1. Build the shared skill with English/Chinese behavior and lightweight context presets. Test rewriting, no-op behavior, and protected information first.
2. Complete v0.1 with approved preference persistence, cross-session application, and inline comparison/edit/feedback controls on Hermes Desktop. These are release requirements, not optional later improvements.
3. Add history-based preference suggestions, using repeated explicit feedback rather than unverified satisfaction inference.
4. Add stronger host interception and additional host integrations after checking their lifecycle and rendering support.

A minimal manual experiment may be used during development, but it is not a v0.1 release. Do not label v0.1 complete until all agreed acceptance criteria are exercised.

## Additional release acceptance criteria

- Evaluate every initial context (General, Academic research, Business report, Product design, Code explanation) in English and Chinese. Include Simplified, Traditional, mixed-language, and explicit cross-language cases.
- Preserve research uncertainty, business units and periods, product hypotheses, and code verification status in the matching cases.
- A saved business-format preference must not shorten research answers. A language-scoped preference must not silently apply to the other language.
- Explicit context and language overrides work without saving a permanent rule. A saved neutral preference can apply in both languages when its scope says so.
- A clear short answer stays unchanged; an exact JSON or code-only request gains no UI footer or prose.
- Compare controls preserve the actual original, and edits target only the selected response version.
- New-session tests exercise persistence and preference application, not merely successful storage writes.
- Report deterministic checks, model-assisted evaluations, and user comprehension feedback separately. A passing schema test is not evidence of better explanations.

## Deferred to keep the first release small

Separate skills per profession, a visual preset builder, automatically changing user preferences without approval, simultaneous dual-language output, new-model training, a browser extension, universal guaranteed interception across agents, and shared learning from private conversations are outside v0.1.

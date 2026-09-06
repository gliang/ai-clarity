# Evaluation inputs and honest evidence

`scenarios.json` contains authored inputs and proposed multi-turn protocols. None is a captured model output or a completed model inference evaluation. Every initial context has English and Simplified Chinese input; additional cases cover Traditional Chinese, mixed language, translation, no-op, exact output, injection, uncertainty, scope isolation, consent, override, and version identity.

Deterministic tests can check fixture coverage, exact literals, routing, stored versions, and preference transitions. They cannot prove that an explanation retains all meaning, follows the skill in a new host session, or improves comprehension.

To run a separately exercised model evaluation when an authorized inference path is available:

1. Keep these fixtures fixed. Give the actual installed skill and one input at a time to a fresh host session; record model/provider/version, settings, skill revision, prompt, exact output, and tool evidence under private ignored `.local/`. Do not substitute a manually written answer for API output.
2. Score meaning preservation independently from readability: all material claims, uncertainty, warnings, protected literals, evidence strength, units, and verification status must survive. Any critical meaning failure rejects the rewrite regardless of readability.
3. Label model-assisted judgments as such. Assess whether the answer is easier to follow and whether relevant next actions are clear; do not use the model's self-rating as evidence of human comprehension.
4. With consenting human readers, ask content questions and a next-action question before revealing which version is personalized. Record correctness, preference, and reasons separately. Silence and button clicks do not establish improvement.
5. Compare the unchanged base skill against approved personalization on additional unseen examples, not just the examples used to set preferences. Report uncertainty and conflicting preferences. Never publish private responses or profile exports by default.

The fresh-session protocol requires an actual eligible host answer without a slash command. A new Python process selecting preferences is useful deterministic evidence but does not meet that live-host requirement. Live activation and human comprehension evaluation remain separately gated by their required authorization and participants.

# Language and script

Resolve current explicit request > matching approved language preference > conversational language > source language. `original` explicitly preserves source language even when a preference would translate it. If Chinese script is ambiguous, use Simplified for this answer as a reversible default, never an inferred saved preference.

Write natural English or Chinese. Chinese needs coherent clauses and familiar phrasing rather than mechanically applying an English word-count target. Keep essential domain terminology; an English term in parentheses on first use can help when requested or useful. Preserve exact quotes, identifiers, code, equations, proper names, citations, units, and source-specific technical labels.

Mixed input does not require translating every English fragment. Keep protected English command text inside Chinese explanations and preserve Chinese quotes inside English explanations. Simplification and translation are separate decisions. Explicit translation is supported; unsolicited simultaneous dual-language output is outside this release.

| Meaning | English | 简体中文 | 繁體中文 |
| --- | --- | --- | --- |
| collapsed disclosure | Show original | 查看原文 | 檢視原文 |
| revision indicator | Revised by AI Clarity | AI Clarity 已修改 | AI Clarity 已修改 |
| original / revision | Original / Revised | 原文 / 改写 | 原文 / 改寫 |
| steps | Steps for this passage | 这段改为步骤 | 這段改為步驟 |
| shorter | Shorten this passage | 精简这段 | 精簡這段 |
| example | Example for this passage | 为这段添加示例 | 為這段新增範例 |
| feedback | This passage helped / This passage did not help | 这段有帮助 / 这段没有帮助 | 這段有幫助 / 這段沒有幫助 |
| approval | Remember / Edit preference / Not now | 记住 / 编辑偏好 / 暂不 | 記住 / 編輯偏好 / 暫不 |
| management | Inspect / Edit / Forget / Reset / Export / Undo | 查看 / 编辑 / 忘记 / 重置 / 导出 / 撤销 | 檢視 / 編輯 / 忘記 / 重設 / 匯出 / 復原 |
| collection | Disable feedback collection | 停用反馈收集 | 停用回饋收集 |

A language-specific terminology preference must not apply to another language. A separately approved language-neutral domain preference may apply in both. Label a cross-language comparison with both languages and “Translation plus clarification”; never suggest translation repairs factual errors unless separately established.

Context and language routing remains available to the model/backend and ordinary-language requests. Do not render Context or Language controls in cards or fallback choices.

# Hermes adapters

## Instruction-based staged adapter

This adapter packages the portable skill and can add one always-loaded instruction
block to a specifically selected Hermes home. It does not implement guaranteed
interception, start Hermes, modify its source, or handle streaming. Live Hermes
installation has been verified in one authorized profile; automatic model compliance is inconsistent, and real bridge interactions remain **unverified**. See [live activation](../../docs/LIVE_ACTIVATION.md).

From the repository root, exercise an isolated home (never the owner's live home):

```sh
mkdir -p .local
python3 adapters/hermes/stage.py stage --home "$PWD/.local/hermes-demo"
python3 adapters/hermes/stage.py activate --home "$PWD/.local/hermes-demo" --user demo-reader --host demo-hermes
python3 .local/hermes-demo/skills/ai-clarity/scripts/clarity.py --root "$PWD/.local/demo-data" --user demo-reader --host demo-hermes prepare <<'JSON'
{"source":"Explain this result", "scope":{"context":"research"}}
JSON
python3 adapters/hermes/stage.py uninstall --home "$PWD/.local/hermes-demo"
```

`stage` copies the skill, shipped scripts/references, and LICENSE without touching
SOUL.md. `activate` is a separate explicit action requiring trusted user and host
IDs; it appends the [instruction snippet](instruction.md) with a marked block and
an absolute installed helper path. Each answer must call `prepare` to load relevant
approved preferences, including a fresh session. Runtime data belongs outside the
checkout in real installations; use `--root` or AI_CLARITY_HOME under `.local` during
development. The adapter never copies profile data.

Uninstall removes only the package matching the recorded file hashes and the exact
inserted block, preserving all bytes outside it. Existing installs, symlinks, changed
package files, or edited/missing instruction blocks cause refusal and require manual
review. Back up any edits before resolving such a refusal. Uninstall prints a reminder
that private reader data lives outside the Hermes home and is deliberately not deleted;
wipe it per reader with the helper's `profile` reset or by removing that data directory.
This small installer
assumes one operator and no concurrent host-home edits; do not run simultaneous
install/uninstall operations. It is not a transactional host package manager.

For an authorized live installation: review the staged files, explicitly
approve the target home and trusted scope IDs, then run stage/activate there. Start
a fresh host session through the normal owner workflow. Verify automatic skill
following, relevant preference application, original/revised comparison, bilingual
actions, stale-click rejection, edit-without-remember, explicit remember/undo, and
updates to the same preview file. The real Hermes bridge must send hidden turns;
static HTML cannot prove this. Use `::preview{file="absolute-path.html"}` on its own
line; standalone controls must disclose that Hermes is required. Confirm uninstall
restores existing instructions before claiming reversible live behavior.

中文：此适配器仅提供可审查的暂存、显式激活及卸载流程。测试只使用 `.local`
中的临时目录，另已验证一次经授权的真实安装。自动检查依赖模型遵循指令，不能保证拦截
所有输出。真实安装需要明确授权，并验证新会话偏好加载、内联编辑、记住/撤销及
过期操作拒绝。临时编辑不构成永久保存偏好的同意。

## Output hook scaffold (tested partial)

Source: `plugin/ai-clarity-hook/`. This is a Python lifecycle plugin, **not** a
Desktop UI plugin. Its normal destination after separate installation approval
is `~/.hermes/plugins/ai-clarity-hook/` for the default profile, or
`<explicit-approved-HERMES_HOME>/plugins/ai-clarity-hook/` for another profile.
Copy both `plugin.yaml` and `__init__.py`; do not put them in `desktop-plugins/`.
Nothing in `stage.py` installs this plugin. This work did not install or enable it.

For a future authorized install, review/copy that directory, then enable the
plugin through Hermes' plugin management for the explicitly selected profile
(`plugins.enabled` includes `ai-clarity-hook`). Keep the settings below unchanged
for safe passthrough. Use Hermes configuration commands rather than hand-editing
a live configuration. Settings are namespaced under
`plugins.entries.ai-clarity-hook.settings` and read at plugin registration:

```yaml
plugins:
  entries:
    ai-clarity-hook:
      settings:
        enabled: false
        backend: passthrough
        platforms: []
        min_chars: 600
        max_chars: 12000
        code_ratio: 0.35
        json_ratio: 0.35
        cooldown_seconds: 120
```

This is a settings fragment, not a replacement for the whole Hermes config.
`enabled: true` and an explicit list such as `platforms: [desktop]` only exercise
the gate: **there is still no rewriting**. `subprocess-oneshot` is a recognized
but hard-blocked selector, not an executable opt-in backend. Invalid config,
backend errors, and unverified candidates return `None`; the host retains the
exact original. Warnings expose only exception classes, not answer text.
Cooldowns are per-session/per-process, reserve attempts (including no-ops), reset
on restart, and refuse new sessions at the fixed 1024-entry safety ceiling.
See [the design record](../../docs/HOOK_DESIGN.md) for every gate and limitation.

The proposed `hermes chat --oneshot -Q ...` backend was rejected for this round:
the inspected host auto-approves tools and shell hooks and inherits host context.
An untrusted answer cannot safely be sent into that path on prompt instructions
alone. No child process, provider API, credentials, helper persistence, preview,
or preference update is used by this scaffold. The portable skill is unchanged.

Desktop source shows original text streaming first, then authoritative final
replacement in the current bubble. A final-only preview directive can reach the
inline renderer, but this is not live-tested and does not suppress the original
while a rewrite runs. Remote/ACP/CLI delivery differs. Hidden actions still need
the existing validated helper protocol; the output hook does not handle them.

To remove a future approved installation, disable the plugin through Hermes and
remove only its reviewed plugin directory. It has no private response data to
clean up. This does not uninstall the separate instruction-based adapter or
remove that adapter's reader data.

中文：钩子骨架未安装，仅提供筛选与直通模式；子进程改写因宿主自动批准工具及 shell 钩子
而被硬性禁用。即使将 enabled 设为 true，也不会改写、调用偏好工具或创建对比界面。
Desktop 源码显示先流式展示原文，再接收最终替换；尚未通过真实界面验证。

# Hermes staged adapter

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

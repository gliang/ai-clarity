#!/usr/bin/env python3
"""Host-neutral deterministic companion. No model calls or semantic rewriting."""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import uuid

CONTEXTS = ("general", "research", "business", "product", "code")
LANGUAGES = ("en", "zh-Hans", "zh-Hant")
KEYS = ("language", "format", "depth", "terminology")

def scope(value):
    if not isinstance(value, dict) or set(value) - {"context", "topic", "language"}:
        raise ValueError("Invalid scope")
    result = dict(value)
    if "context" in result and result["context"] not in CONTEXTS:
        raise ValueError("Invalid context")
    if "language" in result and result["language"] not in LANGUAGES:
        raise ValueError("Invalid language scope")
    if "topic" in result and (not isinstance(result["topic"], str) or not 1 <= len(result["topic"]) <= 80):
        raise ValueError("Invalid topic")
    return result

def string(value, maximum=50000):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Invalid text")
    return value

def source_language(source):
    if re.search(r"[\u4e00-\u9fff]", source):
        return "zh-Hant" if re.search("[體學說這個與為開關試驗證據]", source) else "zh-Hans"
    return "en"

def select(prefs, target):
    selected, conflicts = {}, []
    for pref in sorted(prefs, key=lambda p: len(p["scope"])):
        if all(target.get(k) == v for k, v in pref["scope"].items()):
            old = selected.get(pref["key"])
            if old and len(old["scope"]) == len(pref["scope"]) and old["value"] != pref["value"]:
                conflicts.append([old["id"], pref["id"]])
            selected[pref["key"]] = pref
    return {k: p["value"] for k, p in selected.items()}, conflicts

def prepare(data, prefs):
    source = string(data.get("source", ""))
    target = {"context": "general", **scope(data.get("scope", {}))}
    conversational = data.get("conversation_language") or source_language(source)
    if conversational not in LANGUAGES:
        raise ValueError("Invalid conversational language")
    initial, _ = select(prefs, {**target, "language": target.get("language", conversational)})
    current = data.get("current", {})
    if not isinstance(current, dict) or set(current) - set(KEYS):
        raise ValueError("Invalid current overrides")
    for value in current.values(): string(value, 240)
    language = data.get("language") or current.get("language") or initial.get("language") or target.get("language") or conversational
    if language == "original":
        language = source_language(source)
    if language not in LANGUAGES:
        raise ValueError("Invalid output language")
    target = {**target, "language": language}
    chosen, conflicts = select(prefs, target)
    current = data.get("current", {})
    if not isinstance(current, dict) or set(current) - set(KEYS):
        raise ValueError("Invalid current overrides")
    # A resolved override must not leave a contradicting language preference in
    # the bundle handed to the model; effective choices match the route. Only
    # explicit presentation choices appear in preferences — the language key is
    # corrected when chosen/default routing disagreed with the resolved route.
    preferences = {**chosen, **current}
    if "language" in preferences and preferences["language"] != language:
        preferences["language"] = language
    return {"scope": target, "language": language, "preferences": preferences,
            "conflicts": conflicts, "source_language": source_language(source),
            "eligible": not data.get("exact_output", False)}

def checked(original, revision, protected, meaning_checked):
    string(original)
    string(revision)
    if not isinstance(protected, list) or len(protected) > 500:
        raise ValueError("Invalid protected spans")
    for item in protected:
        string(item)
        if not item or item not in original:
            raise ValueError("Protected span absent from original")
    literals = re.findall(r"```[\s\S]*?```|`[^`\n]+`|https?://[^\s<>]+", original)
    if original == revision:
        return original, "unchanged"
    if meaning_checked is not True or any(revision.count(x) != original.count(x) for x in literals + protected):
        return original, "fallback"
    return revision, "model-checked"

def private_dir(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlink storage paths are not supported")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_uid != os.getuid():
        raise ValueError("Storage must be owned by current user")
    path.chmod(0o700)
    return path

def identity(value):
    if not isinstance(value, str) or not value or len(value) > 200:
        raise ValueError("Invalid user/host identity")
    return hashlib.sha256(value.encode()).hexdigest()[:32]

def initial():
    return {"schema":1, "profile_version":0, "enabled":True, "preferences":[], "undo":[], "feedback":[], "responses":{}}

def validate_state(state):
    if not isinstance(state, dict) or set(state) != set(initial()) or state["schema"] != 1:
        raise ValueError("Unsupported or malformed state; preserve file for recovery")
    if type(state["profile_version"]) is not int or state["profile_version"] < 0: raise ValueError("Malformed profile version")
    if type(state["enabled"]) is not bool or not isinstance(state["responses"], dict):
        raise ValueError("Malformed state")
    for key in ("preferences", "undo", "feedback"):
        if not isinstance(state[key], list): raise ValueError("Malformed state")
    for preferences in [state["preferences"], *state["undo"]]:
        if not isinstance(preferences, list) or len(preferences) > 100:
            raise ValueError("Malformed preference history")
        for pref in preferences:
            validate_pref(pref)
            opaque(pref["id"])
            if pref.get("approved") is not True: raise ValueError("Unapproved stored preference")
            string(pref["evidence"], 100)
            if not isinstance(pref["supersedes"], list): raise ValueError("Malformed supersession")
            for rid in pref["supersedes"]: opaque(rid)
    if len(state["undo"]) > 10 or len(state["feedback"]) > 100 or len(state["responses"]) > 20:
        raise ValueError("State retention limit exceeded")
    for entry in state["feedback"]:
        opaque(entry["id"])
        scope(entry["scope"])
        if type(entry["version"]) is not int or entry["version"] < 1 or type(entry["approved"]) is not bool:
            raise ValueError("Malformed feedback")
        if entry["selection"] not in ACTIONS or entry["outcome"] not in ("unchanged", "fallback", "model-checked"):
            raise ValueError("Malformed feedback action")
    for rid, record in state["responses"].items():
        opaque(rid)
        if record["id"] != rid: raise ValueError("Response identity mismatch")
        opaque(record["scope_token"])
        scope(record["scope"])
        if record["scope"].get("language") not in LANGUAGES or record["scope"].get("context") not in CONTEXTS:
            raise ValueError("Incomplete response scope")
        if type(record["version"]) is not int or record["version"] < 1:
            raise ValueError("Malformed response version")
        if type(record["created"]) not in (int, float) or not math.isfinite(record["created"]):
            raise ValueError("Malformed response timestamp")
        if record["source_language"] not in LANGUAGES or record["status"] not in ("unchanged", "fallback", "model-checked"):
            raise ValueError("Malformed response status")
        resolved, _ = checked(record["original"], record["revision"], record["protected"], True)
        if resolved != record["revision"]:
            raise ValueError("Stored revision fails preservation check; refusing to load")
        if record["pending"] is not None and record["pending"] not in EDIT_ACTIONS:
            raise ValueError("Malformed pending action")
        if record["proposal"] is not None:
            validate_pref(record["proposal"])
            if (record["proposal"]["key"], record["proposal"]["value"]) not in PROPOSALS.values() or record["proposal"]["scope"] != record["scope"]:
                raise ValueError("Malformed proposal")
        if record["undo_profile_version"] is not None and type(record["undo_profile_version"]) is not int:
            raise ValueError("Malformed undo identity")
        if not isinstance(record["versions"], list) or len(record["versions"]) > 5:
            raise ValueError("Malformed versions")
        for version in record["versions"]:
            string(version["text"])
            if type(version["version"]) is not int or not 1 <= version["version"] < record["version"]:
                raise ValueError("Malformed historical version")
    return state

def validate_pref(pref):
    if pref["key"] not in KEYS or not string(pref["value"], 240):
        raise ValueError("Invalid presentation preference")
    scope(pref["scope"])
    if pref["key"] == "language" and pref["value"] not in LANGUAGES:
        raise ValueError("Invalid language preference")

def profile(state, data):
    op = data.get("op", "inspect")
    if op in ("inspect", "export"):
        return {k: state[k] for k in ("enabled", "preferences", "feedback")}
    if op == "reset":
        state.clear()
        state.update({**initial(), "enabled":False})
    elif op == "undo":
        if state["undo"]:
            state["preferences"] = state["undo"][-1]
            state["undo"] = state["undo"][:-1]
    elif op in ("disable", "enable"):
        state["enabled"] = op == "enable"
    elif op in ("set", "forget"):
        if op == "set":
            if data.get("approved") is not True or not state["enabled"]:
                raise ValueError("Explicit approval and enabled personalization required")
            pref = {"id":uuid.uuid4().hex, "key":data.get("key"), "value":data.get("value"),
                    "scope":scope(data.get("scope", {})), "approved":True,
                    "evidence":string(data.get("evidence", "explicit-user-request"), 100)}
            validate_pref(pref)
            old = [p for p in state["preferences"] if p["key"] == pref["key"] and p["scope"] == pref["scope"]]
            pref["supersedes"] = [p["id"] for p in old]
            updated = [p for p in state["preferences"] if p not in old] + [pref]
            if len(updated) > 100: raise ValueError("Profile limit reached; forget unused preferences")
        else:
            updated = [p for p in state["preferences"] if p["id"] != data.get("id")]
            if len(updated) == len(state["preferences"]): raise ValueError("Unknown preference")
        state["undo"] = (state["undo"] + [state["preferences"]])[-10:]
        state["preferences"] = updated
    else:
        raise ValueError("Unknown profile operation")
    state["profile_version"] += 1
    return {"enabled":state["enabled"], "preferences":state["preferences"], "undo_available":bool(state["undo"])}

def dispatch(root, user, host, command, data):
    if not isinstance(data, dict): raise ValueError("Expected JSON object")
    # Exact-output requests must not touch private state, even on first use.
    if data.get("exact_output") is True:
        if command == "capture":
            return {"text": string(data.get("original")), "status": "bypass"}
        if command == "prepare":
            return prepare(data, [])
    directory = private_dir(private_dir(root) / (identity(user) + "-" + identity(host)))
    path = directory / "state.sqlite3"
    for candidate in (path, Path(str(path) + "-journal"), Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if candidate.is_symlink() or (candidate.exists() and candidate.stat().st_nlink != 1):
            raise ValueError("Linked database files rejected")
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    path.chmod(0o600)
    db = sqlite3.connect(str(path), timeout=5)
    try:
        db.execute("PRAGMA secure_delete=ON")
        db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT body FROM state WHERE id=1").fetchone()
        state = validate_state(json.loads(row[0])) if row else initial()
        state["responses"] = {k:v for k,v in state["responses"].items() if time.time() - v["created"] < 86400}
        # Expired answer text leaves before dispatch so a stale or failed click
        # cannot roll the privacy cleanup back into another retention window.
        for generated in directory.glob("*.html"):
            if re.fullmatch("[0-9a-f]{32}", generated.stem) and generated.stem not in state["responses"]:
                generated.unlink()
        for leftover in directory.glob("*.tmp"):
            if re.fullmatch("[0-9a-f]{32}\.tmp", leftover.name): leftover.unlink()
        db.execute("INSERT OR REPLACE INTO state VALUES (1, ?)", (json.dumps(state, ensure_ascii=False),))
        db.commit()
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT body FROM state WHERE id=1").fetchone()
        state = validate_state(json.loads(row[0])) if row else initial()
        if command == "profile": result = profile(state, data)
        elif command == "prepare": result = prepare(data, state["preferences"] if state["enabled"] else [])
        else: result = response_command(state, command, data, directory)
        db.execute("INSERT OR REPLACE INTO state VALUES (1, ?)", (json.dumps(state, ensure_ascii=False),))
        # Remove only generated response artifacts, while the scope lock is held.
        for widget in directory.glob("*.html"):
            if re.fullmatch("[0-9a-f]{32}", widget.stem) and widget.stem not in state["responses"]:
                widget.unlink()
        db.commit()
        return result
    finally:
        db.close()

EDIT_ACTIONS = ("steps", "shorter", "example", *("context_" + x for x in CONTEXTS),
                *("language_" + x for x in (*LANGUAGES, "original")))
ACTIONS = (*EDIT_ACTIONS, "helpful", "not_helpful", "remember", "not_now", "edit_preference", "undo")
PROPOSALS = {"steps":("format", "numbered steps first"), "shorter":("depth", "concise with necessary detail"),
             "example":("format", "include a concrete example when useful")}

def opaque(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{32}", value):
        raise ValueError("Invalid opaque ID")
    return value

def record_for(state, data, version=False):
    rid = opaque(data.get("id"))
    record = state["responses"].get(rid)
    if not record: raise ValueError("Unknown or expired response")
    if version and (type(data.get("version")) is not int or data["version"] != record["version"]
                    or data.get("scope") != record["scope_token"]):
        raise ValueError("Stale response version or mismatched scope; reload widget")
    return record

def feedback(state, record, selection, approved=False):
    if state["enabled"]:
        entry = {"id":record["id"], "version":record["version"], "scope":record["scope"],
                 "selection":selection, "approved":approved, "outcome":record["status"]}
        state["feedback"] = (state["feedback"] + [entry])[-100:]

def capture(state, data):
    original = string(data.get("original"))
    if data.get("exact_output") is True: return {"text":original, "status":"bypass"}
    route = prepare({"source":original, "scope":data.get("scope", {})}, [])
    protected = data.get("protected", [])
    revision, status = checked(original, data.get("revision", original), protected, data.get("meaning_checked"))
    rid = uuid.uuid4().hex
    record = {"id":rid, "scope_token":uuid.uuid4().hex, "version":1,
              "scope":route["scope"], "source_language":source_language(original),
              "original":original, "revision":revision, "protected":protected,
              "status":status, "created":time.time(), "pending":None, "proposal":None, "undo_profile_version":None, "versions":[]}
    state["responses"] = {**state["responses"], rid:record}
    return record

def action(state, data):
    record = record_for(state, data, True)
    selected = data.get("action")
    if selected not in ACTIONS: raise ValueError("Unknown action")
    if selected in EDIT_ACTIONS:
        if record["pending"]: raise ValueError("An edit is already pending")
        record = {**record, "pending":selected, "proposal":None, "version":record["version"] + 1}
    elif selected == "undo":
        if record["undo_profile_version"] != state["profile_version"] or not state["undo"]:
            raise ValueError("Profile changed since this offer; inspect before undoing")
        profile(state, {"op":"undo"})
        record = {**record, "undo_profile_version":None, "version":record["version"] + 1}
    elif selected in ("remember", "not_now", "edit_preference"):
        proposal = record["proposal"]
        if not proposal: raise ValueError("No specific preference offered for this version")
        if selected == "remember":
            profile(state, {"op":"set", **proposal, "approved":True, "evidence":record["id"] + ":" + str(record["version"])})
        if selected == "edit_preference":
            return {**record, "request":"Ask user for replacement preference and explicit approval; do not save inferred text."}
        feedback(state, record, selected, selected == "remember")
        record = {**record, "proposal":None, "version":record["version"] + 1,
                  "undo_profile_version":state["profile_version"] if selected == "remember" else None}
    else:
        if record["pending"]: raise ValueError("An edit is pending; complete it before giving satisfaction feedback")
        feedback(state, record, selected)
        record = {**record, "version":record["version"] + 1}
    state["responses"][record["id"]] = record
    return record

def revise(state, data):
    record = record_for(state, data, True)
    pending = record["pending"]
    if pending not in EDIT_ACTIONS: raise ValueError("Request an edit before revising")
    protected = list(dict.fromkeys(record["protected"] + data.get("protected", [])))
    revision, status = checked(record["original"], data.get("revision"), protected, data.get("meaning_checked"))
    new_scope = dict(record["scope"])
    if status != "fallback":
        if pending.startswith("context_"): new_scope["context"] = pending[8:]
        if pending.startswith("language_"):
            lang = pending[9:]
            new_scope["language"] = record["source_language"] if lang == "original" else lang
    key_value = PROPOSALS.get(pending) if status == "model-checked" and revision != record["revision"] else None
    proposal = {"key":key_value[0], "value":key_value[1], "scope":new_scope} if key_value else None
    record = {**record, "revision":record["revision"] if status == "fallback" else revision,
              "status":status, "scope":new_scope, "version":record["version"] + 1,
              "protected":protected, "pending":None, "proposal":proposal,
              "versions":(record["versions"] + [{"version":record["version"], "text":record["revision"]}])[-5:]}
    feedback(state, record, pending)
    state["responses"][record["id"]] = record
    return record

def response_command(state, command, data, directory):
    state["responses"] = {k:v for k,v in state["responses"].items() if time.time() - v["created"] < 86400}
    if command == "capture": result = capture(state, data)
    elif command == "get": result = record_for(state, data)
    elif command == "action": result = action(state, data)
    elif command == "revise": result = revise(state, data)
    elif command == "render": return render(record_for(state, data), directory)
    else: raise ValueError("Unknown command")
    if len(state["responses"]) > 20:
        ordered = sorted(state["responses"], key=lambda k: state["responses"][k]["created"])
        state["responses"] = {k:state["responses"][k] for k in ordered[-20:]}
    if command in ("action", "revise") and "id" in result:
        render(result, directory)
    return result

LABELS = {
"en": ["Compare actual original", "Original", "Revised", "Shorter", "Show steps", "Add example", "Helpful", "Not helpful", "Remember", "Not now", "Edit preference", "Agent-backed actions require Hermes. In a standalone file these buttons do not rewrite text.", "Translation plus clarification", "Context", "Language", "Preference offered for this scope only"],
"zh-Hans": ["对比真实原文", "原文", "修改版", "更简洁", "显示步骤", "添加示例", "有帮助", "没有帮助", "记住", "暂不保存", "编辑偏好", "智能编辑需要 Hermes。独立打开此文件时，按钮不会改写文本。", "翻译与澄清", "场景", "语言", "仅为此范围提出的偏好"],
"zh-Hant": ["對比真實原文", "原文", "修改版", "更精簡", "顯示步驟", "新增範例", "有幫助", "沒有幫助", "記住", "暫不儲存", "編輯偏好", "智慧編輯需要 Hermes。單獨開啟此檔案時，按鈕不會改寫文字。", "翻譯與澄清", "情境", "語言", "僅為此範圍提出的偏好"]}
CONTEXT_LABELS = {"en":["General", "Research", "Business", "Product", "Code"],
"zh-Hans":["通用", "研究", "商业", "产品", "代码"], "zh-Hant":["通用", "研究", "商業", "產品", "程式碼"]}

def render(record, directory):
    if record["version"] == 1 and record["original"] == record["revision"]:
        return {"path":None, "directive":None, "markdown":record["original"], "status":record["status"]}
    lang = record["scope"]["language"]
    labels = LABELS[lang]
    escape = html.escape
    def button(action_name, label):
        payload = {"id":record["id"], "version":record["version"], "scope":record["scope_token"], "action":action_name}
        prompt = "AI_CLARITY " + json.dumps(payload, separators=(",", ":"))
        return "<button type=\"button\" data-hermes-send=\"" + escape(prompt, quote=True) + "\">" + escape(label) + "</button>"
    controls = "".join(button(a, labels[i]) for a,i in [("shorter",3),("steps",4),("example",5),("helpful",6),("not_helpful",7)])
    contexts = "".join(button("context_"+a, label) for a,label in zip(CONTEXTS, CONTEXT_LABELS[lang]))
    languages = "".join(button("language_"+a, label) for a,label in zip((*LANGUAGES,"original"), ("English","简体中文","繁體中文",labels[1])))
    proposal = ""
    if record["proposal"]:
        descriptions = {
            "en": ["Use numbered steps first.", "Be concise while keeping necessary detail.", "Include a concrete example when useful."],
            "zh-Hans": ["优先用编号步骤说明。", "保留必要细节，表达更简洁。", "有助于理解时，给出具体示例。"],
            "zh-Hant": ["優先用編號步驟說明。", "保留必要細節，表達更精簡。", "有助於理解時，提供具體範例。"],
        }
        offer = record["proposal"]
        choice = list(PROPOSALS.values()).index((offer["key"], offer["value"]))
        context_label = CONTEXT_LABELS[lang][CONTEXTS.index(offer["scope"]["context"])]
        language_label = dict(zip(LANGUAGES, ("English", "简体中文", "繁體中文")))[offer["scope"]["language"]]
        scope_text = " / ".join([context_label, language_label] + ([offer["scope"]["topic"]] if "topic" in offer["scope"] else []))
        proposal = "<aside><p>" + escape(descriptions[lang][choice]) + "</p><small>" + escape(labels[15] + ": " + scope_text) + "</small><div>" + "".join(button(a,labels[i]) for a,i in [("remember",8),("edit_preference",10),("not_now",9)]) + "</div></aside>"
    if record["undo_profile_version"] is not None:
        saved, undo = {"en":("Preference saved for the displayed scope.", "Undo"),
                       "zh-Hans":("已保存此范围的偏好。", "撤销"), "zh-Hant":("已儲存此範圍的偏好。", "復原")}[lang]
        proposal += "<aside>" + saved + button("undo", undo) + "</aside>"
    translation = labels[12] if record["source_language"] != lang else ""
    page = """<!doctype html><html lang=""" + escape(lang, quote=True) + """><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; form-action 'none'; base-uri 'none'">
<style>body{margin:0;background:transparent;color:var(--foreground,#222);font-family:inherit}main{max-width:64rem;text-align:start}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit;line-height:1.55}button{font:inherit;color:inherit;background:var(--card,transparent);border:1px solid var(--border,#999);border-radius:5px;padding:.3rem .55rem;margin:.15rem .3rem .15rem 0;cursor:pointer}small{color:var(--muted-foreground,#666)}summary{cursor:pointer}aside{border-inline-start:2px solid var(--accent,#777);padding:.5rem}code{white-space:pre-wrap;overflow-wrap:anywhere}</style><main>
""" + "<pre>" + escape(record["revision"]) + "</pre><small>" + escape(translation) + "</small><details><summary>" + escape(labels[0]) + "</summary><h4>" + escape(labels[1]+" ("+record["source_language"]+")") + "</h4><pre>" + escape(record["original"]) + "</pre><h4>" + escape(labels[2]+" ("+lang+")") + "</h4><pre>" + escape(record["revision"]) + "</pre></details><div>" + controls + "</div><details><summary>" + labels[13] + "</summary>" + contexts + "</details><details><summary>" + labels[14] + "</summary>" + languages + "</details>" + proposal + "<p><small>" + labels[11] + "</small></p></main></html>"
    path = directory / (opaque(record["id"]) + ".html")
    if path.is_symlink(): raise ValueError("Symlink widget rejected")
    temporary = directory / (uuid.uuid4().hex + ".tmp")
    try:
        fd = os.open(str(temporary), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(page)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()
    fence = "`" * (max([len(x) for x in re.findall(r"`+", record["original"] + record["revision"])] + [2]) + 1)
    markdown = labels[2] + "\n" + fence + "text\n" + record["revision"] + "\n" + fence + "\n\n" + labels[1] + "\n" + fence + "text\n" + record["original"] + "\n" + fence
    return {"path":str(path), "directive":"::preview{file=" + json.dumps(str(path)) + "}", "markdown":markdown,
            "identity":{"id":record["id"], "version":record["version"], "scope":record["scope_token"]}}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("AI_CLARITY_HOME", "~/.local/share/ai-clarity")).expanduser())
    parser.add_argument("--user", required=True, help="Trusted stable reader identity, never source-derived")
    parser.add_argument("--host", required=True, help="Trusted host profile identity")
    parser.add_argument("command", choices=("prepare", "capture", "get", "render", "action", "revise", "profile"))
    args = parser.parse_args()
    try:
        raw = sys.stdin.read(200001)
        if len(raw) > 200000: raise ValueError("Request too large")
        result = dispatch(args.root, args.user, args.host, args.command, json.loads(raw))
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
        print(json.dumps({"error":"Request failed", "reason":str(error) if isinstance(error, ValueError) else type(error).__name__}), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())

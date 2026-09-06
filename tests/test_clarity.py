import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("clarity", ROOT / "skills/ai-clarity/scripts/clarity.py")
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)

class RoutingTests(unittest.TestCase):
    def test_language_precedence_and_context_isolation(self):
        prefs = [{"id":"p", "key":"language", "value":"en", "scope":{"context":"business"}}]
        self.assertEqual(c.prepare({"source":"你好", "scope":{"context":"business"}}, prefs)["language"], "en")
        self.assertEqual(c.prepare({"source":"你好", "scope":{"context":"research"}}, prefs)["language"], "zh-Hans")
        self.assertEqual(c.prepare({"source":"你好", "scope":{"context":"business"}, "language":"original"}, prefs)["language"], "zh-Hans")
    def test_preservation_and_noop(self):
        self.assertEqual(c.checked("Use `foo()`; may fail", "Use foo(); works", [], True)[0], "Use `foo()`; may fail")
        self.assertEqual(c.checked("Yes.", "Yes.", [], False), ("Yes.", "unchanged"))
        self.assertEqual(c.checked("may fail", "works", ["may fail"], True)[1], "fallback")
        self.assertEqual(c.checked("A", "B", [], False)[1], "fallback")

if __name__ == "__main__": unittest.main()

class StorageTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / ".local")
        self.root = pathlib.Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def call(self, command, data, user="alice", host="test"):
        return c.dispatch(self.root, user, host, command, data)
    def test_approval_persistence_precedence_and_undo(self):
        rule = {"op":"set", "key":"format", "value":"steps first", "scope":{"context":"business"}}
        with self.assertRaises(ValueError): self.call("profile", rule)
        self.call("profile", {**rule, "approved":True})
        request = {"source":"Report", "scope":{"context":"business"}}
        self.assertEqual(self.call("prepare", request)["preferences"]["format"], "steps first")
        self.assertEqual(self.call("prepare", {**request, "current":{"format":"paragraph"}})["preferences"]["format"], "paragraph")
        self.assertEqual(self.call("prepare", {"scope":{"context":"research"}})["preferences"], {})
        self.assertEqual(self.call("prepare", request, user="bob")["preferences"], {})
        self.assertEqual(self.call("prepare", request, host="other")["preferences"], {})
        self.call("profile", {"op":"undo"})
        self.assertEqual(self.call("prepare", request)["preferences"], {})
    def test_disable_reset_and_private_mode(self):
        self.call("profile", {"op":"disable"})
        with self.assertRaises(ValueError):
            self.call("profile", {"op":"set", "approved":True, "key":"depth", "value":"brief", "scope":{}})
        self.assertFalse(self.call("profile", {"op":"inspect"})["enabled"])
        self.call("profile", {"op":"reset"})
        result = self.call("profile", {"op":"export"})
        self.assertEqual(result["preferences"], [])
        self.assertEqual(result["feedback"], [])
        for path in self.root.rglob("*.sqlite3"):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
    def test_reject_symlink_and_bad_scope(self):
        (self.root / "link").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): c.dispatch(self.root / "link", "a", "b", "profile", {"op":"inspect"})
        with self.assertRaises(ValueError): self.call("prepare", {"scope":{"context":"../bad"}})

class ResponseTests(StorageTests):
    def capture(self, **extra):
        return self.call("capture", {"original":"Try `run()`; it may fail.", "revision":"It may fail. Try `run()`.",
            "protected":["may fail"], "meaning_checked":True, "scope":{"context":"code", "language":"en"}, **extra})
    def action(self, record, action):
        return self.call("action", {"id":record["id"], "version":record["version"], "scope":record["scope_token"], "action":action})
    def test_edit_consent_and_stale_identity(self):
        r = self.capture()
        pending = self.action(r, "steps")
        self.assertEqual(pending["pending"], "steps")
        self.assertEqual(pending["version"], 2)
        self.assertEqual(self.call("profile", {"op":"inspect"})["preferences"], [])
        with self.assertRaises(ValueError): self.action(r, "remember")
        with self.assertRaises(ValueError): self.action(pending, "helpful")
        revised = self.call("revise", {"id":r["id"], "version":pending["version"], "scope":r["scope_token"],
            "revision":"1. Try `run()`; it may fail.", "meaning_checked":True})
        self.assertEqual(revised["original"], r["original"])
        self.assertEqual(revised["version"], 3)
        with self.assertRaises(ValueError): self.action(r, "helpful")
        self.action(revised, "remember")
        self.assertEqual(self.call("prepare", {"scope":{"context":"code"}})["preferences"]["format"], "numbered steps first")
        with self.assertRaises(ValueError): self.action(revised, "remember")
    def test_injection_render_and_wrong_scope(self):
        r = self.capture(original="<script>alert(1)</script> & `x`", revision="`x` & <script>alert(1)</script>", protected=[])
        page = self.call("render", {"id":r["id"]})
        content = pathlib.Path(page["path"]).read_text()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertIn("data-hermes-send=", content)
        self.assertIn("require Hermes", content)
        with self.assertRaises(ValueError): self.call("action", {"id":r["id"], "version":1, "scope":"wrong", "action":"steps"})
        with self.assertRaises(ValueError): self.action(r, "run shell")
        with self.assertRaises(ValueError): self.call("get", {"id":"../../bad"})
    def test_failed_revision_noop_exact_and_optout(self):
        r = self.capture()
        pending = self.action(r, "shorter")
        r2 = self.call("revise", {"id":r["id"], "version":pending["version"], "scope":r["scope_token"], "revision":"Run it safely", "meaning_checked":True})
        self.assertEqual(r2["revision"], r["revision"])
        self.assertIsNone(r2["proposal"])
        self.assertEqual(self.call("capture", {"original":"{}", "exact_output":True}), {"text":"{}", "status":"bypass"})
        before = self.call("profile", {"op":"inspect"})["feedback"]
        self.call("profile", {"op":"disable"})
        self.action(r2, "helpful")
        self.assertEqual(self.call("profile", {"op":"inspect"})["feedback"], before)

class LifecycleTests(StorageTests):
    def test_reset_deletes_widgets_and_expiry_prunes(self):
        r = self.call("capture", {"original":"hello there", "revision":"there: hello", "meaning_checked":True})
        page = pathlib.Path(self.call("render", {"id":r["id"]})["path"])
        self.call("profile", {"op":"reset"})
        self.assertFalse(page.exists())
        with self.assertRaises(ValueError): self.call("get", {"id":r["id"]})
    def test_explicit_script_and_current_language(self):
        self.assertEqual(c.prepare({"source":"Hello", "scope":{"language":"zh-Hant"}}, [])["language"], "zh-Hant")
        self.assertEqual(c.prepare({"source":"你好", "current":{"language":"en"}}, [])["language"], "en")
    def test_failed_edits_not_satisfaction(self):
        r = self.call("capture", {"original":"Maybe `x`"})
        pending = self.call("action", {"id":r["id"], "version":r["version"], "scope":r["scope_token"], "action":"steps"})
        r2 = self.call("revise", {"id":r["id"], "version":pending["version"], "scope":r["scope_token"], "revision":"x", "meaning_checked":True})
        self.assertEqual(r2["revision"], "Maybe `x`")
        self.assertEqual(self.call("profile", {"op":"inspect"})["feedback"][-1]["outcome"], "fallback")

class HardenedFlowTests(StorageTests):
    def test_noop_render_has_no_controls(self):
        r = self.call("capture", {"original":"Yes."})
        result = self.call("render", {"id":r["id"]})
        self.assertIsNone(result["directive"])
        self.assertEqual(result["markdown"], "Yes.")
    def test_remember_undo_bound_to_profile_change(self):
        r = self.call("capture", {"original":"A. B."})
        envelope = {"id":r["id"], "version":r["version"], "scope":r["scope_token"]}
        pending = self.call("action", {**envelope, "action":"steps"})
        r = self.call("revise", {**envelope, "version":pending["version"], "revision":"1. A.\n2. B.", "meaning_checked":True})
        r = self.call("action", {**envelope, "version":r["version"], "action":"remember"})
        page = self.call("render", {"id":r["id"]})
        self.assertIn("Undo", pathlib.Path(page["path"]).read_text())
        self.call("action", {**envelope, "version":r["version"], "action":"undo"})
        self.assertEqual(self.call("profile", {"op":"inspect"})["preferences"], [])
    def test_invalid_state_fails_closed(self):
        import copy
        good = c.initial()
        for change in ({"enabled":"yes"}, {"schema":99}, {"undo":[{}]}, {"preferences":[{"id":"0"*32,"key":"format","value":"steps","scope":{},"approved":False}]}):
            with self.subTest(change=change):
                with self.assertRaises((ValueError, KeyError)): c.validate_state({**copy.deepcopy(good), **change})

"""Authored fixtures and deterministic CLI flows; never model-comprehension tests."""
import concurrent.futures
from html.parser import HTMLParser
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_clarity import c, ROOT

class ButtonParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.prompts = []
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for key, value in attrs:
            if key == "data-hermes-send": self.prompts.append(value)
            if key.startswith("on"): raise AssertionError("Executable event handler")

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / ".local")
        self.root = pathlib.Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def call(self, command, data): return c.dispatch(self.root, "reader", "fixture", command, data)
    def cli(self, command, data):
        result = subprocess.run([sys.executable, str(ROOT / "skills/ai-clarity/scripts/clarity.py"),
            "--root", str(self.root), "--user", "reader", "--host", "fixture", command],
            input=json.dumps(data), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)
    def test_fresh_process_all_commands_and_concurrent_writes(self):
        def save(index):
            return self.cli("profile", {"op":"set", "approved":True, "key":"format", "value":"steps",
                "scope":{"context":"business", "topic":str(index)}})
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(save, range(12)))
        self.assertEqual(len(self.cli("profile", {"op":"inspect"})["preferences"]), 12)
        self.assertEqual(self.cli("prepare", {"scope":{"context":"business", "topic":"3"}})["preferences"]["format"], "steps")
        self.assertEqual(self.cli("prepare", {"scope":{"context":"research", "topic":"3"}})["preferences"], {})
        r = self.cli("capture", {"original":"One. Two.", "revision":"One; two.", "meaning_checked":True})
        self.assertEqual(self.cli("get", {"id":r["id"]})["original"], "One. Two.")
        page = self.cli("render", {"id":r["id"]})
        pending = self.cli("action", {"id":r["id"], "version":1, "scope":r["scope_token"], "action":"steps"})
        r2 = self.cli("revise", {"id":r["id"], "version":pending["version"], "scope":r["scope_token"],
            "revision":"1. One.\n2. Two.", "meaning_checked":True})
        self.assertEqual(self.cli("render", {"id":r2["id"]})["path"], page["path"])
        self.cli("action", {"id":r2["id"], "version":r2["version"], "scope":r2["scope_token"], "action":"not_now"})
        pid = self.cli("profile", {"op":"inspect"})["preferences"][0]["id"]
        self.cli("profile", {"op":"forget", "id":pid})
        self.cli("profile", {"op":"undo"})
        self.cli("profile", {"op":"disable"})
        self.cli("profile", {"op":"enable"})
        self.assertEqual(len(self.cli("profile", {"op":"export"})["preferences"]), 12)
        self.cli("profile", {"op":"reset"})
        self.assertFalse(pathlib.Path(page["path"]).exists())
    def test_all_authored_scenarios_routing_literals_and_labels(self):
        scenarios = json.loads((ROOT / "evals/scenarios.json").read_text())["scenarios"]
        seen = set()
        for item in scenarios:
            with self.subTest(case=item["id"]):
                if item["label"] == "authored_protocol_not_executed":
                    # These are human/host evaluation protocols, not prose fixtures.
                    # Validate their shape without claiming they were executed here.
                    self.assertTrue(item["turns"])
                    self.assertTrue(all(isinstance(turn, str) for turn in item["turns"]))
                    self.assertTrue(item["qualitative_criterion"])
                    continue
                self.assertEqual(item["label"], "authored_fixture_not_model_output")
                route = self.call("prepare", {"source":item["original"], "scope":item["scope"]})
                self.assertEqual(route["scope"], item["scope"])
                self.assertEqual(c.checked(item["original"], item["original"], item["protected"], False)[1], "unchanged")
                for literal in item["protected"]:
                    candidate = item["original"].replace(literal, "", 1)
                    self.assertEqual(c.checked(item["original"], candidate, item["protected"], True)[1], "fallback")
                seen.add((item["scope"]["context"], item["scope"]["language"]))
        for context in c.CONTEXTS:
            self.assertIn((context, "en"), seen)
            self.assertIn((context, "zh-Hans"), seen)
    def test_html_envelopes_are_source_independent_and_localized(self):
        for lang in c.LANGUAGES:
            r = self.call("capture", {"original":"<img src=x onerror=alert(1)> `x`", "revision":"`x` <img src=x onerror=alert(1)>",
                "meaning_checked":True, "scope":{"context":"code", "language":lang}})
            page = self.call("render", {"id":r["id"]})
            markup = pathlib.Path(page["path"]).read_text()
            parser = ButtonParser()
            parser.feed(markup)
            self.assertNotIn("img", parser.tags)
            self.assertNotIn("script", parser.tags)
            self.assertEqual(len(parser.prompts), 14)
            for prompt in parser.prompts:
                self.assertLess(len(prompt), 500)
                envelope = json.loads(prompt.removeprefix("AI_CLARITY "))
                self.assertEqual(set(envelope), {"id", "version", "scope", "action"})
                self.assertEqual(envelope["scope"], r["scope_token"])
                self.assertNotIn("img", prompt)
            self.assertIn(c.LABELS[lang][0], markup)
            self.assertIn(c.LABELS[lang][11], markup)
    def test_scope_conflicts_override_language_neutral_and_forget(self):
        for sc, val in [({}, "brief"), ({"context":"business"}, "detailed"), ({"language":"en"}, "normal")]:
            self.call("profile", {"op":"set", "approved":True, "key":"depth", "value":val, "scope":sc})
        out = self.call("prepare", {"scope":{"context":"business"}, "language":"en"})
        self.assertEqual(out["preferences"]["depth"], "normal")
        self.assertEqual(len(out["conflicts"]), 1)
        self.assertEqual(self.call("prepare", {"scope":{"context":"business"}, "language":"zh-Hant"})["preferences"]["depth"], "detailed")
        pref = self.call("profile", {"op":"set", "approved":True, "key":"depth", "value":"full", "scope":{"context":"business"}})["preferences"][-1]
        self.assertTrue(pref["supersedes"])
        self.call("profile", {"op":"forget", "id":pref["id"]})
        self.assertEqual(self.call("prepare", {"scope":{"context":"business"}, "language":"zh-Hans"})["preferences"]["depth"], "brief")
    def test_retention_and_malformed_database(self):
        for index in range(23):
            r = self.call("capture", {"original":str(index)})
        database = next(self.root.rglob("*.sqlite3"))
        with sqlite3.connect(database) as db:
            state = json.loads(db.execute("SELECT body FROM state").fetchone()[0])
            self.assertEqual(len(state["responses"]), 20)
        with patch.object(c.time, "time", return_value=c.time.time()+86401):
            self.call("prepare", {})
        with sqlite3.connect(database) as db:
            state = json.loads(db.execute("SELECT body FROM state").fetchone()[0])
            self.assertEqual(state["responses"], {})
            db.execute("UPDATE state SET body=?", ("{bad",))
        with self.assertRaises(ValueError): self.call("prepare", {})
    def test_action_overrides_never_save_and_do_not_retarget(self):
        r = self.call("capture", {"original":"maybe"})
        for selected, value in [("language_zh-Hant", "也許"), ("context_research", "也許如此"), ("language_original", "maybe so")]:
            envelope = {"id":r["id"], "version":r["version"], "scope":r["scope_token"]}
            pending = self.call("action", {**envelope, "action":selected})
            r = self.call("revise", {**envelope, "version":pending["version"], "revision":value, "meaning_checked":True})
            self.assertIsNone(r["proposal"])
        self.assertEqual(r["scope"], {"context":"research", "language":"en"})
        self.assertEqual(self.call("profile", {"op":"inspect"})["preferences"], [])
        with self.assertRaises(ValueError): self.call("action", {**envelope, "action":"helpful"})

if __name__ == "__main__": unittest.main()

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('staging', ROOT / 'adapters/hermes/stage.py')


class StagingTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.local')
        self.home = pathlib.Path(self.temp.name) / 'home'

    def tearDown(self):
        self.temp.cleanup()

    def module(self):
        module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(module)
        return module

    def test_activate_uninstall_preserves_outside_content(self):
        module = self.module()
        module.stage(self.home, ROOT)
        soul = self.home / 'SOUL.md'
        original = b'Owner instructions\r\nKeep exact bytes.'
        soul.write_bytes(original)
        module.activate(self.home, ROOT, 'test-reader', 'test-host')
        self.assertTrue(soul.read_bytes().startswith(original))
        soul.write_bytes(soul.read_bytes() + b'\nLater owner edit')
        module.uninstall(self.home)
        self.assertEqual(soul.read_bytes(), original + b'\nLater owner edit')
        self.assertFalse((self.home / 'skills/ai-clarity').exists())

    def test_uninstall_refuses_added_empty_directory(self):
        module = self.module()
        module.stage(self.home, ROOT)
        (self.home / 'skills/ai-clarity/owner-added-empty-dir').mkdir()
        with self.assertRaises(ValueError): module.uninstall(self.home)
        self.assertTrue((self.home / 'skills/ai-clarity/SKILL.md').exists())
        shutil.rmtree(self.home / 'skills/ai-clarity/owner-added-empty-dir')
        module.uninstall(self.home)

    def test_refuses_existing_modified_and_symlinks(self):
        module = self.module()
        module.stage(self.home, ROOT)
        with self.assertRaises(ValueError):
            module.stage(self.home, ROOT)
        (self.home / 'skills/ai-clarity/SKILL.md').write_text('edited')
        with self.assertRaises(ValueError):
            module.uninstall(self.home)
        link = pathlib.Path(self.temp.name) / 'link'
        link.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(ValueError):
            module.stage(link, ROOT)

    def test_fresh_process_staging_activation_and_helper(self):
        script = str(ROOT / 'adapters/hermes/stage.py')
        for command in ('stage', 'activate'):
            result = subprocess.run([sys.executable, script, command, '--home', str(self.home),
                                     '--user', 'fixture-reader', '--host', 'fixture-hermes'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        soul = (self.home / 'SOUL.md').read_text()
        self.assertIn('before drafting/checking', soul)
        self.assertIn('fixture-reader', soul)
        helper = self.home / 'skills/ai-clarity/scripts/clarity.py'
        def helper_call(command, payload):
            completed = subprocess.run([sys.executable, str(helper), '--root',
                                       str(pathlib.Path(self.temp.name) / 'runtime'), '--user',
                                       'fixture-reader', '--host', 'fixture-hermes', command],
                                      input=json.dumps(payload), capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)
        helper_call('profile', {'op':'set', 'key':'format', 'value':'steps first',
                               'scope':{'context':'business'}, 'approved':True})
        matching = helper_call('prepare', {'source':'Explain revenue', 'scope':{'context':'business'}})
        unrelated = helper_call('prepare', {'source':'Explain evidence', 'scope':{'context':'research'}})
        self.assertEqual(matching['preferences']['format'], 'steps first')
        self.assertNotIn('format', unrelated['preferences'])
        result = subprocess.run([sys.executable, str(helper), '--root',
                                 str(pathlib.Path(self.temp.name) / 'runtime'), '--user',
                                 'fixture-reader', '--host', 'fixture-hermes', 'prepare'],
                                input='{"source":"Hello", "scope":{"context":"general"}}',
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, script, 'uninstall', '--home', str(self.home)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / 'SOUL.md').exists())

    def test_missing_source_leaves_home_untouched(self):
        source = pathlib.Path(self.temp.name) / 'incomplete'
        (source / 'skills/ai-clarity').mkdir(parents=True)
        (source / 'skills/ai-clarity/SKILL.md').write_text('incomplete')
        with self.assertRaises((ValueError, OSError)):
            self.module().stage(self.home, source)
        self.assertFalse(self.home.exists())

    def test_malformed_manifest_does_not_remove_owner_content(self):
        module = self.module()
        module.stage(self.home, ROOT)
        manifest = self.home / '.ai-clarity-install.json'
        data = json.loads(manifest.read_text())
        soul = self.home / 'SOUL.md'
        soul.write_text('Owner content')
        malformed = {**data, 'block':'Owner content', 'soul_existed':False}
        manifest.write_text(json.dumps(malformed))
        with self.assertRaises(ValueError):
            module.uninstall(self.home)
        self.assertEqual(soul.read_text(), 'Owner content')
        self.assertTrue((self.home / 'skills/ai-clarity').exists())

    def test_stage_is_self_contained_and_inactive(self):
        module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(module)
        module.stage(self.home, ROOT)
        self.assertTrue((self.home / 'skills/ai-clarity/SKILL.md').is_file())
        self.assertTrue((self.home / 'skills/ai-clarity/LICENSE').is_file())
        self.assertTrue((self.home / 'skills/ai-clarity/scripts/clarity.py').is_file())
        self.assertFalse((self.home / 'SOUL.md').exists())


if __name__ == '__main__':
    unittest.main()

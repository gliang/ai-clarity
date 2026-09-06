"""Parent review regressions: real storage and rendered behavior."""
import json
import pathlib
import tempfile
import unittest
from test_clarity import c, ROOT


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local").mkdir(exist_ok=True)

    def test_preference_offer_is_readable_in_its_output_language(self):
        expected = {
            'en': ('Use numbered steps first.', 'Code'),
            'zh-Hans': ('优先用编号步骤说明。', '代码'),
            'zh-Hant': ('優先用編號步驟說明。', '程式碼'),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as temporary:
            root = pathlib.Path(temporary)
            for language, (description, context) in expected.items():
                record = c.dispatch(root, 'test', language, 'capture', {
                    'original': 'A. B.', 'scope': {'context': 'code', 'language': language}})
                envelope = {'id': record['id'], 'version': record['version'], 'scope': record['scope_token']}
                pending = c.dispatch(root, 'test', language, 'action', {**envelope, 'action': 'steps'})
                record = c.dispatch(root, 'test', language, 'revise', {
                    **envelope, 'version': pending['version'], 'revision': '1. A.\n2. B.', 'meaning_checked': True})
                page = c.dispatch(root, 'test', language, 'render', {'id': record['id']})
                markup = pathlib.Path(page['path']).read_text()
                self.assertIn(description, markup)
                self.assertIn(context, markup)
                self.assertNotIn('&quot;key&quot;', markup)

    def test_language_override_does_not_contradict_saved_preference(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as temporary:
            root = pathlib.Path(temporary)
            c.dispatch(root, 'test', 'lang', 'profile', {'op':'set', 'approved':True,
                'key':'language', 'value':'en', 'scope':{}})
            routed = c.dispatch(root, 'test', 'lang', 'prepare',
                {'source':'Hello', 'language':'zh-Hant'})
            self.assertEqual(routed['language'], 'zh-Hant')
            self.assertEqual(routed['preferences']['language'], 'zh-Hant')

    def test_expired_text_is_pruned_even_when_next_call_fails(self):
        import sqlite3
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as temporary:
            root = pathlib.Path(temporary)
            record = c.dispatch(root, 'test', 'expiry', 'capture', {
                'original': 'secret answer text', 'revision': 'secret revised',
                'meaning_checked': True})
            page = pathlib.Path(c.dispatch(root, 'test', 'expiry', 'render', {'id': record['id']})['path'])
            database = next(root.rglob('state.sqlite3'))
            with sqlite3.connect(database) as db:
                state = json.loads(db.execute('SELECT body FROM state').fetchone()[0])
                state['responses'][record['id']]['created'] -= 86401
                db.execute('UPDATE state SET body=?', (json.dumps(state),))
            # The likely next interaction is a stale click on the expired widget,
            # which must fail without rolling the privacy cleanup back.
            with self.assertRaises(ValueError):
                c.dispatch(root, 'test', 'expiry', 'get', {'id': record['id']})
            self.assertFalse(page.exists())
            with sqlite3.connect(database) as db:
                state = json.loads(db.execute('SELECT body FROM state').fetchone()[0])
            self.assertNotIn(record['id'], state['responses'])

    def test_pending_edit_consumes_widget_version(self):
        state = c.initial()
        record = c.capture(state, {'original': 'A. B.', 'revision': 'A and B.',
                                   'meaning_checked': True})
        pending = c.action(state, {'id': record['id'], 'version': 1,
                                   'scope': record['scope_token'], 'action': 'steps'})
        self.assertEqual(pending['version'], 2)
        # The superseded v1 widget can no longer deliver satisfaction feedback.
        with self.assertRaises(ValueError):
            c.action(state, {'id': record['id'], 'version': 1,
                             'scope': record['scope_token'], 'action': 'helpful'})
        # While the edit is pending, even a correctly versioned feedback click is
        # refused instead of stranding the pending edit.
        with self.assertRaises(ValueError):
            c.action(state, {'id': record['id'], 'version': 2,
                             'scope': record['scope_token'], 'action': 'helpful'})
        revised = c.revise(state, {'id': record['id'], 'version': 2,
                                   'scope': record['scope_token'], 'revision': '1. A.\n2. B.',
                                   'meaning_checked': True})
        self.assertIsNone(revised['pending'])
        c.action(state, {'id': record['id'], 'version': revised['version'],
                         'scope': record['scope_token'], 'action': 'helpful'})

    def test_corrupted_stored_revision_fails_closed(self):
        state = c.initial()
        record = c.capture(state, {
            'original': 'Do not run `dangerous_command`.',
            'revision': 'Warning: do not run `dangerous_command`.',
            'protected': ['`dangerous_command`'],
            'meaning_checked': True,
        })
        state['responses'][record['id']]['revision'] = 'Run the operation now.'
        with self.assertRaises(ValueError):
            c.validate_state(state)

    def test_exact_capture_never_creates_storage(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as temporary:
            root = pathlib.Path(temporary) / 'must-not-exist'
            result = c.dispatch(root, 'test', 'isolated', 'capture',
                                {'original': '{"ok":true}', 'exact_output': True})
            self.assertEqual(result, {'text': '{"ok":true}', 'status': 'bypass'})
            self.assertFalse(root.exists(), 'Exact output must bypass persistent storage')

    def test_exact_prepare_does_not_load_or_create_profile(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as temporary:
            root = pathlib.Path(temporary) / 'must-not-exist'
            result = c.dispatch(root, 'test', 'isolated', 'prepare',
                                {'source': 'print(1)', 'exact_output': True})
            self.assertFalse(result['eligible'])
            self.assertEqual(result['preferences'], {})
            self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main()

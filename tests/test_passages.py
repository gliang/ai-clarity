"""Deterministic passage protocol, not semantic or browser proof."""
import copy
import pathlib
import tempfile
import unittest
from test_clarity import c, ROOT


class PassageTests(unittest.TestCase):
    def setUp(self):
        self.state = c.initial()
        (ROOT / '.local').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / '.local')
        self.addCleanup(self.tmp.cleanup)
        self.directory = pathlib.Path(self.tmp.name)

    def capture(self, **extra):
        return c.capture(self.state, dict(original='Keep this.\n\nVerbose second.',
            revision='Keep this.\n\nClear second.', meaning_checked=True, **extra))

    def test_explicit_passage_mapping_is_validated_and_reconstructs(self):
        r = self.capture(changes=[{'original':'Verbose second.', 'revision':'Clear second.'}])
        self.assertEqual(len(r['changes']), 1)
        p = r['changes'][0]
        c.opaque(p['id'])
        self.assertEqual(r['revision'][p['start']:p['end']], 'Clear second.')
        for changes in [[], [{'original':'missing', 'revision':'Clear second.'}],
                        [{'original':'', 'revision':'Clear second.'}],
                        [{'original':'Verbose second.', 'revision':' '}],
                        [{'original':'Keep this.', 'revision':'Keep this.'}],
                        [{'original':'Verbose second.', 'revision':'Clear'}],
                        [{'id':'a'*32, 'original':'Verbose second.', 'revision':'Clear second.'}],
                        [{'original':'Verbose second.', 'revision':'Clear second.'}]*2,
                        [{'original':'Verbose second.', 'revision':'Clear second.'},
                         {'original':'second.', 'revision':'second.'}]]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.capture(changes=changes)
        with self.assertRaises(ValueError):
            c.capture(self.state, {'original':'A A', 'revision':'B A', 'meaning_checked':True,
                'changes':[{'original':'A', 'revision':'B'}]})
        for original, revision, changes in [
            ('ABCDE', 'abcDE', [{'original':'ABC','revision':'abc'}, {'original':'BC','revision':'bc'}]),
            ('A B', 'b a', [{'original':'A','revision':'a'}, {'original':'B','revision':'b'}]),
            ('AAAA', 'BBAA', [{'original':'AA','revision':'BB'}]),
            ('A C', 'B B', [{'original':'A','revision':'B'}, {'original':'C','revision':'B'}])]:
            with self.subTest(original=original), self.assertRaises(ValueError):
                c.capture(self.state, dict(original=original, revision=revision, changes=changes, meaning_checked=True))

    def test_legacy_capture_uses_paragraphs_or_suppresses_controls(self):
        r = self.capture()
        self.assertEqual([p['original'] for p in r['changes']], ['Verbose second.'])
        r = c.capture(self.state, {'original':'A\n\nB', 'revision':'A plus B', 'meaning_checked':True})
        self.assertEqual(r['revision'], 'A plus B')
        self.assertEqual(r['status'], 'model-checked-unmapped')
        self.assertEqual(r['changes'], [])
        self.assertIsNone(c.render(r, self.directory)['directive'])
        c.validate_state(self.state)

    def test_widget_only_contains_changed_passage_and_opaque_controls(self):
        from test_integration import ButtonParser
        import json
        for original, revision, changes, excluded in [
            ('Keep this.\n\nVerbose second.', 'Keep this.\n\nClear second.', None, 'Keep this.'),
            ('Keep this. Verbose second.', 'Keep this. Clear second.',
             [{'original':'Verbose second.', 'revision':'Clear second.'}], 'Keep this.')]:
            data = dict(original=original, revision=revision, meaning_checked=True)
            if changes is not None: data['changes'] = changes
            r = c.capture(self.state, data)
            out = c.render(r, self.directory)
            page = pathlib.Path(out['path']).read_text()
            self.assertNotIn(excluded, page)
            self.assertNotIn(excluded, out['markdown'])
            self.assertEqual(page.count('<pre>Clear second.</pre>'), 1)
            self.assertIn('<pre>Verbose second.</pre>', page)
            parser = ButtonParser()
            parser.feed(page)
            for prompt in parser.prompts:
                envelope = json.loads(prompt[len('AI_CLARITY '):])
                self.assertEqual(envelope['passage_id'], r['changes'][0]['id'])

    def envelope(self, r, index=0):
        return dict(id=r['id'], version=r['version'], scope=r['scope_token'],
                    passage_id=r['changes'][index]['id'])

    def test_selected_passage_edit_preserves_other_bytes_and_binds_evidence(self):
        r = c.capture(self.state, {'original':'Old first.\r\n\r\nOld second.',
            'revision':'New first.\r\n\r\nNew second.', 'meaning_checked':True})
        e = self.envelope(r, 1)
        pending = c.action(self.state, dict(e, action='steps'))
        for pid in [None, 'bad', 'f'*32, r['changes'][0]['id']]:
            with self.subTest(pid=pid), self.assertRaises(ValueError):
                c.revise(self.state, dict(e, version=pending['version'], passage_id=pid,
                    revision='1. Second.', meaning_checked=True))
        updated = c.revise(self.state, dict(e, version=pending['version'],
            revision='1. Second.', meaning_checked=True))
        self.assertEqual(updated['revision'], 'New first.\r\n\r\n1. Second.')
        self.assertEqual(updated['original'], r['original'])
        self.assertEqual(updated['changes'][0], r['changes'][0])
        with self.assertRaises(ValueError): c.action(self.state, dict(e, action='helpful'))
        with self.assertRaises(ValueError):
            c.action(self.state, dict(self.envelope(updated, 0), action='remember'))
        c.action(self.state, dict(self.envelope(updated, 1), action='remember'))
        self.assertIn(e['passage_id'], self.state['preferences'][0]['evidence'])
        self.assertEqual(self.state['feedback'][-1]['passage_id'], e['passage_id'])
        c.validate_state(self.state)

    def test_persisted_passages_fail_closed_and_v1_migration_retires_widgets(self):
        import json
        import sqlite3
        r = self.capture()
        for mutate in [lambda x: x.pop('changes'),
                       lambda x: x['changes'][0].update(start=0),
                       lambda x: x['changes'][0].update(id='bad'),
                       lambda x: x.update(pending='steps', pending_passage_id='f'*32),
                       lambda x: x.update(status='fallback')]:
            broken = copy.deepcopy(self.state)
            mutate(broken['responses'][r['id']])
            with self.assertRaises((ValueError, KeyError)):
                c.validate_state(broken)
        root = self.directory / 'migration'
        c.dispatch(root, 'u', 'h', 'profile', {'op':'set', 'approved':True, 'key':'depth', 'value':'brief', 'scope':{}})
        old = c.dispatch(root, 'u', 'h', 'capture', {'original':'A', 'revision':'B', 'meaning_checked':True})
        path = pathlib.Path(c.dispatch(root, 'u', 'h', 'render', {'id':old['id']})['path'])
        database = next(root.rglob('state.sqlite3'))
        with sqlite3.connect(database) as db:
            state = json.loads(db.execute('SELECT body FROM state').fetchone()[0])
            state['schema'] = 1
            state['feedback'] = [{'id':old['id'], 'version':1, 'scope':old['scope'],
                                  'selection':'helpful', 'approved':False, 'outcome':'model-checked'}]
            for record in state['responses'].values():
                for key in ['changes', 'pending_passage_id', 'proposal_passage_id', 'undo_passage_id']:
                    record.pop(key, None)
            db.execute('UPDATE state SET body=?', (json.dumps(state),))
        out = c.dispatch(root, 'u', 'h', 'prepare', {})
        self.assertEqual(out['preferences']['depth'], 'brief')
        self.assertFalse(path.exists())
        with self.assertRaises(ValueError): c.dispatch(root, 'u', 'h', 'get', {'id':old['id']})
        with sqlite3.connect(database) as db:
            migrated = json.loads(db.execute('SELECT body FROM state').fetchone()[0])
            self.assertEqual(migrated['schema'], 2)
            self.assertIsNone(migrated['feedback'][0]['passage_id'])
            self.assertTrue(migrated['feedback'][0]['legacy_response_feedback'])
            self.assertEqual(migrated['profile_version'], state['profile_version'])
            self.assertEqual(migrated['undo'], state['undo'])

    def test_zero_passages_and_rejected_edit_never_leave_actionable_widget(self):
        r = self.capture()
        path = pathlib.Path(c.render(r, self.directory)['path'])
        for pid in [None, 'bad', 'f'*32]:
            with self.assertRaises(ValueError):
                c.action(self.state, dict(self.envelope(r), passage_id=pid, action='shorter'))
        pending = c.action(self.state, dict(self.envelope(r), action='shorter'))
        rejected = c.revise(self.state, dict(self.envelope(pending), revision='Unsafe.', meaning_checked=False))
        self.assertEqual(rejected['changes'], [])
        result = c.render(rejected, self.directory)
        self.assertIsNone(result['directive'])
        self.assertFalse(path.exists())
        self.assertEqual(result['markdown'], r['revision'])
        c.validate_state(self.state)
        r = self.capture()
        r['changes'] = []
        self.assertIsNone(c.render(r, self.directory)['path'])
        for checked in [False, True]:
            r = c.capture(self.state, {'original':'Use `x`.', 'revision':'Use x.', 'meaning_checked':checked})
            self.assertEqual(r['changes'], [])
            self.assertIsNone(c.render(r, self.directory)['path'])

    def test_reverting_passages_retires_ids_and_preserves_remaining_spans(self):
        r = c.capture(self.state, {'original':'Old first.\n\nOld second.',
            'revision':'New first.\n\nNew second.', 'meaning_checked':True})
        original = r['original']
        first_id = r['changes'][0]['id']
        p = c.action(self.state, dict(self.envelope(r), action='shorter'))
        r = c.revise(self.state, dict(self.envelope(p), revision='Old first.', meaning_checked=True))
        self.assertEqual(len(r['changes']), 1)
        self.assertEqual(r['revision'], 'Old first.\n\nNew second.')
        with self.assertRaises(ValueError): c.action(self.state, dict(self.envelope(r), passage_id=first_id, action='helpful'))
        p = c.action(self.state, dict(self.envelope(r), action='shorter'))
        r = c.revise(self.state, dict(self.envelope(p), revision='Old second.', meaning_checked=True))
        self.assertEqual(r['revision'], original)
        self.assertEqual(r['changes'], [])
        self.assertIsNone(c.render(r, self.directory)['directive'])
        c.validate_state(self.state)

    def test_first_passage_length_change_shifts_only_later_spans(self):
        r = c.capture(self.state, {'original':'A.\n\nB.', 'revision':'AA.\n\nBB.', 'meaning_checked':True})
        second_id = r['changes'][1]['id']
        p = c.action(self.state, dict(self.envelope(r), action='example'))
        r = c.revise(self.state, dict(self.envelope(p), revision='An example.', meaning_checked=True))
        self.assertEqual(r['revision'], 'An example.\n\nBB.')
        self.assertEqual(r['changes'][1]['id'], second_id)
        c.validate_state(self.state)

    def test_passage_html_is_data_and_css_inherits_paired_tokens(self):
        from test_integration import ButtonParser
        import re
        import json
        r = c.capture(self.state, {'original':'Unchanged. <script>alert(1)</script>',
            'revision':'Unchanged. <script>alert(2)</script>', 'meaning_checked':True,
            'changes':[{'original':'<script>alert(1)</script>', 'revision':'<script>alert(2)</script>'}]})
        page = pathlib.Path(c.render(r, self.directory)['path']).read_text()
        self.assertNotIn('Unchanged.', page)
        self.assertIn('&lt;script&gt;', page)
        parser = ButtonParser()
        parser.feed(page)
        self.assertNotIn('script', parser.tags)
        for prompt in parser.prompts:
            envelope = json.loads(prompt[len('AI_CLARITY '):])
            self.assertEqual(set(envelope), {'id','version','scope','passage_id','action'})
            self.assertNotIn('alert', prompt)
        match = re.search(r'<style>(.*?)</style>', page, re.S)
        assert match is not None
        style = match[1]
        def declarations(selector):
            match = re.search(r'\b' + selector + r'\{([^}]*)\}', style)
            assert match is not None
            body = match[1]
            return dict(x.split(':', 1) for x in body.split(';'))
        self.assertEqual(declarations('body')['background'], 'var(--card,#fff)')
        self.assertEqual(declarations('body')['color'], 'var(--foreground,#222)')
        self.assertEqual(declarations('button')['color'], 'inherit')
        self.assertEqual(declarations('button')['background'], 'var(--card,transparent)')
        # Both host themes supply the paired tokens; standalone buttons are
        # transparent over the white body. Structural contract, not visual proof.

    def test_new_edit_retires_old_undo_capability(self):
        r = self.capture()
        p = c.action(self.state, dict(self.envelope(r), action='steps'))
        r = c.revise(self.state, dict(self.envelope(p), revision='1. Clear second.', meaning_checked=True))
        r = c.action(self.state, dict(self.envelope(r), action='remember'))
        pending = c.action(self.state, dict(self.envelope(r), action='shorter'))
        self.assertIsNone(pending['undo_profile_version'])
        with self.assertRaises(ValueError):
            c.action(self.state, dict(self.envelope(pending), action='undo'))
        c.validate_state(self.state)

    def test_passage_offer_preserves_localized_scope_and_saved_acknowledgement(self):
        for language, language_label, saved in [('en','English','Preference saved for the displayed scope.'),
                ('zh-Hans','简体中文','已保存此范围的偏好。'), ('zh-Hant','繁體中文','已儲存此範圍的偏好。')]:
            r = self.capture(scope={'language':language})
            p = c.action(self.state, dict(self.envelope(r), action='steps'))
            r = c.revise(self.state, dict(self.envelope(p), revision='1. Second.', meaning_checked=True))
            page = c.passage_html(r, r['changes'][0])
            self.assertIn(' / ' + language_label, page)
            r = c.action(self.state, dict(self.envelope(r), action='remember'))
            self.assertIn(saved, c.passage_html(r, r['changes'][0]))

    def test_noop_has_no_widget_even_after_version_history(self):
        r = c.capture(self.state, {'original':'Yes.'})
        r['version'] = 9
        r['versions'] = [{'version':1, 'text':'Yes.'}]
        out = c.render(r, self.directory)
        self.assertIsNone(out['path'])
        self.assertIsNone(out['directive'])
        self.assertEqual(r.get('changes'), [])

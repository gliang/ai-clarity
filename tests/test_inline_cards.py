"""Inline presentation contract; synthetic data only, no live host proof."""
import pathlib
import tempfile
import unittest
from test_clarity import c, ROOT


class InlineCardsTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.local').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / '.local')
        self.addCleanup(self.tmp.cleanup)
        self.directory = pathlib.Path(self.tmp.name)
        self.state = c.initial()

    def capture(self):
        return c.capture(self.state, dict(
            original='Intro.\n\nVerbose paragraph.\n\nEnd.',
            revision='Intro.\n\nClear paragraph.\n\nEnd.', meaning_checked=True))

    def test_multiple_passages_have_distinct_cards_in_exact_byte_order(self):
        before, between, after = '标题\r\n\r\n', '\r\n \t\r\nUnchanged.\n\n', '\n\n尾部  \n'
        r = c.capture(self.state, dict(original=before + 'Old A.' + between + 'Old B.' + after,
            revision=before + 'New A.' + between + 'New B.' + after, meaning_checked=True))
        out = c.render(r, self.directory)
        cards = out.get('cards', [])
        self.assertEqual(len(cards), 2)
        self.assertNotEqual(cards[0]['path'], cards[1]['path'])
        self.assertEqual(out['inline_markdown'].encode(),
                         (before + cards[0]['directive'] + between + cards[1]['directive'] + after).encode())
        for i, card in enumerate(cards):
            page = pathlib.Path(card['path']).read_text()
            self.assertIn(r['changes'][i]['revision'], page)
            self.assertNotIn(r['changes'][1-i]['revision'], page)
        self.assertIsNone(out['directive'])  # Never offer an aggregate end widget.
        self.assertEqual(c.render(r, self.directory), out)

    def test_localized_cards_hide_routing_controls_but_backend_accepts_them(self):
        from test_integration import ButtonParser
        import json
        for lang, indicator, disclosure in [('en', 'Revised by AI Clarity', 'Show original'),
                ('zh-Hans', 'AI Clarity 已修改', '查看原文'), ('zh-Hant', 'AI Clarity 已修改', '檢視原文')]:
            r = self.capture()
            r['scope']['language'] = lang
            page = pathlib.Path(c.render(r, self.directory)['path']).read_text()
            self.assertNotIn('context_', page)
            self.assertNotIn('language_', page)
            self.assertIn(indicator, page)
            self.assertIn('<details><summary>' + disclosure, page)
            self.assertLess(page.index('<pre>Clear paragraph.'), page.index(indicator))
            parser = ButtonParser()
            parser.feed(page)
            self.assertEqual(len(parser.prompts), 5)
            for prompt in parser.prompts:
                e = json.loads(prompt[len('AI_CLARITY '):])
                self.assertEqual(e['passage_id'], r['changes'][0]['id'])
            for selection in ['context_research', 'language_zh-Hant', 'language_original']:
                e = dict(id=r['id'], version=r['version'], scope=r['scope_token'], passage_id=r['changes'][0]['id'])
                p = c.action(self.state, dict(e, action=selection))
                r = c.revise(self.state, dict(e, version=p['version'], revision='Even clearer paragraph.' + selection,
                                            meaning_checked=True))
            self.assertEqual(r['scope'], {'context':'research', 'language':'en'})
            self.assertEqual(c.prepare({'scope':{'context':'business'}, 'language':'zh-Hans'}, [])['scope'],
                             {'context':'business', 'language':'zh-Hans'})

    def test_per_passage_lifecycle_permissions_and_retirement(self):
        from test_integration import ButtonParser
        import json
        def call(cmd, data):
            return c.dispatch(self.directory, 'fixture', 'inline', cmd, data)
        r = call('capture', dict(original='Old A.\n\nOld B.', revision='New A.\n\nNew B.', meaning_checked=True))
        out = call('render', {'id':r['id']})
        paths = [pathlib.Path(card['path']) for card in out['cards']]
        for path in paths:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        def edit(record, replacement):
            envelope = dict(id=record['id'], version=record['version'], scope=record['scope_token'],
                            passage_id=record['changes'][0]['id'])
            pending = call('action', dict(envelope, action='shorter'))
            return call('revise', dict(envelope, version=pending['version'], revision=replacement, meaning_checked=True))
        r = edit(r, 'New A.')  # No-op edit keeps existing changes and paths.
        self.assertEqual([card['path'] for card in call('render', {'id':r['id']})['cards']], list(map(str, paths)))
        for path in paths:
            parser = ButtonParser()
            parser.feed(path.read_text())
            self.assertTrue(all(json.loads(x[len('AI_CLARITY '):])['version'] == r['version'] for x in parser.prompts))
        r = edit(r, 'Old A.')
        self.assertFalse(paths[0].exists(), 'Reverted passage file must be retired')
        self.assertTrue(paths[1].exists())
        r = edit(r, 'Old B.')
        out = call('render', {'id':r['id']})
        self.assertFalse(paths[1].exists())
        self.assertEqual(out['inline_markdown'], r['original'])
        self.assertEqual(out['cards'], [])

    def test_cleanup_expiry_reset_migration_and_legacy_files(self):
        from unittest.mock import patch
        import json
        import sqlite3
        for operation in ['expiry', 'reset', 'migration']:
            with self.subTest(operation=operation):
                root = self.directory / operation
                def call(cmd, data): return c.dispatch(root, 'fixture', 'inline', cmd, data)
                r = call('capture', dict(original='Old A.\n\nOld B.', revision='New A.\n\nNew B.', meaning_checked=True))
                cards = call('render', {'id':r['id']})['cards']
                directory = pathlib.Path(cards[0]['path']).parent
                legacy = directory / (r['id'] + '.html')
                legacy.write_text('obsolete aggregate')
                unrelated = directory / 'user.html'
                unrelated.write_text('keep')
                if operation == 'expiry':
                    with patch.object(c.time, 'time', return_value=c.time.time()+86401):
                        with self.assertRaises(ValueError): call('action', dict(id=r['id'], version=1,
                            scope=r['scope_token'], passage_id=r['changes'][0]['id'], action='helpful'))
                elif operation == 'reset': call('profile', {'op':'reset'})
                else:
                    with sqlite3.connect(directory / 'state.sqlite3') as db:
                        state = json.loads(db.execute('SELECT body FROM state').fetchone()[0])
                        state['schema'] = 1
                        db.execute('UPDATE state SET body=?', (json.dumps(state),))
                    call('prepare', {})
                self.assertFalse(legacy.exists())
                self.assertTrue(unrelated.exists())
                for card in cards: self.assertFalse(pathlib.Path(card['path']).exists())

    def test_sentence_cards_are_standalone_paragraphs_without_rewriting_neighbors(self):
        r = c.capture(self.state, dict(original='Keep α. Old sentence. Keep ω.',
            revision='Keep α. New sentence. Keep ω.', meaning_checked=True,
            changes=[{'original':'Old sentence.', 'revision':'New sentence.'}]))
        out = c.render(r, self.directory)
        self.assertEqual(out['inline_markdown'], 'Keep α. \n\n' + out['directive'] + '\n\n Keep ω.')
        self.assertEqual(out['inline_markdown'].split('\n\n')[1], out['directive'])

    def test_markdown_fallback_is_complete_inline_safe_and_passage_addressed(self):
        r = c.capture(self.state, dict(original='Intro.\n\nOld <script>x</script> ````.\n\nEnd.',
            revision='Intro.\n\nNew <script>x</script> ````.\n\nEnd.', meaning_checked=True))
        out = c.render(r, self.directory)
        md = out['markdown']
        self.assertTrue(md.startswith('Intro.\n\n'))
        self.assertTrue(md.endswith('\n\nEnd.'))
        self.assertEqual(md.count(r['changes'][0]['revision']), 1)
        self.assertIn('`````text\n', md)
        self.assertIn('id=' + r['id'], md)
        self.assertIn('version=1', md)
        self.assertIn('scope=' + r['scope_token'], md)
        self.assertIn('passage_id=' + r['changes'][0]['id'], md)
        self.assertIn('Shorten this passage', md)
        self.assertNotIn('::preview', md)
        self.assertNotIn('Context', md)
        self.assertNotIn('Language', md)

    def test_every_visible_button_has_full_identity_and_escaped_passage_data(self):
        from test_integration import ButtonParser
        import json
        r = c.capture(self.state, dict(original='Old <script>x</script>.\n\nOld <img onerror="x">.',
            revision='New <script>x</script>.\n\nNew <img onerror="x">.', meaning_checked=True))
        for transition in ['initial', 'revise', 'remember']:
            if transition != 'initial':
                e = dict(id=r['id'], version=r['version'], scope=r['scope_token'], passage_id=r['changes'][0]['id'])
                if transition == 'revise':
                    p = c.action(self.state, dict(e, action='steps'))
                    r = c.revise(self.state, dict(e, version=p['version'], revision='1. New <script>x</script>.', meaning_checked=True))
                else: r = c.action(self.state, dict(e, action='remember'))
            out = c.render(r, self.directory)
            for i, card in enumerate(out['cards']):
                page = pathlib.Path(card['path']).read_text()
                parser = ButtonParser()
                parser.feed(page)
                self.assertNotIn('script', parser.tags)
                self.assertNotIn('img', parser.tags)
                self.assertIn('&lt;', page)
                expected = dict(id=r['id'], version=r['version'], scope=r['scope_token'], passage_id=r['changes'][i]['id'])
                self.assertEqual(card['identity'], expected)
                self.assertTrue(parser.prompts)
                for prompt in parser.prompts:
                    e = json.loads(prompt[len('AI_CLARITY '):])
                    self.assertIn(e.pop('action'), c.ACTIONS)
                    self.assertEqual(e, expected)
                self.assertEqual(len(parser.prompts), (8 if transition == 'revise' else 6) if i == 0 and transition != 'initial' else 5)

    def test_host_instructions_require_helper_owned_inline_presentation(self):
        for name in ['skills/ai-clarity/SKILL.md', 'skills/ai-clarity/references/helper-workflow.md',
                     'adapters/hermes/instruction.md']:
            text = (ROOT / name).read_text()
            with self.subTest(file=name):
                self.assertIn('inline_markdown', text)
                self.assertIn('verbatim', text)
                self.assertNotIn('Show the complete accepted `record["revision"]` outside the widget', text)
                self.assertNotIn('The host shows the complete accepted `record["revision"]` outside the widget', text)
                self.assertNotIn('Example · Context · Language', text)

    def test_card_creation_permissions_symlink_refusal_and_cleanup_scope(self):
        from unittest.mock import patch
        import os
        r = self.capture()
        real_open = c.os.open
        modes = []
        def checked_open(path, flags, mode=0o777):
            if str(path).endswith('.tmp'):
                modes.append(mode)
                self.assertEqual(mode, 0o600)
                self.assertTrue(flags & os.O_EXCL)
            return real_open(path, flags, mode)
        with patch.object(c.os, 'open', side_effect=checked_open):
            out = c.render(r, self.directory)
        self.assertEqual(modes, [0o600])
        target = self.directory / 'unrelated.txt'
        target.write_text('keep')
        card = pathlib.Path(out['path'])
        card.unlink()
        card.symlink_to(target)
        with self.assertRaises(ValueError): c.render(r, self.directory)
        r['status'], r['changes'] = 'fallback', []
        c.render(r, self.directory)
        self.assertFalse(card.is_symlink())
        self.assertEqual(target.read_text(), 'keep')

    def test_no_cards_for_noop_unmapped_rejection_or_exact_output(self):
        for data in [dict(original='Yes.'),
                dict(original='A\n\nB', revision='Combined.', meaning_checked=True),
                dict(original='Safe.', revision='Unsafe.', meaning_checked=False)]:
            r = c.capture(self.state, data)
            out = c.render(r, self.directory)
            self.assertEqual(out['cards'], [])
            self.assertIsNone(out['directive'])
            self.assertEqual(out['inline_markdown'], r['revision'])
            self.assertEqual(out['markdown'], r['revision'])
        untouched = self.directory / 'must-not-exist'
        out = c.dispatch(untouched, 'fixture', 'inline', 'capture',
                         {'original':'{"x":1}', 'revision':'not JSON', 'exact_output':True})
        self.assertEqual(out, {'text':'{"x":1}', 'status':'bypass'})
        self.assertFalse(untouched.exists())

    def test_one_passage_replaces_revision_at_its_document_position(self):
        record = self.capture()
        out = c.render(record, self.directory)
        # Legacy host protocol duplicates the revised paragraph before an end widget.
        presentation = out.get('inline_markdown', record['revision'] + '\n\n' + out['directive'])
        self.assertEqual(presentation, 'Intro.\n\n' + out['directive'] + '\n\nEnd.')
        self.assertNotIn('Clear paragraph.', presentation)
        self.assertIn('<pre>Clear paragraph.</pre>', pathlib.Path(out['path']).read_text())

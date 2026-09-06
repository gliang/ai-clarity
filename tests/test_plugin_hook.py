"""Adapter tests; never launch Hermes or use a live reader profile."""
import importlib.util
from pathlib import Path
import unittest
import io
import json
import subprocess
from unittest.mock import patch, Mock
from contextlib import redirect_stderr


def load_hook():
    spec = importlib.util.spec_from_file_location('clarity_hook', PLUGIN)
    assert spec is not None and spec.loader is not None
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    return hook

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'adapters/hermes/plugin/ai-clarity-hook/__init__.py'


class HookTests(unittest.TestCase):
    def test_gate_conservative_defaults_and_shapes(self):
        self.assertTrue(PLUGIN.is_file(), 'hook scaffold is missing')
        hook = load_hook()
        text = 'An explanatory answer with a material limitation. ' * 15
        self.assertFalse(hook.eligible(text, 'cli', hook.DEFAULTS))
        config = dict(hook.DEFAULTS, enabled=True, platforms=['cli'])
        self.assertTrue(hook.eligible(text, 'cli', config))
        for source in ['short', '{"text": "' + 'x' * 700 + '"}',
                       '```python\n' + 'print(1)\n' * 100 + '```',
                       '    print(1)\n' * 100, '[1,2,3]',
                       text + '\n::preview{file="/tmp/a.html"}']:
            with self.subTest(source=source[:20]):
                self.assertFalse(hook.eligible(source, 'cli', config))
        self.assertFalse(hook.eligible(text, 'unknown', config))
        self.assertFalse(hook.eligible(text, 'cli', dict(config, enabled=False)))
        self.assertTrue(hook.eligible(text + '\n`literal`', 'cli', config))
        self.assertFalse(hook.eligible(text + '\n```unterminated', 'cli', config))


    def test_registration_passthrough_and_blocked_backend(self):
        hook = load_hook()
        self.assertTrue(hasattr(hook, 'register'), 'register is missing')
        ctx = Mock()
        ctx.get_config.side_effect = lambda key, default: default
        hook.register(ctx)
        name, callback = ctx.register_hook.call_args.args
        self.assertEqual(name, 'transform_llm_output')
        with patch.object(subprocess, 'run') as run:
            self.assertIsNone(callback(response_text='text' * 300, platform='cli', session_id='s'))
            self.assertIsNone(hook.Passthrough().rewrite('source', {}))
            with self.assertRaises(RuntimeError):
                hook.SubprocessOneshot().rewrite('source', {})
            run.assert_not_called()

    def test_cooldown_is_per_session_and_attempts_are_bounded(self):
        hook = load_hook()
        self.assertTrue(hasattr(hook, 'Gate'), 'stateful gate is missing')
        config = dict(hook.DEFAULTS, enabled=True, platforms=['cli'])
        gate = hook.Gate(config, clock=lambda: 10)
        text = 'An explanatory answer. ' * 40
        self.assertTrue(gate.claim(text, 'cli', 'one'))
        self.assertFalse(gate.claim(text, 'cli', 'one'))
        self.assertTrue(gate.claim(text, 'cli', 'two'))
        self.assertFalse(gate.claim(text, 'cli', ''))
        gate.clock = lambda: 131
        self.assertTrue(gate.claim(text, 'cli', 'one'))

    def test_malformed_config_fails_open(self):
        hook = load_hook()
        self.assertTrue(hasattr(hook, 'register'), 'register is missing')
        for key, value in [('enabled', 'false'), ('min_chars', -1),
                           ('platforms', 'cli'), ('code_ratio', float('nan')),
                           ('backend', 'unknown')]:
            ctx = Mock()
            ctx.get_config.side_effect = lambda k, d: value if k == key else d
            with redirect_stderr(io.StringIO()) as log:
                hook.register(ctx)
            self.assertIn('ai-clarity-hook', log.getvalue())
            callback = ctx.register_hook.call_args.args[1]
            original = 'Exact bytes\n' * 80
            self.assertIsNone(callback(response_text=original, session_id='s', platform='cli'))


    def test_failures_and_unverified_candidates_preserve_exact_response(self):
        hook = load_hook()
        original = '  Material uncertainty must remain.\n' * 30
        for failure in [subprocess.TimeoutExpired('hermes', 1),
                        subprocess.CalledProcessError(1, 'hermes', output=original),
                        RuntimeError('helper failed: ' + original), None]:
            ctx = Mock()
            config = dict(hook.DEFAULTS, enabled=True, platforms=['cli'])
            ctx.get_config.side_effect = lambda key, default: config[key]
            with patch.object(hook.Passthrough, 'rewrite', side_effect=failure,
                              return_value={'revision': 'unsafe candidate'}) as rewrite:
                hook.register(ctx)
                callback = ctx.register_hook.call_args.args[1]
                with redirect_stderr(io.StringIO()) as log:
                    replacement = callback(response_text=original, session_id='s', platform='cli')
                rewrite.assert_called_once()
                self.assertIsNone(replacement)
                delivered = replacement if isinstance(replacement, str) and replacement else original
                self.assertEqual(delivered.encode(), original.encode())
                self.assertNotIn(original, log.getvalue())
                self.assertIn('ai-clarity-hook', log.getvalue())

    def test_blocked_selection_never_spawns_or_captures(self):
        hook = load_hook()
        ctx = Mock()
        config = dict(hook.DEFAULTS, enabled=True, platforms=['desktop'], backend='subprocess-oneshot')
        ctx.get_config.side_effect = lambda key, default: config[key]
        hook.register(ctx)
        callback = ctx.register_hook.call_args.args[1]
        with patch.object(subprocess, 'run') as run, redirect_stderr(io.StringIO()):
            self.assertIsNone(callback(response_text='说明与限制。' * 150, session_id='s', platform='desktop'))
            run.assert_not_called()

    def test_mixed_languages_json_dominance_and_tilde_fences(self):
        hook = load_hook()
        config = dict(hook.DEFAULTS, enabled=True, platforms=['desktop'])
        for prose in ['说明仍有不确定性。', '說明仍有不確定性。', 'Mixed explanation 中英混合。']:
            self.assertTrue(hook.eligible(prose * 100, 'desktop', config))
        for source in ['A brief introduction.\n' + json.dumps({'value': 'x' * 1000}),
                       '~~~python\n' + 'x = 1\n' * 150 + '~~~',
                       '{broken JSON: ' + 'x' * 700]:
            self.assertFalse(hook.eligible(source, 'desktop', config))


if __name__ == '__main__':
    unittest.main()

"""Conservative Hermes activation scaffold. No inference is enabled in this build."""
import json
import math
import re
import sys
import threading
import time
from abc import ABC, abstractmethod

DEFAULTS = {
    'enabled': False,
    'backend': 'passthrough',
    'platforms': [],
    'min_chars': 600,
    'max_chars': 12000,
    'code_ratio': 0.35,
    'json_ratio': 0.35,
    'cooldown_seconds': 120,
}


def eligible(text, platform, config):
    """Pure, text-only heuristic; cannot recover a user's exact-output request."""
    if config['enabled'] is not True or platform not in config['platforms']:
        return False
    if not isinstance(text, str) or not config['min_chars'] <= len(text.strip()) <= config['max_chars']:
        return False
    if '::preview{' in text or 'AI_CLARITY' in text or text.lstrip().startswith(('{', '[')):
        return False
    try:
        json.loads(text)
        return False
    except ValueError:
        pass
    # Count balanced, matching fenced spans; ambiguous/malformed fences bypass.
    code_chars = 0
    opening = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line.rstrip('\n'))
        if opening:
            code_chars += len(line)
            if marker and marker[1][0] == opening[0] and len(marker[1]) >= len(opening) and not marker[2].strip():
                opening = None
        elif marker:
            opening = marker[1]
            code_chars += len(line)
        elif line.startswith(('    ', '\t')):
            code_chars += len(line)
    if opening or code_chars / len(text) >= config['code_ratio']:
        return False
    # Detect valid embedded JSON without interpreting its contents as instructions.
    decoder = json.JSONDecoder()
    json_chars = 0
    end = 0
    for match in re.finditer(r'[\[{]', text):
        if match.start() < end:
            continue
        try:
            _, length = decoder.raw_decode(text[match.start():])
        except ValueError:
            continue
        end = match.start() + length
        json_chars += length
    return json_chars / len(text) < config['json_ratio']


def validate_config(config):
    if type(config['enabled']) is not bool:
        raise ValueError('enabled must be boolean')
    if config['backend'] not in ('passthrough', 'subprocess-oneshot'):
        raise ValueError('unknown backend')
    if not isinstance(config['platforms'], list) or any(
            not isinstance(p, str) or not p for p in config['platforms']):
        raise ValueError('platforms must be a list of nonempty strings')
    for key in ('min_chars', 'max_chars'):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError('invalid character limit')
    if not config['min_chars'] <= config['max_chars'] <= 50000:
        raise ValueError('character range exceeds safety ceiling')
    for key in ('code_ratio', 'json_ratio', 'cooldown_seconds'):
        value = config[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('invalid numeric setting')
        if key == 'cooldown_seconds':
            if value < 0:
                raise ValueError('negative cooldown')
        elif not 0 < value <= 1:
            raise ValueError('ratio must be in (0, 1]')


class Gate:
    """Atomic in-process attempt reservation; never stores response text."""
    def __init__(self, config, clock=time.monotonic):
        validate_config(config)
        self.config = dict(config)
        self.clock = clock
        self.recent = {}
        self.lock = threading.Lock()

    def claim(self, text, platform, session_id):
        if not isinstance(session_id, str) or not session_id:
            return False
        if not eligible(text, platform, self.config):
            return False
        with self.lock:
            now = self.clock()
            cooldown = self.config['cooldown_seconds']
            self.recent = {key: stamp for key, stamp in self.recent.items()
                           if now - stamp < cooldown}
            if session_id in self.recent:
                return False
            # Refuse new sessions at capacity rather than evicting active cooldowns.
            if len(self.recent) >= 1024:
                return False
            self.recent[session_id] = now
            return True


class Rewriter(ABC):
    @abstractmethod
    def rewrite(self, source, prepared):
        """Return a checked candidate bundle, or None. Never execute source text."""


class Passthrough(Rewriter):
    def rewrite(self, source, prepared):
        return None


class SubprocessOneshot(Rewriter):
    """Reserved selector, NOT an enabled subprocess implementation.

    Hermes oneshot auto-approves tools/hooks. A timeout cannot undo side effects.
    Keep this hard-blocked until a tool-free, profile-isolated host contract exists.
    See docs/HOOK_DESIGN.md. There is intentionally no configuration escape hatch.
    """
    def rewrite(self, source, prepared):
        raise RuntimeError('subprocess-oneshot blocked: unsafe host approval contract')


def warn(error):
    # Exception messages can contain answer text / subprocess stdout / private paths.
    # Emit only the exception class; no source, session IDs, or credentials.
    try:
        print('ai-clarity-hook: bypass (' + type(error).__name__ + ')', file=sys.stderr)
    except Exception:
        pass


def register(ctx):
    """Read only namespaced settings; registering never writes host files."""
    try:
        config = {key: ctx.get_config(key, default) for key, default in DEFAULTS.items()}
        gate = Gate(config)
        backend = Passthrough() if config['backend'] == 'passthrough' else SubprocessOneshot()
    except Exception as error:
        warn(error)
        ctx.register_hook('transform_llm_output', lambda **kwargs: None)
        return

    def transform(response_text=None, session_id='', model='', platform='', **kwargs):
        try:
            if not gate.claim(response_text, platform, session_id):
                return None
            candidate = backend.rewrite(response_text, {})
            if candidate is not None:
                # No unverified candidate can reach the reader. capture/render and
                # semantic-preservation integration are deliberately NOT shipped yet.
                raise RuntimeError('rewrite delivery unavailable in this scaffold')
        except Exception as error:
            warn(error)
        return None

    ctx.register_hook('transform_llm_output', transform)

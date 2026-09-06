"""Explicit, non-destructive staging for a caller-selected Hermes home."""
import argparse
import hashlib
import json
import os
import re
import shlex
from pathlib import Path
import shutil
import tempfile

BEGIN = '<!-- BEGIN AI CLARITY -->'
END = '<!-- END AI CLARITY -->'


def safe(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('Symlink paths are not supported')
    return path


def inventory(path):
    if not path.is_dir():
        raise ValueError('Package directory is missing')
    result = {}
    for item in path.rglob('*'):
        if item.is_symlink():
            raise ValueError('Symlinks are not supported')
        if item.is_file():
            result[str(item.relative_to(path))] = hashlib.sha256(item.read_bytes()).hexdigest()
        elif item.is_dir():
            # Record empty directories too: a directory added after staging is a
            # package modification and must block verification/uninstall.
            result[str(item.relative_to(path)) + '/'] = hashlib.sha256(b'directory').hexdigest()
        else:
            raise ValueError('Only regular files and directories are supported')
    return result


def paths(home):
    home = safe(home)
    return home, safe(home / 'skills/ai-clarity'), safe(home / '.ai-clarity-install.json')


def atomic(path, content):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.ai-clarity-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def stage(home, source):
    home, target, manifest = paths(home)
    if target.exists() or manifest.exists():
        raise ValueError('Existing installation: refusing to overwrite')
    source = safe(source)
    package = safe(source / 'skills/ai-clarity')
    contents = inventory(package)
    if not {'SKILL.md', 'scripts/clarity.py'} <= contents.keys():
        raise ValueError('Skill package is incomplete')
    license_file = safe(source / 'LICENSE')
    if not license_file.is_file():
        raise ValueError('License is missing')
    license_file.read_bytes()
    home.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / 'skills/ai-clarity', target,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copyfile(source / 'LICENSE', target / 'LICENSE')
    atomic(manifest, json.dumps({'files': inventory(target), 'block': None}).encode())


def verified(home):
    home, target, manifest = paths(home)
    data = json.loads(manifest.read_text())
    validate_manifest(data)
    if inventory(target) != data['files']:
        raise ValueError('Installed files changed; preserve and review manually')
    return home, target, manifest, data


def validate_manifest(data):
    if not isinstance(data, dict) or not {'files', 'block'} <= data.keys():
        raise ValueError('Invalid installation manifest')
    if set(data) - {'files', 'block', 'soul_existed'}:
        raise ValueError('Unknown installation manifest fields')
    files = data['files']
    if not isinstance(files, dict) or not {'SKILL.md', 'scripts/clarity.py', 'LICENSE'} <= files.keys():
        raise ValueError('Incomplete installation manifest')
    for name, digest in files.items():
        if (not isinstance(name, str) or Path(name).is_absolute()
                or '..' in Path(name).parts or not isinstance(digest, str)
                or not re.fullmatch('[0-9a-f]{64}', digest)):
            raise ValueError('Invalid installation file entry')
    block = data['block']
    if block is not None:
        if (not isinstance(block, str) or type(data.get('soul_existed')) is not bool
                or not block.startswith('\n\n' + BEGIN + '\n')
                or not block.endswith('\n' + END + '\n')
                or block.count(BEGIN) != 1 or block.count(END) != 1):
            raise ValueError('Invalid activation block manifest')


def activate(home, source, user, host):
    for value in (user, host):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
            raise ValueError('User and host IDs must be 1-64 ASCII letters/digits/_/-')
    home, target, manifest, data = verified(home)
    soul = safe(home / 'SOUL.md')
    original = soul.read_bytes() if soul.exists() else b''
    if data['block'] or BEGIN.encode() in original or END.encode() in original:
        raise ValueError('Existing activation marker; refusing to overwrite')
    snippet = (source / 'adapters/hermes/instruction.md').read_text()
    helper = shlex.quote(str(target / 'scripts/clarity.py'))
    snippet = snippet.replace('{{HELPER}}', helper).replace('{{USER}}', user).replace('{{HOST}}', host)
    block = '\n\n' + BEGIN + '\n' + snippet + '\n' + END + '\n'
    updated = {**data, 'block': block, 'soul_existed': soul.exists()}
    # Record intent first so interruption cannot leave an untracked activation.
    atomic(manifest, json.dumps(updated).encode())
    atomic(soul, original + block.encode())


def uninstall(home):
    home, target, manifest, data = verified(home)
    soul = safe(home / 'SOUL.md')
    if data['block']:
        content = soul.read_bytes()
        block = data['block'].encode()
        if content.count(block) != 1:
            raise ValueError('Activation block changed or missing; preserve and review manually')
        remaining = content.replace(block, b'', 1)
        if remaining or data['soul_existed']:
            atomic(soul, remaining)
        else:
            soul.unlink()
    shutil.rmtree(target)
    manifest.unlink()
    # Runtime data lives outside the Hermes home and survives intentionally:
    # deleting a reader's preferences or feedback without a wipe request would
    # be its own data-loss bug. Point the operator at the exact controls.
    print('Uninstalled the skill package. Private reader data was NOT removed; '
          'it stays under AI_CLARITY_HOME (default ~/.local/share/ai-clarity) for '
          'each recorded user/host. To inspect: run the installed helper\'s '
          '`profile` command with {"op":"inspect"}; to delete all data for a '
          'reader, use {"op":"reset"} or remove that directory manually. '
          'Without such an invocation, stored answer text is not pruned.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stage', 'activate', 'uninstall'])
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--user')
    parser.add_argument('--host')
    args = parser.parse_args()
    try:
        source = Path(__file__).resolve().parents[2]
        if args.command == 'stage':
            stage(args.home, source)
        elif args.command == 'activate':
            if not args.user or not args.host:
                raise ValueError('Activation requires explicit --user and --host')
            activate(args.home, source, args.user, args.host)
        else:
            uninstall(args.home)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()

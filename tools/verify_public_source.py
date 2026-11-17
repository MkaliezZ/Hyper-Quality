"""Verify the tracked publication boundary. Not a complete secret or license audit."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tracked_files(root=ROOT):
    result = subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True)
    return [s.decode('utf-8') for s in result.stdout.split(b'\0') if s]


def check(root=ROOT):
    root = root.resolve()
    manifest = json.loads((root/'PUBLICATION.json').read_text(encoding='utf-8'))
    paths = tracked_files(root)
    errors = []
    blocked_parts = {'__pycache__','.venv','node_modules','runtime','evidence','cases','reports','intake','qa','snapshots','calibration','dist'}
    patterns = {
        'private-local-path': re.compile(r'[A-Za-z]:[/\\](?:Users|Codex[ ]Workspace|WSL)', re.I),
        'private-chat-storage': re.compile(r'xwechat[_]files', re.I),
        'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'github-token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
        'openai-token': re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b'),
        'aws-access-key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    }
    if not paths:
        errors.append('No tracked files; initialize and stage the reviewed public source first.')
    for name in paths:
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts or set(relative.parts)&blocked_parts:
            errors.append(name+': excluded path')
            continue
        allowed=name in manifest['allowed_root_files'] if len(relative.parts)==1 else relative.parts[0] in manifest['allowed_roots']
        if not allowed:
            errors.append(name+': not in publication allowlist')
        path=root/relative
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            errors.append(name+': missing, linked or outside checkout')
            continue
        if path.suffix.lower() in {'.zip','.exe','.dll','.db','.sqlite','.pyc'} or path.name.startswith('.env'):
            errors.append(name+': runtime/binary file')
        try:
            text=path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            errors.append(name+': unexpected non-UTF8 payload')
            continue
        for label,pattern in patterns.items():
            if pattern.search(text):
                errors.append(name+': '+label)
    required=['README.md','README.zh-CN.md','CONTRIBUTING.md','CONTRIBUTING.zh-CN.md',
              'LICENSE','LICENSE-NOTE.md','LICENSE-NOTE.zh-CN.md','THIRD_PARTY_NOTICES.md',
              'vendor/hyper-protocol/LICENSE','vendor/hyper-protocol/LICENSES/CC-BY-4.0.txt']
    errors += ['Missing tracked required file: '+p for p in required if p not in paths]
    return dict(valid=not errors,files=len(paths),errors=errors,
                scope='Tracked path allowlist, UTF8/source boundary and selected credential/private-path patterns; not a comprehensive security audit.')


if __name__=='__main__':
    result=check()
    print(json.dumps(result,ensure_ascii=False))
    raise SystemExit(0 if result['valid'] else 1)

#!/usr/bin/env python3
"""Rebrand an OpenJarvis checkout as AGI PROCESOR.

Deterministic and idempotent: running it again on an already rebranded tree changes nothing.
It renames files and directories (with ``git mv`` inside a git work tree) and rewrites text:

    display name   OpenJarvis / Jarvis          -> AGI PROCESOR
    technical name OpenJarvis (paths, agents)   -> AGI-PROCESOR
    Python package openjarvis                   -> agi_procesor
    kebab names    openjarvis-core              -> agi-procesor-core
    home folder    ~/.openjarvis                -> ~/.agi-procesor
    environment    OPENJARVIS_* / JARVIS_*      -> AGI_PROCESOR_* / AGI_*
    CLI            jarvis                       -> agi
    identifiers    JarvisConfig, OpenJarvisError -> AgiConfig, AgiProcesorError; SDK class Jarvis -> AgiProcesor
    repository     github.com/open-jarvis/OpenJarvis -> github.com/Procesordb/OpenJarvis

Kept verbatim: LICENSE, CHANGELOG.md (upstream history), BibTeX citations of the upstream paper,
and files listed in KEEP. Usage: python3 agi_procesor_rebrand.py <repo root> [--dry-run]
After merging new upstream OpenJarvis commits, run it again on the merged tree.
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tokenize

OLD = 'jarvis'  # the only literal the rules are built from

KEEP = {'LICENSE', 'CHANGELOG.md', 'NOTICE', 'scripts/rebrand/agi_procesor_rebrand.py', 'scripts/rebrand/README.md'}
SKIP_DIRS = {'.git', '.venv', 'node_modules', 'target', 'dist', '__pycache__', '.pytest_cache', '.ruff_cache'}
BINARY_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.icns', '.woff', '.woff2', '.ttf', '.otf',
              '.mp4', '.mp3', '.wav', '.pdf', '.zip', '.gz', '.tgz', '.whl', '.so', '.dll', '.exe', '.bin'}

OJ = 'open' + OLD            # openjarvis
OJC = 'Open' + OLD.capitalize()  # OpenJarvis
OJU = OJ.upper()             # OPENJARVIS
J = OLD                      # jarvis
JC = OLD.capitalize()        # Jarvis
JU = OLD.upper()             # JARVIS

DISPLAY = 'AGI PROCESOR'
TECH = 'AGI-PROCESOR'
FORK = 'Procesordb/OpenJarvis'          # the GitHub repository keeps its name until the owner renames it
PAGES = 'procesordb.github.io/OpenJarvis'

IDCH = re.compile(r'[A-Za-z0-9_]')
MARK = '\x02'  # temporary marker for the display name (fixes "a"/"an" afterwards)
TECH_EDGE = {'/', '\\', '-', '_'}


def _is_id(text, i):
    """True when text[i] is an identifier character that is not the letter of a backslash escape (\\n, \\t)."""
    if i < 0 or i >= len(text) or not IDCH.match(text[i]):
        return False
    if text[i] in 'ntr' and i > 0 and text[i - 1] == '\\':
        return False
    return True


class Placeholders:
    def __init__(self):
        self.items = []

    def put(self, value):
        self.items.append(value)
        return '\x01%d\x01' % (len(self.items) - 1)

    def restore(self, text):
        return re.sub('\x01(\\d+)\x01', lambda m: self.items[int(m.group(1))], text)


def _protect(text, ph):
    # citations of the upstream paper stay exactly as published
    text = re.sub(r'@(?:misc|article|inproceedings|software)\{[^@]*?\n\}', lambda m: ph.put(m.group(0)), text)
    text = re.sub(r'saadfalcon2026' + OJ + r'\w*', lambda m: ph.put(m.group(0)), text)
    # third-party repositories that merely contain the old name
    text = re.sub(r'youdotcom-integration/open-' + J + '-' + OJ, lambda m: ph.put(m.group(0)), text)
    # community links of the upstream project stay as they are (edited by hand where shown)
    text = re.sub(r'https?://(?:x|twitter)\.com/' + OJC + r'AI\b', lambda m: ph.put(m.group(0)), text)
    text = re.sub(r'https?://discord\.gg/\w+', lambda m: ph.put(m.group(0)), text)
    # upstream repository and docs site -> the AGI PROCESOR fork
    text = re.sub(r'open-' + J + r'\.github\.io/' + OJC, lambda m: ph.put(PAGES), text)
    text = re.sub(r'open-' + J + '/' + OJC + r'\b', lambda m: ph.put(FORK), text)
    text = re.sub(r'open-' + J + r'\.github\.io\b', lambda m: ph.put('procesordb.github.io'), text)
    text = re.sub(r'@open-' + J + '/', lambda m: ph.put('@Procesordb/'), text)
    text = re.sub(r'@' + OJC + r'AI\b', lambda m: ph.put('@YOUR_X_HANDLE'), text)
    text = re.sub(r'(github\.com/)open-' + J + '/', lambda m: m.group(1) + ph.put('Procesordb/'), text)
    text = re.sub(r'https://github\.com/' + OJ + r'\b', lambda m: ph.put('https://github.com/' + FORK), text)
    # upstream services and example addresses
    text = text.replace(OJ + '.stanford.edu', ph.put('procesor.com'))
    text = re.sub(r'\b(you|team)@' + OJ + r'\.ai\b', lambda m: ph.put(m.group(1) + '@example.com'), text)
    text = re.sub(r'\b([a-z]+)\.' + OJ + r'\.(ai|dev)\b', lambda m: ph.put(m.group(1) + '.example.com'), text)
    text = re.sub(r'(?<![\w.-])' + OJ + r'\.ai\b', lambda m: ph.put('example.com'), text)
    return text


def _clone_cd(text, ph):
    # "git clone <fork>.git && cd OpenJarvis" -> clone into agi-procesor
    pat = re.compile(r'(\x01\d+\x01\.git)((?:\s|\\n|&&|then)+)cd ' + OJC + r'\b')
    return pat.sub(lambda m: m.group(1) + ' agi-procesor' + m.group(2) + 'cd agi-procesor', text)


def _sub_ctx(text, word, repl_fn):
    out, i, n = [], 0, len(word)
    while True:
        j = text.find(word, i)
        if j < 0:
            out.append(text[i:])
            return ''.join(out)
        out.append(text[i:j])
        out.append(repl_fn(text, j, j + n))
        i = j + n


def _oj_camel(text, a, b):
    prev, nxt = (text[a - 1] if a else ''), (text[b] if b < len(text) else '')
    if _is_id(text, a - 1) and prev != '_' or (nxt and re.match(r'[A-Za-z0-9]', nxt)):
        return 'AgiProcesor'
    if prev in TECH_EDGE or nxt in TECH_EDGE or (nxt == '.' and b + 1 < len(text) and text[b + 1].isalpha()):
        return TECH
    return MARK


def _oj_lower(text, a, b):
    prev, nxt = (text[a - 1] if a else ''), (text[b] if b < len(text) else '')
    if prev == '-' or nxt == '-':
        return 'agi-procesor'
    if nxt.isupper():
        return 'agiProcesor'
    return 'agi_procesor'


_SDK_AFTER = re.compile(r'\(|\.[a-z_]|\]|`| (?:SDK|class|instance|instances|constructor|object|context manager)\b')


def _j_camel(text, a, b):
    prev, nxt = (text[a - 1] if a else ''), (text[b] if b < len(text) else '')
    if _is_id(text, a - 1) or (nxt and re.match(r'[A-Za-z0-9]', nxt)):
        return 'Agi'
    if prev == '.':
        return 'AgiProcesor'
    line_start = text.rfind('\n', 0, a) + 1
    line = text[line_start:text.find('\n', a) if text.find('\n', a) >= 0 else len(text)]
    before = text[max(0, a - 12):a]
    if (re.match(r'\s*(from\s+\S+\s+)?import\b', line) or _SDK_AFTER.match(text, b) or before.endswith('`')
            or before.endswith('-> ') or before.endswith('[')):
        return 'AgiProcesor'
    return MARK


def tx(text, prose=False):
    """Rewrite prose, strings, comments and config values."""
    if OLD not in text.lower():
        return text
    ph = Placeholders()
    text = _protect(text, ph)
    text = _clone_cd(text, ph)
    # fixed technical names
    text = text.replace('name = "' + OJ + '"', 'name = "agi-procesor"')
    text = text.replace('com.' + OJ, 'com.agiprocesor')
    text = text.replace(OJ + '://', 'agiprocesor://')
    text = re.sub(r'("schemes"\s*:\s*\[\s*")' + OJ + '"', r'\1agiprocesor"', text)
    text = re.sub(r'(?<![A-Za-z0-9_])\.' + OJ + r'(?![A-Za-z0-9_])', '.agi-procesor', text)
    text = text.replace(OJ + '.service', 'agi-procesor.service')
    text = re.sub(r'\bOpen ' + JC + r'\b', MARK, text)
    # generic rules
    text = text.replace(OJU, 'AGI_PROCESOR')
    text = _sub_ctx(text, OJC, _oj_camel)
    text = _sub_ctx(text, OJ, _oj_lower)
    text = text.replace(JU, 'AGI')
    text = _sub_ctx(text, JC, _j_camel)
    text = text.replace(J, 'agi')
    # "a AGI PROCESOR" -> "an AGI PROCESOR"
    text = re.sub(r'\b([aA]) ' + MARK, lambda m: ('an ' if m.group(1) == 'a' else 'An ') + MARK, text)
    text = re.sub(r'\b([aA]) (`?)AgiProcesor\b', lambda m: ('an ' if m.group(1) == 'a' else 'An ') + m.group(2) + 'AgiProcesor', text)
    if prose:
        text = re.sub(MARK + r"'(?=[\s,.;:)])", MARK + "'s", text)
    text = text.replace(MARK, DISPLAY)
    return ph.restore(text)


def ident(name):
    """Rewrite a code identifier (Python NAME token)."""
    if OLD not in name.lower():
        return name
    name = name.replace(OJU, 'AGI_PROCESOR')
    name = name.replace(OJC, 'AgiProcesor')
    name = re.sub(OJ + '(?=[A-Z])', 'agiProcesor', name)
    name = name.replace(OJ, 'agi_procesor')
    if name == JC:
        return 'AgiProcesor'
    return name.replace(JC, 'Agi').replace(JU, 'AGI').replace(J, 'agi')


_NAME_CTX = re.compile(r'__all__|_EXPORTS|getattr|setattr|hasattr|delattr|monkeypatch|patch\(|import_module')


def _line_of(src, i):
    a = src.rfind('\n', 0, i) + 1
    b = src.find('\n', i)
    return src[a:b if b >= 0 else len(src)]


def rewrite_python(src):
    """Identifiers via ident(), strings and comments via tx(); everything else untouched."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return tx(src), False
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    edits = []
    for t in toks:
        a = starts[t.start[0] - 1] + t.start[1]
        b = starts[t.end[0] - 1] + t.end[1]
        piece = src[a:b]
        if OLD not in piece.lower():
            continue
        kind = tokenize.tok_name[t.type]
        if kind == 'NAME':
            new = ident(piece)
        elif kind == 'STRING' and piece.strip('\'"') == JC and _NAME_CTX.search(_line_of(src, a)):
            new = piece.replace(JC, 'AgiProcesor')
        elif kind in ('STRING', 'COMMENT', 'FSTRING_MIDDLE', 'TSTRING_MIDDLE'):
            new = tx(piece, prose=kind == 'COMMENT' or piece.lstrip('rRbBuUfF').startswith(('"""', "'''")))
        else:
            continue
        if new != piece:
            edits.append((a, b, new))
    for a, b, new in reversed(edits):
        src = src[:a] + new + src[b:]
    return src, True


def rewrite_path_part(part):
    return tx(part)


def special_files(rel, text):
    if rel == 'pyproject.toml':
        text = re.sub(r'(?m)^name = "' + OJC + '"', 'name = "agi-procesor"', text)
    if rel == 'uv.lock':
        text = text.replace('name = "' + OJ + '"\nsource = { editable = "." }', 'name = "agi-procesor"\nsource = { editable = "." }')
    if rel.endswith('tauri.conf.json'):
        text = re.sub(r'"productName": "' + OJC + '"', '"productName": "' + TECH + '"', text)
    return text


def is_binary(path):
    if os.path.splitext(path)[1].lower() in BINARY_EXT:
        return True
    with open(path, 'rb') as f:
        return b'\0' in f.read(8192)


def walk(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            yield os.path.relpath(os.path.join(dp, f), root)


def main():
    root = os.path.abspath(sys.argv[1])
    dry = '--dry-run' in sys.argv
    in_git = os.path.isdir(os.path.join(root, '.git'))
    changed = renamed = 0
    # 1) contents
    for rel in sorted(walk(root)):
        if rel in KEEP or rel.replace(os.sep, '/') in KEEP:
            continue
        p = os.path.join(root, rel)
        if os.path.islink(p) or is_binary(p):
            continue
        try:
            src = open(p, encoding='utf-8', newline='').read()
        except UnicodeDecodeError:
            continue
        new = special_files(rel.replace(os.sep, '/'), src)
        if OLD in new.lower():
            if rel.endswith('.py'):
                new, ok = rewrite_python(new)
                if not ok:
                    print('note: tokenize failed, text rules used:', rel)
            else:
                new = tx(new, prose=rel.endswith(('.md', '.txt', '.rst')))
        if new != src:
            changed += 1
            if not dry:
                open(p, 'w', encoding='utf-8', newline='').write(new)
    # 2) paths, deepest first
    paths = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for name in dn + fn:
            if OLD in name.lower():
                paths.append(os.path.join(dp, name))
    for p in sorted(paths, key=lambda x: -x.count(os.sep)):
        rel = os.path.relpath(p, root).replace(os.sep, '/')
        if rel in KEEP:
            continue
        head, name = os.path.split(p)
        target = os.path.join(head, rewrite_path_part(name))
        if target == p:
            continue
        renamed += 1
        if dry:
            print('rename', os.path.relpath(p, root), '->', os.path.relpath(target, root))
            continue
        if in_git:
            r = subprocess.run(['git', '-C', root, 'mv', p, target], capture_output=True, text=True)
            if r.returncode != 0:
                os.rename(p, target)
        else:
            os.rename(p, target)
    print('files rewritten: %d, paths renamed: %d%s' % (changed, renamed, ' (dry run)' if dry else ''))


if __name__ == '__main__':
    main()

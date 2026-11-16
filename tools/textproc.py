"""Line-break handling and validation for RF4S message strings.

Message boxes show at most 3 lines; the renderer does not wrap, so every line
break is stored in the string. English wraps at ~29 em of Noto Sans CJK JP;
the PC dialogue box holds ~37 em. We wrap Spanish at TARGET_EM and allow up
to MAX_EM so a line never needs a 4th row.
"""
from __future__ import annotations

import re
from collections import Counter

TARGET_EM = 30.0
MAX_EM = 34.0
SOFT_BREAK_EM = 19.0   # an English line at least this wide before '\n' was a wrap

TOKEN = re.compile(r'＠[^＠\n]*＠')
GENDER = re.compile(r'＠‡([^＠\n]*)＠')
FORMAT = re.compile(r'%[-+ 0#]*\d*(?:\.\d+)?[sdifxXcu%]')
PRIVATE = re.compile('[\ue000-\uf8ff]')

_SAMPLE = {'しゅじんこうくん': 'Lestmmm', '姫': 'princesa', '子供ちゃん': 'Childnam', '字': '[A]'}


class Metrics:
    """Advance widths (em) from the game's own font (Noto Sans CJK JP)."""

    def __init__(self, widths: dict[int, float], fallback: float):
        self.widths = widths
        self.fallback = fallback

    def text(self, s: str) -> float:
        w = self.widths
        return sum(w.get(ord(c), self.fallback) for c in s)

    def line(self, line: str) -> float:
        return self.text(expand(line))


def expand(line: str) -> str:
    """Replace runtime tokens by a representative worst-case text."""
    def rep(m):
        t = m.group(0)[1:-1]
        if t.startswith('‡'):
            opts = t[1:].split(',')
            return max(opts, key=len)
        if t in _SAMPLE:
            return _SAMPLE[t]
        if t.startswith(('アイテム', 'マップ')):
            return 'Nombre de objeto'
        if t.startswith('カレンダー'):
            return 'Primavera 30'
        if t.startswith(('キャラ', 'その他')):
            return 'Personaje'
        if re.fullmatch(r'[０-９Ａ-Ｚ]|数字.', t):
            return '9999'
        return 'Nombrex'
    return TOKEN.sub(rep, line).replace('＋', '')


def split_hard(en: str, m: Metrics) -> list[str]:
    """Split an English string into paragraphs at its hard (non-wrap) breaks."""
    lines = en.split('\n')
    paras = [lines[0]]
    for prev, cur in zip(lines, lines[1:]):
        if m.line(prev) >= SOFT_BREAK_EM and not re.match(r'[\[<(・\-]', cur):
            paras[-1] = paras[-1].rstrip() + ' ' + cur.lstrip()
        else:
            paras.append(cur)
    return paras


def wrap_para(text: str, width: float, m: Metrics) -> list[str]:
    words = text.split(' ')
    lines, cur = [], ''
    for w in words:
        cand = w if not cur else cur + ' ' + w
        if cur and m.line(cand) > width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    lines.append(cur)
    return lines


def wrap(text: str, max_lines: int, base_width: float, max_width: float, m: Metrics) -> tuple[str, bool]:
    """Wrap hard-broken paragraphs at base_width, widening up to max_width when
    needed to respect max_lines. Returns (text, fits)."""
    paras = text.split('\n')
    width = base_width
    while True:
        out = [ln for p in paras for ln in wrap_para(p, width, m)]
        if len(out) <= max_lines or width >= max_width:
            break
        width = min(width + 0.5, max_width)
    # Avoid a lone short word on the last line when a slightly wider wrap
    # (still within max_width) saves that line.
    if len(out) > 1 and m.line(out[-1]) < 5 and width < max_width:
        wider = [ln for p in paras for ln in wrap_para(p, min(width + 3, max_width), m)]
        if len(wider) < len(out):
            out = wider
    fits = len(out) <= max_lines and all(m.line(l) <= max_width + 0.01 for l in out)
    return '\n'.join(out), fits


def tokens(s: str) -> Counter:
    c = Counter(t for t in TOKEN.findall(s) if not t.startswith('＠‡'))
    c.update(FORMAT.findall(s))
    c.update(PRIVATE.findall(s))
    return c


def problems(en: str, es: str, allow_gender: bool) -> list[str]:
    errs = []
    if tokens(en) != tokens(es):
        missing = tokens(en) - tokens(es)
        extra = tokens(es) - tokens(en)
        errs.append(f'tokens differ: missing {dict(missing)} extra {dict(extra)}')
    if en.count('＋') != es.count('＋'):
        errs.append(f'＋ highlight markers: expected {en.count("＋")}, got {es.count("＋")}')
    for g in GENDER.findall(es):
        if not allow_gender:
            errs.append('＠‡…＠ is not supported in this file')
            break
        opts = g.split(',')
        if len(opts) != 2 or not all(opts) or any(len(o.encode()) > 60 for o in opts):
            errs.append(f'bad gender token ＠‡{g}＠ (needs exactly "masc,fem")')
    stray = TOKEN.sub('', es)
    if '＠' in stray:
        errs.append('unbalanced ＠')
    if not es.strip() and en.strip():
        errs.append('empty translation')
    return errs

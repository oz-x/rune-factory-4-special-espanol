"""Regenerates mod/texto/* from the translation memory in work/ and the game files.

    python tools/build_texts.py "D:/SteamLibrary/steamapps/common/Rune Factory 4 Special"

Needs fontTools (line widths are measured with the game's Noto Sans CJK JP).
Translation memory (edit these to fix a line, then rebuild + reinstall):
    work/tr_rf3mc.json     "en\\x01fr" -> Spanish (dialogue; \\n only for structural breaks)
    work/tr_ui.json        "file\\x02en\\x01fr" -> Spanish (menus, descriptions)
    work/tr_strings.json   key -> Spanish (Localization-en.strings)
    work/glossary.json     English name -> Spanish (items, monsters, places...)
    work/nombres_cortos.json  "file\\x02en" -> shortened name where space is tight
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import mbundle  # noqa: E402
import rf4text  # noqa: E402
import textproc  # noqa: E402

WORK = os.path.join(ROOT, 'work')
OUT = os.path.join(ROOT, 'mod', 'texto')

GLOSSARY_FILES = ['rf3TxtItem_split2_1.eng', 'rf3TxtNpc_split2_1.eng', 'rf3TxtMapName.eng',
                  'rf3TxtCropName.eng', 'rf3TxtCalendar_split2_2.eng', 'rf4TxtShop_split2_2.eng',
                  'rf3TxtSkill_split2_1.eng']
UI_FILES = ['rf3TxtItem_split2_2.eng', 'rf3TxtNpc_split2_2.eng', 'rf3TxtQuest_split3_2.eng',
            'rf3TxtQuest_split3_3.eng', 'rf3TxtShopNpc_split2_2.eng', 'rf3TxtMenuCommon_split1_1.eng',
            'rf3TxtLoad.eng', 'rf3TxtTouchPocket.eng', 'rf4TxtItemParameter_split2_2.eng',
            'rf4TxtQuestRequestDetailFormat_split2_2.eng', 'rf4TxtShinkonHelp.eng',
            'rf3TxtSkill_split2_2.eng', 'rf3TxtHeroNickName.eng', 'rf3TxtTravelerName.eng',
            'rf3TxtTravelerTitleM.eng', 'rf3TxtTravelerTitleW.eng', 'rf3TxtFriendMonsterName.eng']
# Hand fixes by index (nicknames are inserted mid-sentence; the date label precedes a number).
FIXES = {
    'rf3TxtHeroNickName.eng': {
        106: 'Peque ＠しゅじんこうくん＠', 107: 'Maestro ＠しゅじんこうくん＠', 112: 'Hermano',
        114: 'Hermanito', 115: 'Hermanita', 120: 'Hermanita', 124: 'Señorita Meg',
        128: 'Hermano Dylas', 131: 'Sr. Vishnal', 135: 'Señorita Clorica', 153: 'Señorita Xiao',
        155: 'Señorita Amber', 159: 'Señorita Dolcie', 163: 'Sr. Kiel'},
    'rf3TxtLoad.eng': {19: 'Día '},
}
TECH = re.compile(r'^(BLANK.*|JP|Dummy|\(UNUSED\)|0|＠|@|\s*|DUMMY.*)$')
STRINGS_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)";', re.M)


def load(name):
    with open(os.path.join(WORK, name), encoding='utf-8') as f:
        return json.load(f)


def is_skip(e: str) -> bool:
    return e.startswith('＊') or bool(TECH.match(e)) or not re.search(r'[A-Za-z]', e)


def keep_ws(en: str, es: str) -> str:
    lead = en[:len(en) - len(en.lstrip())]
    trail = en[len(en.rstrip()):]
    return lead + es.strip() + trail


def em_max(m, s):
    return max((m.line(line) for line in s.split('\n')), default=0)


def wrap_spec(m, e, f, dialogue):
    en = '\n'.join(textproc.split_hard(e, m))
    fr = f.replace('\xa0', ' ')
    if dialogue:
        base = max(textproc.TARGET_EM, em_max(m, e), em_max(m, fr))
        return en, max(3, e.count('\n') + 1, fr.count('\n') + 1), base, max(textproc.MAX_EM, base)
    base = max(em_max(m, e), em_max(m, fr), 3)
    return en, max(e.count('\n') + 1, fr.count('\n') + 1), base, base * 1.06


def main() -> None:
    game = sys.argv[1]
    bundle_dir = os.path.join(game, 'Bundle')
    manifest = mbundle.read_manifest(os.path.join(bundle_dir, 'Manifest.plist'))
    for name in manifest:
        if os.path.exists(os.path.join(bundle_dir, name + mbundle.BACKUP_SUFFIX)):
            sys.exit('Desinstala la traducción antes de regenerar (se necesitan los textos originales).')

    def read(name):
        for bundle, files in manifest.items():
            if name in files:
                off, size, _ = files[name]
                with open(os.path.join(bundle_dir, bundle), 'rb') as f:
                    f.seek(off)
                    return f.read(size)
        raise KeyError(name)

    from fontTools.ttLib import TTCollection
    font = TTCollection(io.BytesIO(read('Noto Sans.ttc'))).fonts[0]
    cmap, hmtx, upm = font.getBestCmap(), font['hmtx'].metrics, font['head'].unitsPerEm
    m = textproc.Metrics({c: hmtx[g][0] / upm for c, g in cmap.items() if c < 0x10000}, 1.0)

    gloss, short = load('glossary.json'), load('nombres_cortos.json')
    tr_ui, tr_mc = load('tr_ui.json'), load('tr_rf3mc.json')
    tr_ui.update({k: v for k, v in load('tr_ui_forzado.json').items() if k not in tr_ui})
    os.makedirs(OUT, exist_ok=True)

    def table(name):
        return rf4text.parse(read(name)), rf4text.parse(read(name[:-4] + '.fra'))

    out = {}
    for name in GLOSSARY_FILES:
        en, _ = table(name)
        out[name] = [e if is_skip(e) or not gloss.get(e) else
                     keep_ws(e, short.get(f'{name}\u0002{e}', gloss[e])) for e in en]
    for name, dialogue in [(n, False) for n in UI_FILES] + [('rf3mc.eng', True)]:
        en, fr = table(name)
        rows = []
        for e, f in zip(en, fr):
            key = e + '\u0001' + f
            es = tr_mc.get(key) if dialogue else tr_ui.get(f'{name}\u0002{key}')
            if is_skip(e) or not es:
                rows.append(e)
            elif not dialogue and '\n' not in e and '\n' not in f:
                rows.append(keep_ws(e, es.replace('\n', ' ')))
            else:
                _, lines, base, mx = wrap_spec(m, e, f, dialogue)
                rows.append(keep_ws(e, textproc.wrap(es.strip(), lines, base, mx, m)[0]))
        out[name] = rows
    for name, fixes in FIXES.items():
        for i, v in fixes.items():
            out[name][i] = v
    for name, rows in out.items():
        with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=0)

    strings = read('Localization-en.strings').decode('utf-8')
    tr_s = load('tr_strings.json')

    def unesc(s):
        return s.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

    def esc(s):
        return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    def rep(mt):
        k, v = mt.group(1), mt.group(2)
        if k == 'str_options_language_english':
            return f'"{k}" = "Español";'
        if k in tr_s:
            return f'"{k}" = "{esc(keep_ws(unesc(v), tr_s[k]))}";'
        return mt.group(0)

    with open(os.path.join(OUT, 'Localization-en.strings'), 'w', encoding='utf-8', newline='') as f:
        f.write(STRINGS_RE.sub(rep, strings))
    print(f'{len(out) + 1} archivos generados en {OUT}')


if __name__ == '__main__':
    main()

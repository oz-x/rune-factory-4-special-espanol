"""Instala la traducción al español de Rune Factory 4 Special (sustituye el idioma inglés).

Uso:  python instalar.py ["ruta al juego"]
Para volver al inglés original:  python desinstalar.py ["ruta al juego"]
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))

import mbundle  # noqa: E402
import rf4text  # noqa: E402

DEFAULT_GAME = r'C:\Program Files (x86)\Steam\steamapps\common\Rune Factory 4 Special'
TEXT_DIR = os.path.join(HERE, 'mod', 'texto')


def game_dir() -> str:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    if not os.path.isfile(os.path.join(path, 'Bundle', 'Manifest.plist')):
        sys.exit(f'No encuentro el juego en "{path}". Pasa la carpeta del juego como argumento.')
    return path


def read_entry(bundle_dir: str, manifest, name: str) -> tuple[str, bytes]:
    for bundle, files in manifest.items():
        if name in files:
            off, size, _ = files[name]
            with open(os.path.join(bundle_dir, bundle), 'rb') as f:
                f.seek(off)
                return bundle, f.read(size)
    raise KeyError(name)


def main() -> None:
    bundle_dir = os.path.join(game_dir(), 'Bundle')
    restored = mbundle.restore(bundle_dir)
    if restored:
        print('Revirtiendo instalación anterior:', ', '.join(restored))
    manifest = mbundle.read_manifest(os.path.join(bundle_dir, 'Manifest.plist'))

    patches: dict[str, dict[str, bytes]] = {}
    for fn in sorted(os.listdir(TEXT_DIR)):
        path = os.path.join(TEXT_DIR, fn)
        if fn.endswith('.json'):
            name = fn[:-5]
            bundle, original = read_entry(bundle_dir, manifest, name)
            with open(path, encoding='utf-8') as f:
                strings = json.load(f)
            if len(strings) != len(rf4text.parse(original)):
                sys.exit(f'{name}: el juego tiene otra versión del texto; no se instala nada.')
            data = rf4text.build(strings)
        elif fn.endswith('.strings'):
            name = fn
            bundle, _ = read_entry(bundle_dir, manifest, name)
            with open(path, 'rb') as f:
                data = f.read()
        else:
            continue
        patches.setdefault(bundle, {})[name] = data

    mbundle.apply(bundle_dir, patches)

    manifest = mbundle.read_manifest(os.path.join(bundle_dir, 'Manifest.plist'))
    for bundle, files in patches.items():
        for name, data in files.items():
            if read_entry(bundle_dir, manifest, name)[1] != data:
                sys.exit(f'Verificación fallida en {name}; ejecuta desinstalar.py.')
    total = sum(len(f) for f in patches.values())
    print(f'Traducción instalada ({total} archivos). Elige "English" en las opciones de idioma del juego.')


if __name__ == '__main__':
    main()

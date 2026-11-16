"""Instala la traducción al español de Rune Factory 4 Special (sustituye el idioma inglés).

Uso:  python instalar.py ["ruta al juego"]
Para volver al inglés original:  python desinstalar.py ["ruta al juego"]
Sin ruta, busca el juego en las bibliotecas de Steam.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# PyInstaller extrae los datos en sys._MEIPASS; en el repositorio están junto al script.
DATA = getattr(sys, '_MEIPASS', HERE)
sys.path.insert(0, os.path.join(HERE, 'tools'))

import mbundle  # noqa: E402
import rf4text  # noqa: E402

GAME_FOLDER = 'Rune Factory 4 Special'
TEXT_DIR = os.path.join(DATA, 'mod', 'texto')


class InstallError(Exception):
    pass


def is_game(path: str) -> bool:
    return os.path.isfile(os.path.join(path, 'Bundle', 'Manifest.plist'))


def steam_libraries() -> list[str]:
    roots = []
    try:
        import winreg
        for hive, key, value in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                                 (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath')):
            try:
                with winreg.OpenKey(hive, key) as k:
                    roots.append(winreg.QueryValueEx(k, value)[0])
            except OSError:
                pass
    except ImportError:
        pass
    roots.append(r'C:\Program Files (x86)\Steam')
    libs = []
    for root in roots:
        libs.append(root)
        vdf = os.path.join(root, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            with open(vdf, encoding='utf-8', errors='replace') as f:
                libs += [p.replace('\\\\', '\\') for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    return list(dict.fromkeys(os.path.normpath(p) for p in libs))


def find_game() -> str | None:
    for lib in steam_libraries():
        path = os.path.join(lib, 'steamapps', 'common', GAME_FOLDER)
        if is_game(path):
            return path
    return None


def read_entry(bundle_dir: str, manifest, name: str) -> tuple[str, bytes]:
    for bundle, files in manifest.items():
        if name in files:
            off, size, _ = files[name]
            with open(os.path.join(bundle_dir, bundle), 'rb') as f:
                f.seek(off)
                return bundle, f.read(size)
    raise KeyError(name)


def install(game: str) -> str:
    if not is_game(game):
        raise InstallError(f'No encuentro Rune Factory 4 Special en "{game}".')
    bundle_dir = os.path.join(game, 'Bundle')
    mbundle.restore(bundle_dir)
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
                raise InstallError(f'{name}: el juego tiene otra versión del texto; no se ha instalado nada.')
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
                mbundle.restore(bundle_dir)
                raise InstallError(f'Verificación fallida en {name}; se ha restaurado el juego original.')
    total = sum(len(f) for f in patches.values())
    return f'Traducción instalada ({total} archivos).\nEn el juego, elige "Español" (antes "English") como idioma.'


def uninstall(game: str) -> str:
    if not is_game(game):
        raise InstallError(f'No encuentro Rune Factory 4 Special en "{game}".')
    restored = mbundle.restore(os.path.join(game, 'Bundle'))
    return 'Juego restaurado al original.' if restored else 'No había ninguna traducción instalada.'


def game_from_args() -> str:
    game = sys.argv[1] if len(sys.argv) > 1 else find_game()
    if not game:
        sys.exit('No encuentro el juego. Pasa la carpeta del juego como argumento.')
    return game


def main() -> None:
    try:
        print(install(game_from_args()))
    except InstallError as e:
        sys.exit(str(e))


if __name__ == '__main__':
    main()

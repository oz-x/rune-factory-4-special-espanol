"""Restaura los archivos originales (inglés) de Rune Factory 4 Special.

Uso:  python desinstalar.py ["ruta al juego"]
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))

import mbundle  # noqa: E402
from instalar import game_dir  # noqa: E402


def main() -> None:
    restored = mbundle.restore(os.path.join(game_dir(), 'Bundle'))
    print('Restaurado: ' + ', '.join(restored) if restored else 'No había ninguna traducción instalada.')


if __name__ == '__main__':
    main()

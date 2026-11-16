"""RF4S 'TEXT' string tables (rf3mc.*, rf3Txt*.*, rf4Txt*.*).

Layout (little endian): b'TEXT', u32 count, count * (u32 byte_length, u32 offset),
then the UTF-8 strings, each followed by a NUL byte.
"""
from __future__ import annotations

import struct


def parse(data: bytes) -> list[str]:
    if data[:4] != b'TEXT':
        raise ValueError('not a TEXT table')
    n = struct.unpack_from('<I', data, 4)[0]
    out = []
    for i in range(n):
        length, off = struct.unpack_from('<II', data, 8 + 8 * i)
        out.append(data[off:off + length].decode('utf-8'))
    return out


def build(strings: list[str]) -> bytes:
    head = bytearray(b'TEXT' + struct.pack('<I', len(strings)))
    body = bytearray()
    base = 8 + 8 * len(strings)
    for s in strings:
        raw = s.encode('utf-8')
        head += struct.pack('<II', len(raw), base + len(body))
        body += raw + b'\0'
    return bytes(head + body)

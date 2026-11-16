"""Reader/patcher for Rune Factory 4 Special .mbundle archives and Manifest.plist.

Every .mbundle and Bundle/Manifest.plist is a binary plist (bplist00). The game's
writer stores `top` as (root object offset - 8) and the root as the last object;
the trailer is otherwise standard:
    6 unused, u8 offset_int_size, u8 object_ref_size,
    u64be num_objects, u64be top, u64be offset_table_offset

An .mbundle root dict maps file name -> data. The game does NOT read that dict:
it locates files through Manifest.plist:
    {bundles: [{bundleName, files: {name: {offset, size}}}]}
where offset is the absolute file position of the data bytes.

Patching never rewrites the 4.7 GB archive. Replacement data is appended where
the bundle's offset table used to start, the offset table + trailer are written
after it, and the matching Manifest entries are redirected by appending new
integer objects and rewriting the two value refs inside each file's
{offset, size} dict in place. Backups (<file>.es_backup) allow byte-exact restore.
"""
from __future__ import annotations

import os
import shutil
import struct

BACKUP_SUFFIX = '.es_backup'


class Plist:
    """Lazy reader over the object table of a bplist00 file."""

    def __init__(self, path: str):
        self.path = path
        self.f = open(path, 'rb')
        if self.f.read(8) != b'bplist00':
            raise ValueError(f'{path}: not a bplist00 file')
        self.f.seek(-32, 2)
        t = self.f.read(32)
        self.osz, self.rsz = t[6], t[7]
        self.nobj, self.top, self.offtab = struct.unpack('>QQQ', t[8:])
        self.f.seek(self.offtab)
        raw = self.f.read(self.osz * self.nobj)
        o = self.osz
        self.offs = [int.from_bytes(raw[i:i + o], 'big') for i in range(0, len(raw), o)]

    def close(self):
        self.f.close()

    def header(self, i: int) -> tuple[int, int, int]:
        """(type nibble, count, payload position) of object i."""
        f = self.f
        f.seek(self.offs[i])
        m = f.read(1)[0]
        kind, n = m >> 4, m & 15
        if n == 15 and kind not in (0, 1, 2, 3):
            b = f.read(1)[0]
            n = int.from_bytes(f.read(1 << (b & 15)), 'big')
        return kind, n, f.tell()

    def refs(self, i: int) -> tuple[int, list[int], int]:
        """(type, refs, position of first ref) for array/dict object i."""
        kind, n, pos = self.header(i)
        cnt = 2 * n if kind == 0xD else n
        self.f.seek(pos)
        r = self.f.read(cnt * self.rsz)
        s = self.rsz
        return kind, [int.from_bytes(r[j:j + s], 'big') for j in range(0, len(r), s)], pos

    def value(self, i: int):
        kind, n, pos = self.header(i)
        self.f.seek(pos)
        if kind == 1:
            return int.from_bytes(self.f.read(1 << n), 'big', signed=(n == 3))
        if kind == 5:
            return self.f.read(n).decode('ascii')
        if kind == 6:
            return self.f.read(2 * n).decode('utf-16-be')
        raise ValueError(f'object {i}: type {kind:#x} is not a scalar')

    def dict_items(self, i: int) -> list[tuple[int, int]]:
        kind, refs, _ = self.refs(i)
        if kind != 0xD:
            raise ValueError(f'object {i} is not a dict')
        n = len(refs) // 2
        return list(zip(refs[:n], refs[n:]))

    def root(self) -> int:
        """The writer stores `top` as the root dict's offset - 8."""
        return self.offs.index(self.top + 8)


def read_manifest(path: str) -> dict[str, dict[str, tuple[int, int, int]]]:
    """bundleName -> {file name -> (offset, size, object index of the {offset,size} dict)}."""
    p = Plist(path)
    try:
        top = {p.value(k): v for k, v in p.dict_items(p.root())}
        kind, bundle_refs, _ = p.refs(top['bundles'])
        out = {}
        for b in bundle_refs:
            fields = {p.value(k): v for k, v in p.dict_items(b)}
            files = {}
            for k, v in p.dict_items(fields['files']):
                entry = {p.value(a): p.value(c) for a, c in p.dict_items(v)}
                files[p.value(k)] = (entry['offset'], entry['size'], v)
            out[p.value(fields['bundleName'])] = files
        return out
    finally:
        p.close()


def _int_object(v: int) -> bytes:
    if v < 0:
        return b'\x13' + v.to_bytes(8, 'big', signed=True)
    for marker, size in ((0x10, 1), (0x11, 2), (0x12, 4)):
        if v < 1 << (8 * size):
            return bytes([marker]) + v.to_bytes(size, 'big')
    return b'\x13' + v.to_bytes(8, 'big', signed=True)


def _write_tail(f, p: Plist, pos: int, blob: bytes, offs: list[int], top: int | None = None) -> None:
    new_offtab = pos + len(blob)
    if new_offtab >= 1 << (8 * p.osz):
        raise OverflowError('offsets no longer fit the offset table width')
    table = b''.join(o.to_bytes(p.osz, 'big') for o in offs)
    top = p.top if top is None else top
    trailer = bytes(6) + bytes([p.osz, p.rsz]) + struct.pack('>QQQ', len(offs), top, new_offtab)
    f.seek(pos)
    f.write(blob)
    f.write(table)
    f.write(trailer)
    f.truncate()


def _backup_tail(path: str, offtab: int) -> None:
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        f.seek(offtab)
        tail = f.read()
    with open(path + BACKUP_SUFFIX, 'wb') as f:
        f.write(struct.pack('<QQ', size, offtab))
        f.write(tail)


def _restore_tail(path: str) -> bool:
    bp = path + BACKUP_SUFFIX
    if not os.path.exists(bp):
        return False
    with open(bp, 'rb') as f:
        orig_size, offtab = struct.unpack('<QQ', f.read(16))
        tail = f.read()
    if offtab + len(tail) != orig_size:
        raise ValueError(f'{bp}: corrupt backup')
    # Patching only ever appends. A file that is not larger than the original
    # was replaced (Steam update / integrity check): the backup is stale.
    if os.path.getsize(path) <= orig_size:
        os.remove(bp)
        return False
    with open(path, 'r+b') as f:
        f.seek(offtab)
        f.write(tail)
        f.truncate(orig_size)
    os.remove(bp)
    return True


def _append_bundle_data(path: str, files: dict[str, bytes], manifest_files) -> dict[str, tuple[int, int]]:
    """Append data objects to a bundle; returns name -> (data offset, size)."""
    p = Plist(path)
    try:
        index = {p.value(k): v for k, v in p.dict_items(p.root())}
        missing = [n for n in files if n not in index or n not in manifest_files]
        if missing:
            raise KeyError(f'{os.path.basename(path)} lacks {missing}')
        _backup_tail(path, p.offtab)
        offs = list(p.offs)
        blob = bytearray()
        placed = {}
        for name, data in files.items():
            offs[index[name]] = p.offtab + len(blob)
            blob += b'\x4f\x13' + len(data).to_bytes(8, 'big')
            placed[name] = (p.offtab + len(blob), len(data))
            blob += data
        with open(path, 'r+b') as f:
            _write_tail(f, p, p.offtab, bytes(blob), offs)
        return placed
    finally:
        p.close()


def _redirect_manifest(path: str, entries: list[tuple[int, int, int]]) -> None:
    """entries: (object index of {offset,size} dict, new offset, new size)."""
    p = Plist(path)
    try:
        # The root must stay the last object (and `top` its offset - 8): new
        # objects take over the root's index and a copy of the root goes last.
        root = p.root()
        if root != p.nobj - 1:
            raise ValueError('manifest root is not the last object; restore it first')
        kind, n, pos = p.header(root)
        p.f.seek(p.offs[root])
        root_raw = p.f.read(pos - p.offs[root] + 2 * n * p.rsz)
        offs = p.offs[:root]
        blob = bytearray()
        writes = []
        for obj, off, size in entries:
            kind, refs, pos = p.refs(obj)
            n = len(refs) // 2
            keys = [p.value(k) for k in refs[:n]]
            new_refs = list(refs)
            for key, val in (('offset', off), ('size', size)):
                offs.append(p.offtab + len(blob))
                blob += _int_object(val)
                new_refs[n + keys.index(key)] = len(offs) - 1
            writes.append((pos, b''.join(r.to_bytes(p.rsz, 'big') for r in new_refs)))
        root_off = p.offtab + len(blob)
        offs.append(root_off)
        blob += root_raw
        if len(offs) >= 1 << (8 * p.rsz):
            raise OverflowError('object refs no longer fit')
        with open(path, 'r+b') as f:
            for pos, raw in writes:
                f.seek(pos)
                f.write(raw)
            _write_tail(f, p, p.offtab, bytes(blob), offs, top=root_off - 8)
    finally:
        p.close()


def restore(bundle_dir: str) -> list[str]:
    """Undo every patch in a game's Bundle directory. Returns restored file names."""
    done = []
    man = os.path.join(bundle_dir, 'Manifest.plist')
    if os.path.exists(man + BACKUP_SUFFIX):
        if os.path.getsize(man) > os.path.getsize(man + BACKUP_SUFFIX):
            shutil.copyfile(man + BACKUP_SUFFIX, man)
            done.append('Manifest.plist')
        os.remove(man + BACKUP_SUFFIX)
    for name in sorted(os.listdir(bundle_dir)):
        if name.endswith('.mbundle') and _restore_tail(os.path.join(bundle_dir, name)):
            done.append(name)
    return done


def apply(bundle_dir: str, patches: dict[str, dict[str, bytes]]) -> None:
    """patches: bundle file name -> {entry name -> new bytes}. Restores old patches first."""
    restore(bundle_dir)
    man = os.path.join(bundle_dir, 'Manifest.plist')
    manifest = read_manifest(man)
    shutil.copyfile(man, man + BACKUP_SUFFIX)
    entries = []
    for bundle, files in patches.items():
        placed = _append_bundle_data(os.path.join(bundle_dir, bundle), files, manifest[bundle])
        for name, (off, size) in placed.items():
            entries.append((manifest[bundle][name][2], off, size))
    _redirect_manifest(man, entries)

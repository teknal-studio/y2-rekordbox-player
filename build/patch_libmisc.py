#!/usr/bin/env python3
"""Replace files inside Rockbox's resource archive, /system/lib/libmisc.so.

libmisc.so is a zip of the .rockbox tree (themes, fonts, plugins) that Rockbox
unpacks onto the Y2. make_rom.py writes files in place, so the result must keep
the original's number of 4 KiB blocks: every other entry is copied byte for
byte, the replaced ones are deflated again, and when the result is smaller the
zip comment pads it back to the original length.

usage: patch_libmisc.py libmisc.orig libmisc.patched NAME=FILE [NAME=FILE ...]
  e.g. .rockbox/wps/MacClassic-Dark.wps=themes/MacClassic-Dark-Y2DJ.wps
"""
import os
import struct
import sys
import zlib

EOCD = b'PK\x05\x06'
CEN = b'PK\x01\x02'
LOC = b'PK\x03\x04'
BLOCK = 4096  # ext4 block size of the Y2 system image


def deflate(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()


def entries(zip_bytes):
    """Central directory records: (name, fields, extra, comment)."""
    eocd = zip_bytes.rfind(EOCD)
    assert eocd >= 0, 'not a zip'
    _, disk, _, n, total, size, offset, clen = struct.unpack_from('<4sHHHHIIH', zip_bytes, eocd)
    assert disk == 0 and n == total, 'multi-disk zips are not supported'
    out, pos = [], offset
    for _ in range(n):
        assert zip_bytes[pos:pos + 4] == CEN
        f = list(struct.unpack_from('<4sHHHHHHIIIHHHHHII', zip_bytes, pos))
        nlen, xlen, clen_ = f[10], f[11], f[12]
        name = zip_bytes[pos + 46:pos + 46 + nlen]
        extra = zip_bytes[pos + 46 + nlen:pos + 46 + nlen + xlen]
        comment = zip_bytes[pos + 46 + nlen + xlen:pos + 46 + nlen + xlen + clen_]
        out.append((name, f, extra, comment))
        pos += 46 + nlen + xlen + clen_
    return out


def replace(orig, files):
    """orig with files {name: data} replaced; the same length as orig."""
    files = {k.encode() if isinstance(k, str) else k: v for k, v in files.items()}
    records = entries(orig)
    missing = set(files) - {r[0] for r in records}
    assert not missing, f'not in the archive: {sorted(missing)}'

    body, central = bytearray(), bytearray()
    for name, f, extra, comment in records:
        flags, method, csize, lofs = f[3], f[4], f[8], f[16]
        assert not flags & 0x08, 'data descriptors are not supported'
        assert orig[lofs:lofs + 4] == LOC
        lnlen, lxlen = struct.unpack_from('<HH', orig, lofs + 26)
        if name in files:
            data = files[name]
            comp = deflate(data)
            f[4], f[7], f[8], f[9] = 8, zlib.crc32(data), len(comp), len(data)
            local = struct.pack('<4sHHHHHIIIHH', LOC, f[2], flags, 8, f[5], f[6],
                                f[7], f[8], f[9], len(name), 0) + name
        else:
            comp = orig[lofs + 30 + lnlen + lxlen:lofs + 30 + lnlen + lxlen + csize]
            local = orig[lofs:lofs + 30 + lnlen + lxlen]
        f[16] = len(body)
        body += local + comp
        central += struct.pack('<4sHHHHHHIIIHHHHHII', *f) + name + extra + comment

    eocd = orig.rfind(EOCD)
    n = len(records)
    old_comment = orig[eocd + 22:]
    base = len(body) + len(central) + 22 + len(old_comment)
    blocks = lambda size: -(-size // BLOCK)
    if blocks(base) != blocks(len(orig)):
        raise ValueError(f'patched archive needs {blocks(base)} blocks, the original '
                         f'{blocks(len(orig))}: make_rom.py can only replace it in place')
    # Pad back to the original length when smaller, so nothing else changes.
    pad = max(0, len(orig) - base)
    if pad + len(old_comment) > 0xFFFF:
        raise ValueError('size difference too big for the zip comment')
    comment = old_comment + b'\0' * pad
    end = struct.pack('<4sHHHHIIH', EOCD, 0, 0, n, n, len(central), len(body), len(comment))
    return bytes(body + central + end + comment)


def main():
    src, dst, *pairs = sys.argv[1:]
    if not pairs:
        raise SystemExit(__doc__)
    files = {}
    for pair in pairs:
        name, path = pair.split('=', 1)
        with open(path, 'rb') as f:
            files[name] = f.read()
    with open(src, 'rb') as f:
        orig = f.read()
    with open(dst, 'wb') as f:
        f.write(replace(orig, files))
    print(f'replaced {len(files)} file(s) in {dst}: {len(orig)} -> {os.path.getsize(dst)} bytes')


if __name__ == '__main__':
    main()

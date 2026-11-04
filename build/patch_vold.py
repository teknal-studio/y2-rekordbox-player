#!/usr/bin/env python3
"""Present the microSD as the first USB drive (LUN 0), internal storage second.

vold picks a sysfs LUN file by volume: the primary volume (internal) gets
lun/file and everything else gets lun1/file. Hosts that only look at the first
LUN therefore never see the card. shareVolume and unshareVolume each load those
two paths through a PC-relative literal, so swapping the four literals swaps
the slots without touching any instruction. The file size does not change.

usage: patch_vold.py vold.orig vold.patched
"""
import hashlib
import struct
import sys

LUN0 = b"/sys/class/android_usb/android0/f_mass_storage/lun/file\0"
LUN1 = b"/sys/class/android_usb/android0/f_mass_storage/lun1/file\0"
ADD_R0_PC = 0x4478

# (literal offset, offset of its "add r0, pc", path it loads today)
SITES = [
    (0x4E6C, 0x4D1C, LUN0),  # shareVolume, primary
    (0x4E78, 0x4D44, LUN1),  # shareVolume, secondary
    (0x50C8, 0x4F6E, LUN0),  # unshareVolume, primary
    (0x50D4, 0x4F96, LUN1),  # unshareVolume, secondary
]
ORIG_SHA256 = "7e07a24814f42a7b2d38b05481eb372202a5257e62637cfbd0d42e90f0fccc0f"


def patch(orig, sites=SITES):
    """Return orig with the LUN literals swapped."""
    data = bytearray(orig)
    assert data.count(LUN0) == 1 and data.count(LUN1) == 1
    addr = {LUN0: data.find(LUN0), LUN1: data.find(LUN1)}
    other = {LUN0: LUN1, LUN1: LUN0}

    for lit, add, path in sites:
        assert struct.unpack_from("<H", data, add)[0] == ADD_R0_PC, hex(add)
        pc = add + 4
        assert pc + struct.unpack_from("<I", data, lit)[0] == addr[path], hex(lit)
        struct.pack_into("<I", data, lit, addr[other[path]] - pc)

    for lit, add, path in sites:
        pc = add + 4
        assert pc + struct.unpack_from("<I", data, lit)[0] == addr[other[path]]
    return bytes(data)


def main():
    src, dst = sys.argv[1:3]
    orig = open(src, "rb").read()
    assert hashlib.sha256(orig).hexdigest() == ORIG_SHA256, "unexpected vold"
    data = patch(orig)

    with open(dst, "wb") as f:
        f.write(data)
    print("patched 4 literals, sha256", hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()

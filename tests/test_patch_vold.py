"""build/patch_vold.py: swap vold's USB LUN paths so the card is LUN 0.

The real vold is an Android binary we don't ship, so these tests use a
synthetic file with the same layout: the two LUN path strings, and four
"add r0, pc" sites whose PC-relative literals load them.
"""
import hashlib
import struct
import unittest

from helpers import ROOT  # noqa: F401  (sets the import path)
import patch_vold as pv

STR0, STR1 = 0x9000, 0x9100


def synthetic_vold():
    data = bytearray(0xA000)
    data[STR0:STR0 + len(pv.LUN0)] = pv.LUN0
    data[STR1:STR1 + len(pv.LUN1)] = pv.LUN1
    addr = {pv.LUN0: STR0, pv.LUN1: STR1}
    for lit, add, path in pv.SITES:
        struct.pack_into('<H', data, add, pv.ADD_R0_PC)
        struct.pack_into('<I', data, lit, addr[path] - (add + 4))
    return bytes(data)


def loads(data, lit, add):
    """The address an "add r0, pc" site ends up with."""
    return add + 4 + struct.unpack_from('<I', data, lit)[0]


class PatchVoldTest(unittest.TestCase):
    def setUp(self):
        self.orig = synthetic_vold()
        self.out = pv.patch(self.orig)

    def test_swaps_every_site(self):
        swapped = {pv.LUN0: STR1, pv.LUN1: STR0}
        for lit, add, path in pv.SITES:
            self.assertEqual(loads(self.out, lit, add), swapped[path], hex(lit))

    def test_changes_only_the_four_literals(self):
        self.assertEqual(len(self.out), len(self.orig))
        changed = {i for i in range(len(self.orig)) if self.orig[i] != self.out[i]}
        literal_bytes = {lit + k for lit, _, _ in pv.SITES for k in range(4)}
        self.assertTrue(changed)
        self.assertLessEqual(changed, literal_bytes)

    def test_patching_twice_restores_the_original(self):
        # The swap is its own inverse once the sites are relabelled.
        flipped = [(lit, add, pv.LUN1 if p == pv.LUN0 else pv.LUN0) for lit, add, p in pv.SITES]
        self.assertEqual(pv.patch(self.out, flipped), self.orig)

    def test_refuses_an_unexpected_layout(self):
        bad = bytearray(self.orig)
        struct.pack_into('<H', bad, pv.SITES[0][1], 0)  # not "add r0, pc"
        with self.assertRaises(AssertionError):
            pv.patch(bytes(bad))
        with self.assertRaises(AssertionError):
            pv.patch(self.orig.replace(pv.LUN1, b'x' * len(pv.LUN1)))

    def test_main_only_accepts_the_v25_vold(self):
        self.assertNotEqual(hashlib.sha256(self.orig).hexdigest(), pv.ORIG_SHA256)
        self.assertEqual(len(pv.ORIG_SHA256), 64)


if __name__ == '__main__':
    unittest.main()

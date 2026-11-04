"""build/patch_libmisc.py: replace files in Rockbox's resource archive in place."""
import io
import os
import random
import unittest
import zipfile

from helpers import ROOT
import patch_libmisc as pl

THEME = os.path.join(ROOT, 'themes', 'MacClassic-Dark-Y2DJ.wps')
NAME = '.rockbox/wps/MacClassic-Dark.wps'


def archive(theme=b'stock theme ' * 200, comment=b''):
    """A small libmisc-like zip: deflated and stored entries, and a folder."""
    rnd = random.Random(1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('.rockbox/wps/MacClassic-Dark/', b'')
        z.writestr(NAME, theme, zipfile.ZIP_DEFLATED)
        z.writestr('.rockbox/fonts/a.fnt', bytes(rnd.randrange(256) for _ in range(9000)),
                   zipfile.ZIP_STORED)
        z.writestr('.rockbox/viewers.config', b'viewer config\n' * 50, zipfile.ZIP_DEFLATED)
        z.comment = comment
    return buf.getvalue()


def raw_entries(data):
    """{name: (local header + data bytes)} for comparing entries byte for byte."""
    out = {}
    for name, f, _, _ in pl.entries(data):
        ofs = f[16]
        nlen, xlen = int.from_bytes(data[ofs + 26:ofs + 28], 'little'), \
            int.from_bytes(data[ofs + 28:ofs + 30], 'little')
        out[name] = data[ofs + 30 + nlen + xlen:ofs + 30 + nlen + xlen + f[8]]
    return out


class PatchLibmiscTest(unittest.TestCase):
    def setUp(self):
        self.orig = archive()

    def test_replaces_the_theme(self):
        out = pl.replace(self.orig, {NAME: b'new theme'})
        z = zipfile.ZipFile(io.BytesIO(out))
        self.assertIsNone(z.testzip())
        self.assertEqual(z.read(NAME), b'new theme')
        self.assertEqual(z.getinfo(NAME).compress_type, zipfile.ZIP_DEFLATED)

    def test_other_entries_are_copied_byte_for_byte(self):
        out = pl.replace(self.orig, {NAME: b'new theme'})
        before, after = raw_entries(self.orig), raw_entries(out)
        self.assertEqual(list(before), list(after))
        for name in before:
            if name != NAME.encode():
                self.assertEqual(before[name], after[name], name)

    def test_smaller_result_is_padded_to_the_same_length(self):
        out = pl.replace(self.orig, {NAME: b'tiny'})
        self.assertEqual(len(out), len(self.orig))
        self.assertIsNone(zipfile.ZipFile(io.BytesIO(out)).testzip())

    def test_bigger_result_stays_in_the_same_blocks(self):
        # Fill the last block nearly full so there is little room to grow.
        n = len(self.orig)
        orig = archive(comment=b'\0' * (pl.BLOCK - n % pl.BLOCK - 40))
        self.assertEqual(len(orig) % pl.BLOCK, pl.BLOCK - 40)
        grown = pl.replace(orig, {NAME: (b'stock theme ' * 200) + b'x' * 8})
        self.assertEqual(-(-len(grown) // pl.BLOCK), -(-len(orig) // pl.BLOCK))
        rnd = random.Random(2)
        with self.assertRaises(ValueError):
            pl.replace(orig, {NAME: bytes(rnd.randrange(256) for _ in range(4000))})

    def test_keeps_an_existing_comment(self):
        orig = archive(comment=b'libmisc')
        out = zipfile.ZipFile(io.BytesIO(pl.replace(orig, {NAME: b'x'})))
        self.assertTrue(out.comment.startswith(b'libmisc'))

    def test_unknown_names_are_refused(self):
        with self.assertRaises(AssertionError):
            pl.replace(self.orig, {'.rockbox/wps/Nope.wps': b'x'})

    def test_real_theme_fits(self):
        with open(THEME, 'rb') as f:
            theme = f.read()
        self.assertIn(b'%pv(0,0,9,', theme)
        out = pl.replace(self.orig, {NAME: theme})
        self.assertEqual(zipfile.ZipFile(io.BytesIO(out)).read(NAME), theme)


if __name__ == '__main__':
    unittest.main()

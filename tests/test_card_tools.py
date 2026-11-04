"""tools/card_audio_scan.py and tools/card_manifest.py."""
import contextlib
import io
import os
import struct
import tempfile
import unittest

from helpers import ROOT  # noqa: F401  (sets the import path)
import card_audio_scan as scan
import card_manifest as manifest


def chunk(cid, body):
    return cid + struct.pack('>I', len(body)) + body + (b'\0' if len(body) & 1 else b'')


def aiff(fllr=0, form=b'AIFF', comm=True):
    comm_body = struct.pack('>HIH', 2, 1000, 16) + b'\x40\x0e\xac\x44' + b'\0' * 6
    if form == b'AIFC':
        comm_body += b'NONE\x00'
    parts = []
    if fllr:
        parts.append(chunk(b'FLLR', b'\0' * fllr))
    if comm:
        parts.append(chunk(b'COMM', comm_body))
    parts.append(chunk(b'SSND', struct.pack('>II', 0, 0) + b'\0' * 4000))
    body = form + b''.join(parts)
    return b'FORM' + struct.pack('>I', len(body)) + body


class AudioScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def scan(self, data):
        p = os.path.join(self.tmp.name, 'x.aiff')
        with open(p, 'wb') as f:
            f.write(data)
        return scan.scan_aiff(p)

    def test_plain_aiff_plays(self):
        info = self.scan(aiff())
        self.assertIsNone(info['reason'])
        self.assertEqual((info['form'], info['channels'], info['bits']), ('AIFF', 2, 16))

    def test_4k_fllr_chunk_is_what_stock_rockbox_refused(self):
        # rekordbox/Core Audio AIFFs: the reason for AIFF_HEADER_MAX 8192.
        info = self.scan(aiff(fllr=4096))
        self.assertIn('FLLR chunk', info['reason'])
        self.assertEqual([c[0] for c in info['layout']], ['FLLR', 'COMM', 'SSND'])

    def test_missing_comm(self):
        self.assertEqual(self.scan(aiff(comm=False))['reason'], 'no COMM before SSND')

    def test_aifc(self):
        info = self.scan(aiff(form=b'AIFC'))
        self.assertEqual((info['form'], info['compression']), ('AIFC', 'NONE'))

    def test_not_an_aiff(self):
        self.assertIn('bad_form', self.scan(b'RIFF' + b'\0' * 100))


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, 'Contents'))
        os.makedirs(os.path.join(self.root, 'PIONEER'))
        self.put('Contents/a.aiff', b'audio')
        self.put('PIONEER/export.pdb', b'v1')

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, data):
        with open(os.path.join(self.root, rel), 'wb') as f:
            f.write(data)

    def diff(self, before, after):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = manifest.diff(before, after)
        return rc, out.getvalue()

    def test_snapshot(self):
        snap = manifest.snap(self.root)
        self.assertEqual(sorted(snap), [os.path.join('Contents', 'a.aiff'),
                                        os.path.join('PIONEER', 'export.pdb')])
        self.assertEqual(snap[os.path.join('Contents', 'a.aiff')]['size'], 5)

    def test_library_changes_are_ok(self):
        before = manifest.snap(self.root)
        self.put('PIONEER/export.pdb', b'v2')
        self.put('._junk', b'')
        rc, out = self.diff(before, manifest.snap(self.root))
        self.assertEqual(rc, 0)
        self.assertIn('CHANGED  PIONEER/export.pdb', out)
        self.assertIn('ADDED    ._junk  (macOS noise)', out)

    def test_changed_audio_fails(self):
        before = manifest.snap(self.root)
        self.put('Contents/a.aiff', b'AUDIO')
        rc, out = self.diff(before, manifest.snap(self.root))
        self.assertEqual(rc, 1)
        self.assertIn('FAIL', out)

    def test_removed_audio_fails(self):
        before = manifest.snap(self.root)
        os.remove(os.path.join(self.root, 'Contents', 'a.aiff'))
        rc, _ = self.diff(before, manifest.snap(self.root))
        self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main()

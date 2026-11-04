"""tools/stamp_card_playlists.py: clean macOS ._ files, restore order timestamps."""
import contextlib
import io
import os
import shutil
import tempfile
import unittest

from helpers import ROOT  # noqa: F401  (sets the import path)
import stamp_card_playlists as stamp

T0 = 1577836800  # pdb_playlists.ORDER_EPOCH


class StampTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.local = os.path.join(self.tmp.name, 'local')
        self.card = os.path.join(self.tmp.name, 'card')
        os.makedirs(os.path.join(self.local, 'System 2023', 'Emotion'))
        os.makedirs(os.path.join(self.card, 'Contents'))
        open(os.path.join(self.card, 'Contents', 'a.aiff'), 'w').close()
        self.write('Top.m3u8', ['#EXTM3U', '/storage/sdcard1/Contents/a.aiff'])
        self.write('System 2023/Emotion/HAPPY.m3u8',
                   ['#EXTM3U', '/storage/sdcard1/Contents/a.aiff',
                    '/storage/sdcard1/Contents/missing.mp3'])
        for rel, n in (('System 2023/Emotion/HAPPY.m3u8', 1), ('System 2023/Emotion', 1),
                       ('Top.m3u8', 1), ('System 2023', 2)):
            t = T0 + n * 10
            os.utime(os.path.join(self.local, rel), (t, t))
        # Copy to the card as cp -R does (times not kept), and add macOS litter.
        shutil.copytree(self.local, os.path.join(self.card, 'Playlists'),
                        copy_function=shutil.copyfile)
        for rel in ('._Top.m3u8', 'System 2023/._Emotion', 'System 2023/Emotion/._HAPPY.m3u8'):
            open(os.path.join(self.card, 'Playlists', rel), 'w').close()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, lines):
        with open(os.path.join(self.local, rel), 'w') as f:
            f.write('\n'.join(lines) + '\n')

    def run_stamp(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return stamp.main([self.local, self.card])

    def test_removes_macos_files(self):
        r = self.run_stamp()
        self.assertEqual((r['removed'], r['stuck']), (3, 0))
        left = [f for d, _, fs in os.walk(self.card) for f in fs if f.startswith('._')]
        self.assertEqual(left, [])

    def test_restores_times_children_first(self):
        r = self.run_stamp()
        self.assertEqual(r['wrong_times'], 0)
        for rel in ('Top.m3u8', 'System 2023', 'System 2023/Emotion',
                    'System 2023/Emotion/HAPPY.m3u8'):
            self.assertEqual(os.stat(os.path.join(self.card, 'Playlists', rel)).st_mtime,
                             os.stat(os.path.join(self.local, rel)).st_mtime, rel)

    def test_reports_tracks_missing_from_the_card(self):
        r = self.run_stamp()
        self.assertEqual((r['playlists'], r['missing_tracks']), (2, 1))

    def test_accepts_command_line_style_arguments(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            stamp.main([self.local, self.card, 'extra'])
        self.assertIn('playlists 2', out.getvalue())


if __name__ == '__main__':
    unittest.main()

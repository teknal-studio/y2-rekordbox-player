"""Volume keys and the volume bar.

- build/patches/y2dj-volume-keys.patch: the native block, compiled from the
  patch with tests/c/volume_keys_test.c; and the Java markers.
- themes/MacClassic-Dark-Y2DJ.wps and tools/install_theme.py.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from helpers import ROOT
from test_catalog_paths import added, file_sections
import install_theme

PATCH = os.path.join(ROOT, 'build', 'patches', 'y2dj-volume-keys.patch')
HARNESS = os.path.join(ROOT, 'tests', 'c', 'volume_keys_test.c')
THEME = os.path.join(ROOT, 'themes', 'MacClassic-Dark-Y2DJ.wps')


def patch_files():
    with open(PATCH) as f:
        return file_sections(f.read())


@unittest.skipIf(shutil.which('cc') is None, 'needs a C compiler')
class VolumeKeysNativeTest(unittest.TestCase):
    def test_volume_keys_are_queued(self):
        block = added(patch_files()['firmware/target/hosted/android/button-android.c'],
                      'if (keycode == KEYCODE_VOLUME_UP', 'return true;')
        block += '    }\n'
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, 'volume.inc'), 'w') as f:
                f.write(block)
            exe = os.path.join(tmp, 'volume_keys_test')
            r = subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-I', tmp,
                                '-o', exe, HARNESS], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = subprocess.run([exe], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn('0 failure(s)', r.stdout)


class VolumeKeysJavaTest(unittest.TestCase):
    def test_markers_log_where_a_key_gets_to(self):
        files = patch_files()
        activity = '\n'.join(files['android/src/org/rockbox/RockboxActivity.java'])
        view = '\n'.join(files['android/src/org/rockbox/RockboxFramebuffer.java'])
        self.assertIn('+import android.view.KeyEvent;', activity)
        self.assertIn('RockboxVolume:activity', activity)
        self.assertIn('+        return super.dispatchKeyEvent(event);', activity)
        self.assertIn('RockboxVolume:view key-down', view)
        self.assertIn('RockboxVolume:view key-up', view)


class ThemeTest(unittest.TestCase):
    def setUp(self):
        with open(THEME) as f:
            self.wps = f.read()

    def test_volume_bar_on_the_right_edge(self):
        m = re.search(r'^%V\((\d+),(\d+),(\d+),(\d+),-\)\n%pv\(0,0,(\d+),(\d+),vertical\)$',
                      self.wps, re.M)
        self.assertIsNotNone(m, 'no vertical volume bar')
        x, y, w, h, bw, bh = map(int, m.groups())
        self.assertEqual((bw, bh), (w, h))
        self.assertLessEqual(x + w, 480)          # on screen
        self.assertGreaterEqual(x, 460)           # at the right edge
        self.assertLessEqual(y + h, 276)          # above the progress bar

    def test_speaker_icon_is_gone(self):
        self.assertNotIn('volume320.bmp', self.wps)
        self.assertNotIn('%xd(Va)', self.wps)

    def test_text_rows_clear_the_fixed_elements(self):
        # With no album art, the title row used to start inside the "5 of 15"
        # track counter, which then clipped the start of the title.
        fixed = [tuple(map(int, m.groups())) for m in
                 re.finditer(r'^%V\((\d+),(\d+),(\d+),(\d+),', self.wps, re.M)]
        rows = [(m.group(1), tuple(map(int, m.groups()[1:]))) for m in
                re.finditer(r'%Vl\(([ab]),(\d+),(\d+),(\d+),(\d+),', self.wps)]
        self.assertEqual(sorted(l for l, _ in rows), ['a'] * 4 + ['b'] * 3)
        for layout, (x, y, w, h) in rows:
            for fx, fy, fw, fh in fixed:
                overlap = x < fx + fw and fx < x + w and y < fy + fh and fy < y + h
                self.assertFalse(overlap, f'layout {layout} row {(x, y, w, h)} overlaps '
                                          f'{(fx, fy, fw, fh)}')

    def test_no_art_rows_match_the_art_rows(self):
        rows = {l: sorted(int(y) for l2, y in re.findall(r'%Vl\(([ab]),\d+,(\d+),', self.wps)
                          if l2 == l) for l in 'ab'}
        # Title, artist and album sit at the same heights with or without art.
        self.assertEqual(rows['b'], [81, 117, 153])
        self.assertEqual(rows['a'][1:], [81, 119, 156])

    def test_nothing_else_overlaps_the_bar(self):
        for m in re.finditer(r'%V\((\d+),(\d+),(\d+),(\d+),', self.wps):
            x, y, w, h = map(int, m.groups())
            if (x, w) == (467, 9):
                continue
            overlaps_x = x < 476 and x + w > 467
            overlaps_y = y < 270 and y + h > 80
            self.assertFalse(overlaps_x and overlaps_y, f'viewport {m.group(0)} overlaps the bar')


class InstallThemeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = self.tmp.name
        base = os.path.join(self.storage, '.rockbox', 'wps', 'MacClassic-Dark')
        os.makedirs(base)
        for name in ('progress.bmp', 'battery.bmp'):
            with open(os.path.join(base, name), 'wb') as f:
                f.write(b'BM')
        with open(base + '.wps', 'w') as f:
            f.write('stock')

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, *parts):
        with open(os.path.join(self.storage, *parts)) as f:
            return f.read()

    def theme(self):
        with open(THEME) as f:
            return f.read()

    def test_writes_the_default_theme_and_cfg(self):
        install_theme.install(self.storage)
        self.assertEqual(self.read('.rockbox', 'wps', 'MacClassic-Dark.wps'), self.theme())
        self.assertEqual(self.read('y2dj-theme.cfg'), 'wps: /.rockbox/wps/MacClassic-Dark.wps\n')
        # No side copy unless an earlier install made one.
        self.assertFalse(os.path.exists(
            os.path.join(self.storage, '.rockbox', 'wps', 'MacClassic-Dark-Y2DJ.wps')))

    def test_refreshes_a_stale_copy(self):
        # An earlier install left an old copy that settings may point at: it
        # must be updated too, or a fix silently never shows.
        wps = os.path.join(self.storage, '.rockbox', 'wps')
        with open(os.path.join(wps, 'MacClassic-Dark-Y2DJ.wps'), 'w') as f:
            f.write('old layout')
        install_theme.install(self.storage)
        self.assertEqual(self.read('.rockbox', 'wps', 'MacClassic-Dark-Y2DJ.wps'), self.theme())
        self.assertEqual(sorted(os.listdir(os.path.join(wps, 'MacClassic-Dark-Y2DJ'))),
                         ['battery.bmp', 'progress.bmp'])

    def test_runs_again_cleanly(self):
        install_theme.install(self.storage)
        install_theme.install(self.storage)
        self.assertEqual(self.read('.rockbox', 'wps', 'MacClassic-Dark.wps'), self.theme())
        # The stock images are left alone.
        self.assertEqual(sorted(os.listdir(os.path.join(
            self.storage, '.rockbox', 'wps', 'MacClassic-Dark'))), ['battery.bmp', 'progress.bmp'])

    def test_removes_macos_litter_it_caused(self):
        wps = os.path.join(self.storage, '.rockbox', 'wps')
        open(os.path.join(wps, '._MacClassic-Dark.wps'), 'w').close()
        open(os.path.join(self.storage, '._y2dj-theme.cfg'), 'w').close()
        install_theme.install(self.storage)
        self.assertFalse(os.path.exists(os.path.join(wps, '._MacClassic-Dark.wps')))
        self.assertFalse(os.path.exists(os.path.join(self.storage, '._y2dj-theme.cfg')))

    def test_refuses_other_drives(self):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(SystemExit):
                install_theme.install(other)


if __name__ == '__main__':
    unittest.main()

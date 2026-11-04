"""The firmware patches apply cleanly to the Y2-Rockbox V2.5 source.

Needs the V2.5 source unpacked in sources/v2.5 (build/build_all.sh does that);
skipped otherwise.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

from helpers import ROOT

SRC = os.path.join(ROOT, 'sources', 'v2.5', 'Y2-Rockbox-V2.5-Source',
                   '11_rockbox_android', 'rockbox-y1')
PATCHES = os.path.join(ROOT, 'build', 'patches')
ALL = ['y2dj-playlists-aiff.patch', 'y2dj-title-display.patch', 'y2dj-launch-guard.patch']


@unittest.skipUnless(os.path.isdir(SRC), 'needs the V2.5 source in sources/v2.5')
@unittest.skipIf(shutil.which('patch') is None, 'needs patch')
class PatchesTest(unittest.TestCase):
    def test_every_patch_is_listed(self):
        self.assertEqual(sorted(ALL), sorted(p for p in os.listdir(PATCHES) if p.endswith('.patch')))

    def test_patches_apply_cleanly_in_build_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = set()
            for name in ALL:
                with open(os.path.join(PATCHES, name)) as f:
                    for line in f:
                        if line.startswith('+++ '):
                            files.add(line[4:].split('\t')[0].split('/', 1)[1])
            for rel in files:
                os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
                shutil.copy(os.path.join(SRC, rel), os.path.join(tmp, rel))
            for name in ALL:
                with open(os.path.join(PATCHES, name)) as f:
                    r = subprocess.run(['patch', '-p1', '--forward', '--batch'], stdin=f,
                                       cwd=tmp, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f'{name}:\n{r.stdout}{r.stderr}')
                self.assertNotIn('fuzz', r.stdout, f'{name} applied with fuzz:\n{r.stdout}')
                self.assertNotIn('offset', r.stdout, f'{name} applied at an offset:\n{r.stdout}')

            # Spot checks of what each patch is for.
            def read(rel):
                with open(os.path.join(tmp, rel), errors='replace') as f:
                    return f.read()
            self.assertIn('#define AIFF_HEADER_MAX 8192', read('lib/rbcodec/codecs/aiff.c'))
            self.assertIn('catalog_reopen_path', read('apps/playlist_catalog.c'))
            self.assertIn('tc.dirlevel = levels;', read('apps/tree.c'))
            self.assertIn('staleRouteRecovered', read('android/src/org/rockbox/Y2BootState.java'))
            # Track display defaults to "title from tags" (choice 3).
            self.assertIn('playlist_viewer_track_display, LANG_TRACK_DISPLAY, 3,',
                          read('apps/settings_list.c'))


if __name__ == '__main__':
    unittest.main()

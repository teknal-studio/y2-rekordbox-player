"""tools/pdb_playlists.py: rekordbox export.pdb to a nested Rockbox Playlists tree."""
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import ROOT
import pdb_fixture
import pdb_playlists as pp


class FixtureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pdb = os.path.join(cls.tmp.name, 'export.pdb')
        with open(cls.pdb, 'wb') as f:
            f.write(pdb_fixture.sample())
        cls.db, cls.tracks, cls.tree, cls.entries = pp.load(cls.pdb)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class StringTest(unittest.TestCase):
    def test_short_ascii(self):
        self.assertEqual(pp.dstring(pdb_fixture.dstring('HAPPY'), 0), 'HAPPY')
        self.assertEqual(pp.dstring(pdb_fixture.dstring(''), 0), '')

    def test_utf16(self):
        self.assertEqual(pp.dstring(pdb_fixture.dstring('Zürich Nights'), 0), 'Zürich Nights')

    def test_fs_name_keeps_names_readable_on_fat(self):
        self.assertEqual(pp.fs_name('Bad: Name?'), 'Bad_ Name_')
        self.assertEqual(pp.fs_name('AC/DC'), 'AC-DC')
        self.assertEqual(pp.fs_name('trailing dots...'), 'trailing dots')
        self.assertEqual(pp.fs_name('  '), '_')
        self.assertEqual(pp.fs_name('Zürich'), 'Zürich')


class LoadTest(FixtureCase):
    def test_tables(self):
        self.assertEqual(self.db.page_len, pdb_fixture.PAGE)
        self.assertEqual(sorted(self.db.tables), [0, 2, 7, 8])

    def test_tracks_span_two_pages(self):
        self.assertEqual(len(self.tracks), 22)
        t = self.tracks[2]
        self.assertEqual((t['title'], t['artist'], t['duration']),
                         ('Zürich Nights', 'Ünïcode Artist', 301))
        self.assertEqual(t['path'], '/Contents/Unicode/Zurich.flac')

    def test_index_page_is_skipped(self):
        self.assertEqual(self.tracks[1]['artist'], 'DJ One')

    def test_deleted_rows_are_ignored(self):
        self.assertNotIn(99, self.tree)
        self.assertEqual(len(self.tree), 8)

    def test_entries_are_in_rekordbox_order(self):
        # More than 16 rows per page, spread over two pages, stored out of order.
        happy = [tid for _, tid in self.entries[13]]
        self.assertEqual(happy, [100 + i for i in reversed(range(20))])

    def test_walk_is_depth_first_in_sort_order(self):
        names = ['/'.join(path) for _, path in pp.walk(self.tree)]
        self.assertEqual(names, ['Top Hits', 'System 2023', 'System 2023/Emotion',
                                 'System 2023/Emotion/HAPPY', 'System 2023/Emotion/SAD',
                                 'System 2023/Mix', 'Bad: Name?', 'Bad/ Name?'])


class WritePlaylistsTest(FixtureCase):
    def setUp(self):
        self.out = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self.out.name, 'Playlists')

    def tearDown(self):
        self.out.cleanup()

    def write(self, numbered=False):
        return pp.write_playlists(self.dir, self.tree, self.tracks, self.entries,
                                  numbered, '/storage/sdcard1')

    def read(self, rel):
        with open(os.path.join(self.dir, rel), encoding='utf-8') as f:
            return f.read().splitlines()

    def test_mirrors_the_rekordbox_tree(self):
        self.assertEqual(self.write(), [2, 6])
        found = sorted(os.path.relpath(os.path.join(d, x), self.dir)
                       for d, ds, fs in os.walk(self.dir) for x in ds + fs)
        self.assertEqual(found, sorted([
            'Top Hits.m3u8', 'System 2023', 'System 2023/Emotion',
            'System 2023/Emotion/HAPPY.m3u8', 'System 2023/Emotion/SAD.m3u8',
            'System 2023/Mix.m3u8', 'Bad_ Name_.m3u8', 'Bad- Name_.m3u8']))

    def test_track_paths_are_absolute_on_the_card(self):
        # Rockbox only collapses one level of "..", so nested lists need absolute paths.
        self.write()
        lines = self.read('System 2023/Emotion/SAD.m3u8')
        self.assertEqual(lines, ['#EXTM3U', '#EXTINF:245,DJ One - Anthem',
                                 '/storage/sdcard1/Contents/DJ One/Anthem.aiff'])

    def test_playlist_keeps_track_order_and_unicode(self):
        self.write()
        top = self.read('Top Hits.m3u8')
        self.assertEqual(top[3:], ['#EXTINF:301,Ünïcode Artist - Zürich Nights',
                                   '/storage/sdcard1/Contents/Unicode/Zurich.flac'])
        happy = [l for l in self.read('System 2023/Emotion/HAPPY.m3u8') if l.startswith('/')]
        self.assertEqual(happy[0], '/storage/sdcard1/Contents/Happy/19.mp3')
        self.assertEqual(happy[-1], '/storage/sdcard1/Contents/Happy/00.mp3')

    def test_empty_playlist(self):
        self.write()
        self.assertEqual(self.read('System 2023/Mix.m3u8'), ['#EXTM3U'])

    def test_order_is_carried_by_modified_times(self):
        # "sort playlists: oldest" shows them in rekordbox order; no number prefixes.
        self.write()
        def mtime(rel):
            return os.stat(os.path.join(self.dir, rel)).st_mtime
        top = ['Top Hits.m3u8', 'System 2023', 'Bad_ Name_.m3u8', 'Bad- Name_.m3u8']
        self.assertEqual([mtime(r) for r in top],
                         [pp.ORDER_EPOCH + n * pp.ORDER_STEP for n in (1, 2, 3, 4)])
        self.assertLess(mtime('System 2023/Emotion'), mtime('System 2023/Mix.m3u8'))
        self.assertLess(mtime('System 2023/Emotion/HAPPY.m3u8'),
                        mtime('System 2023/Emotion/SAD.m3u8'))
        # FAT keeps times to 2 s, so steps must be wider.
        self.assertGreater(pp.ORDER_STEP, 2)

    def test_numbered_names(self):
        self.write(numbered=True)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, '1 Top Hits.m3u8')))
        self.assertTrue(os.path.isdir(os.path.join(self.dir, '2 System 2023', '1 Emotion')))

    def test_names_that_collide_after_cleaning_get_a_suffix(self):
        tree = {1: {'id': 1, 'parent': 0, 'sort': 0, 'folder': False, 'name': 'A?'},
                2: {'id': 2, 'parent': 0, 'sort': 1, 'folder': False, 'name': 'A*'},
                3: {'id': 3, 'parent': 0, 'sort': 2, 'folder': False, 'name': 'a_'}}
        pp.write_playlists(self.dir, tree, {}, {}, False, '/storage/sdcard1')
        self.assertEqual(sorted(os.listdir(self.dir)),
                         ['A_ (2).m3u8', 'A_.m3u8', 'a_ (3).m3u8'])


class CommandLineTest(FixtureCase):
    def test_playlists_option(self):
        with tempfile.TemporaryDirectory() as out:
            r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'pdb_playlists.py'),
                                self.pdb, '--playlists', os.path.join(out, 'Playlists')],
                               capture_output=True, text=True, check=True)
            self.assertIn('wrote 2 folders and 6 playlists', r.stderr)
            self.assertTrue(os.path.isfile(
                os.path.join(out, 'Playlists', 'System 2023', 'Emotion', 'HAPPY.m3u8')))

    def test_tree_option(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'pdb_playlists.py'),
                            self.pdb, '--tree'], capture_output=True, text=True, check=True)
        self.assertIn('[+] System 2023', r.stdout)
        self.assertIn('    - HAPPY  (20 tracks)', r.stdout)


if __name__ == '__main__':
    unittest.main()

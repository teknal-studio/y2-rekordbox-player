"""Playlist catalog Back navigation, from build/patches/y2dj-playlists-aiff.patch.

Compiles the new C code straight out of the patch with tests/c/catalog_paths_test.c
and runs it against a mock Playlists folder. Needs a C compiler (cc).
"""
import os
import shutil
import subprocess
import tempfile
import unittest

from helpers import ROOT

PATCH = os.path.join(ROOT, 'build', 'patches', 'y2dj-playlists-aiff.patch')
HARNESS = os.path.join(ROOT, 'tests', 'c', 'catalog_paths_test.c')


def file_sections(patch):
    """{path: [lines]} for each file in a unified diff."""
    out, cur = {}, None
    for line in patch.splitlines():
        if line.startswith('+++ '):
            cur = line[4:].split('\t')[0].split('/', 1)[1]
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


def added(lines, start, end):
    """The added lines from the one containing start to the next one containing
    end (or, for end '}', the next line that is exactly '}')."""
    code, on = [], False
    for line in lines:
        if not line.startswith('+'):
            if on:
                raise AssertionError(f'unchanged line inside new code: {line!r}')
            continue
        text = line[1:]
        if start in text:
            on = True
        if on:
            code.append(text)
            done = text.rstrip() == '}' if end == '}' else end in text
            if done and len(code) > 1:
                return '\n'.join(code) + '\n'
    raise AssertionError(f'{start!r} .. {end!r} not found in the patch')


def extract(patch_text):
    files = file_sections(patch_text)
    reopen = added(files['apps/playlist_catalog.c'],
                   'static void catalog_reopen_path', '}')
    browse = added(files['apps/tree.c'],
                   'selected is relative to root', 'tc.dirlevel = levels;')
    return reopen, browse


@unittest.skipIf(shutil.which('cc') is None, 'needs a C compiler')
class CatalogPathsTest(unittest.TestCase):
    def test_back_navigation_cases(self):
        with open(PATCH) as f:
            reopen, browse = extract(f.read())
        with tempfile.TemporaryDirectory() as tmp:
            for name, code in (('reopen.inc', reopen), ('browse.inc', browse)):
                with open(os.path.join(tmp, name), 'w') as f:
                    f.write(code)
            exe = os.path.join(tmp, 'catalog_paths_test')
            flags = ['-std=c99', '-Wall', '-Wextra', '-Werror']
            if 'clang' not in subprocess.run(['cc', '--version'], capture_output=True,
                                             text=True).stdout:
                # GCC flags the deliberate, checked snprintf truncation.
                flags.append('-Wno-format-truncation')
            r = subprocess.run(['cc', *flags, '-I', tmp, '-o', exe, HARNESS],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            cards = os.path.join(tmp, 'card')
            os.makedirs(os.path.join(cards, 'Playlists', 'System 2023', 'Emotion'))
            r = subprocess.run([exe, cards], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('0 failure(s)', r.stdout)

    def test_catalog_no_longer_slices_the_saved_path(self):
        # The old code passed &most_recent_playlist[playlist_dir_length + 1],
        # which broke when the saved path had an extra slash.
        with open(PATCH) as f:
            catalog = '\n'.join(file_sections(f.read())['apps/playlist_catalog.c'])
        self.assertIn('-        .selected = &most_recent_playlist[playlist_dir_length + 1],', catalog)
        self.assertIn('+        .selected = reopen_at,', catalog)


if __name__ == '__main__':
    unittest.main()

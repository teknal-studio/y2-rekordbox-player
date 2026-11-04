"""build/build_all.sh and build/build_java.sh wiring.

- every patch in build/patches is applied, to the build(s) its files belong to;
- the resource version the build sets is the one the ROM test expects;
- build_java.sh's resource-version step rewrites RockboxService.java (needs
  GNU sed, as in the build container; skipped otherwise).
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from helpers import ROOT

BUILD_ALL = os.path.join(ROOT, 'build', 'build_all.sh')
BUILD_JAVA = os.path.join(ROOT, 'build', 'build_java.sh')
PATCHES = os.path.join(ROOT, 'build', 'patches')


def read(path):
    with open(path) as f:
        return f.read()


def patch_lists():
    """{'native': [...], 'java': [...]} patch names from build_all.sh."""
    text = read(BUILD_ALL)
    out = {}
    for key, script in (('native', 'build.sh'), ('java', 'build_java.sh')):
        m = re.search(r'bash /bld/' + re.escape(script) + r' \w+((?: /bld/patches/[\w.-]+)+)', text)
        assert m, f'{script} call not found'
        out[key] = [os.path.basename(p) for p in m.group(1).split()]
    return out


def patched_files(name):
    with open(os.path.join(PATCHES, name)) as f:
        return [l[4:].split('\t')[0].split('/', 1)[1] for l in f if l.startswith('+++ ')]


def gnu_sed():
    sed = shutil.which('gsed') or shutil.which('sed')
    r = subprocess.run([sed, '--version'], capture_output=True, text=True)
    return sed if r.returncode == 0 and 'GNU' in r.stdout else None


class PatchWiringTest(unittest.TestCase):
    def test_every_patch_is_applied(self):
        lists = patch_lists()
        used = set(lists['native']) | set(lists['java'])
        on_disk = {p for p in os.listdir(PATCHES) if p.endswith('.patch')}
        self.assertEqual(used, on_disk)

    def test_patches_go_to_the_builds_their_files_belong_to(self):
        lists = patch_lists()
        for name in sorted(set(lists['native']) | set(lists['java'])):
            files = patched_files(name)
            java = any(f.endswith('.java') for f in files)
            native = any(not f.endswith('.java') for f in files)
            self.assertEqual(name in lists['java'], java, f'{name} and the Java build')
            self.assertEqual(name in lists['native'], native, f'{name} and the native build')

    def test_build_order_is_fixed(self):
        # Later patches are made against earlier ones having been applied.
        lists = patch_lists()
        self.assertEqual(lists['native'], ['y2dj-playlists-aiff.patch', 'y2dj-title-display.patch',
                                           'y2dj-volume-keys.patch'])
        self.assertEqual(lists['java'], ['y2dj-launch-guard.patch', 'y2dj-volume-keys.patch'])


class ResourceVersionTest(unittest.TestCase):
    def test_version_comes_from_the_theme_hash(self):
        text = read(BUILD_ALL)
        self.assertIn('THEME=themes/MacClassic-Dark-Y2DJ.wps', text)
        self.assertIn('RESOURCE_VERSION="29-y2dj-$(shasum -a 256 "$THEME" | cut -c1-8)"', text)
        self.assertIn('-e Y2_RESOURCE_VERSION="$RESOURCE_VERSION"', text)
        # The ROM test computes the same value.
        self.assertIn("'29-y2dj-' + hashlib.sha256(f.read()).hexdigest()[:8]",
                      read(os.path.join(ROOT, 'tests', 'test_rom.py')))

    def test_theme_goes_into_the_resource_archive(self):
        text = read(BUILD_ALL)
        self.assertIn('debugfs -R "dump /lib/libmisc.so /tmp/x/libmisc.so"', text)
        self.assertIn('.rockbox/wps/MacClassic-Dark.wps=/themes/MacClassic-Dark-Y2DJ.wps', text)
        self.assertIn('-v "$ROOT/themes:/themes:ro"', text)


@unittest.skipIf(gnu_sed() is None, 'needs GNU sed, as in the build container')
class BuildJavaVersionStepTest(unittest.TestCase):
    def run_step(self, version):
        """Run build_java.sh's resource-version block against a stand-in file."""
        text = read(BUILD_JAVA)
        block = text[text.index('if [ -n "${Y2_RESOURCE_VERSION:-}" ]'):]
        block = block[:block.index('\nfi\n') + 4]
        with tempfile.TemporaryDirectory() as tmp:
            svc = os.path.join(tmp, 'src', 'org', 'rockbox', 'RockboxService.java')
            os.makedirs(os.path.dirname(svc))
            with open(svc, 'w') as f:
                f.write('class S {\n    private static final String Y2_RESOURCE_VERSION = "29";\n}\n')
            env = dict(os.environ, A=tmp, Y2_RESOURCE_VERSION=version)
            sed_dir = os.path.dirname(gnu_sed())
            env['PATH'] = sed_dir + os.pathsep + env['PATH']
            script = block.replace('sed -i', f'{gnu_sed()} -i')
            r = subprocess.run(['bash', '-euo', 'pipefail', '-c', script], env=env,
                               capture_output=True, text=True)
            return r, read(svc)

    def test_sets_the_version(self):
        r, svc = self.run_step('29-y2dj-1234abcd')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Y2_RESOURCE_VERSION = "29-y2dj-1234abcd";', svc)
        self.assertNotIn('= "29";', svc)

    def test_empty_version_leaves_the_file_alone(self):
        r, svc = self.run_step('')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Y2_RESOURCE_VERSION = "29";', svc)


if __name__ == '__main__':
    unittest.main()

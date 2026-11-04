"""The built ROM, checked by build/verify_rom.py inside the build image.

Needs Docker, the y2-rockbox-build image, the stock ROM in sources/ and a
build in build/out/ (run build/build_all.sh first); skipped otherwise.
"""
import os
import shutil
import subprocess
import unittest

from helpers import ROOT

IMAGE = 'y2-rockbox-build'
STOCK = os.path.join(ROOT, 'sources', 'rom_y2.zip')
BUILT = os.path.join(ROOT, 'build', 'out', 'rom', 'rom_y2.zip')


def have_image():
    if shutil.which('docker') is None:
        return False
    return subprocess.run(['docker', 'image', 'inspect', IMAGE],
                          capture_output=True).returncode == 0


@unittest.skipUnless(os.path.exists(STOCK) and os.path.exists(BUILT), 'needs a ROM build')
@unittest.skipUnless(have_image(), f'needs Docker and the {IMAGE} image')
class RomTest(unittest.TestCase):
    def test_verify_rom(self):
        r = subprocess.run(
            ['docker', 'run', '--rm', '--platform', 'linux/amd64',
             '-v', f'{ROOT}/build:/bld:ro', '-v', f'{ROOT}/build/out:/out:ro',
             '-v', f'{ROOT}/sources:/src:ro', IMAGE,
             'python3', '/bld/verify_rom.py', '/src/rom_y2.zip', '/out/rom/rom_y2.zip',
             '/out/patched'], capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('0 failure(s)', r.stdout)


if __name__ == '__main__':
    unittest.main()

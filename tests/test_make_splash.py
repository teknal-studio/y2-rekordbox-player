"""tools/make_splash.py: boot animation zip and MTK logo.bin."""
import io
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib

from helpers import ROOT

try:
    from PIL import Image, ImageChops, ImageStat
    import make_splash as ms
except ImportError:  # Pillow missing
    ms = None

W, H = 480, 360


def make_logo(path):
    """An asymmetric test logo: a wide bar with a block on its left end."""
    img = Image.new('RGBA', (600, 240), (0, 0, 0, 0))
    img.paste((40, 220, 230, 255), (0, 60, 600, 180))
    img.paste((255, 255, 255, 255), (0, 0, 120, 240))
    img.save(path)


def stock_logo_bin(boot, others):
    """An MTK logo.bin like the Y2's: boot logo first and last, others between."""
    images = [boot] + others + [boot]
    blobs = [zlib.compress(raw) for raw in images]
    n = len(blobs)
    offs, pos = [], 8 + 4 * n
    for b in blobs:
        offs.append(pos)
        pos += len(b)
    body = struct.pack(f'<II{n}I', n, pos, *offs) + b''.join(blobs)
    header = struct.pack('<II', ms.LOGO_MAGIC, len(body)) + b'LOGO'
    return header.ljust(40, b'\0').ljust(512, b'\xff') + body


def decode565(raw):
    return Image.frombuffer('RGB', (W, H), raw, 'raw', 'BGR;16', 0, 1)


def diff(a, b):
    """Mean absolute difference between two images, 0 to 255."""
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


@unittest.skipIf(ms is None, 'needs Pillow')
class SplashTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.logo = os.path.join(cls.tmp.name, 'logo.png')
        make_logo(cls.logo)
        cls.frames = ms.render_frames(cls.logo, W, H, 40, (0, 0, 0), 240, 2.5)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_frame_count_and_size(self):
        self.assertEqual(len(self.frames), 40)
        for f in self.frames:
            self.assertEqual((f.size, f.mode), ((W, H), 'RGB'))

    def test_first_frame_is_the_flat_logo(self):
        # Frame 0 faces the viewer: the logo is 240 px wide and centred.
        box = self.frames[0].convert('L').point(lambda v: 255 if v > 30 else 0).getbbox()
        left, top, right, bottom = box
        self.assertAlmostEqual(right - left, 240, delta=3)
        self.assertAlmostEqual((left + right) / 2, W / 2, delta=2)
        self.assertAlmostEqual((top + bottom) / 2, H / 2, delta=2)

    def test_spins_about_the_vertical_axis(self):
        # Half a turn shows the back: the logo mirrored left to right.
        flipped = self.frames[0].transpose(Image.FLIP_LEFT_RIGHT)
        self.assertLess(diff(self.frames[20], flipped), 2)
        self.assertGreater(diff(self.frames[20], self.frames[0]), 5)

    def test_edge_on_frame_is_nearly_empty(self):
        # A quarter turn shows the logo edge-on.
        self.assertLess(ImageStat.Stat(self.frames[10].convert('L')).mean[0], 3)

    def test_perspective_makes_the_near_edge_taller(self):
        # While turning, one end is nearer the viewer and drawn taller.
        def column_height(img, x):
            col = [img.getpixel((x, y)) for y in range(H)]
            lit = [y for y, p in enumerate(col) if sum(p) > 90]
            return (lit[-1] - lit[0]) if lit else 0
        f = self.frames[4]
        box = f.convert('L').point(lambda v: 255 if v > 30 else 0).getbbox()
        left = column_height(f, box[0] + 2)
        right = column_height(f, box[2] - 3)
        self.assertNotAlmostEqual(left, right, delta=4)

    def test_loops_seamlessly(self):
        # The next frame after the last would be frame 0 again: the step from
        # the last frame to the first matches a normal step.
        step = diff(self.frames[1], self.frames[0])
        wrap = diff(self.frames[0], self.frames[-1])
        self.assertLess(abs(wrap - step), max(2, step))


@unittest.skipIf(ms is None, 'needs Pillow')
class ZipTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, 'bootanimation.zip')
        self.frames = [Image.new('RGB', (W, H), (i * 6, 0, 0)) for i in range(40)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_layout_matches_the_stock_animation(self):
        ms.write_zip(self.frames, self.path, W, H, 20, 85)
        with zipfile.ZipFile(self.path) as z:
            self.assertEqual(z.read('desc.txt'), b'480 360 20\np 0 0 part0\n')
            names = z.namelist()
            self.assertEqual(names[0], 'desc.txt')
            self.assertEqual(names[1:], [f'part0/{i:05d}.jpg' for i in range(40)])
            # Android needs the zip stored, not deflated.
            self.assertEqual({i.compress_type for i in z.infolist()}, {zipfile.ZIP_STORED})
            jpeg = Image.open(io.BytesIO(z.read('part0/00000.jpg')))
            self.assertEqual((jpeg.format, jpeg.size), ('JPEG', (W, H)))

    def test_pads_to_an_exact_size(self):
        size = ms.write_zip(self.frames, self.path, W, H, 20, 85, pad_to=658280)
        self.assertEqual(size, 658280)
        self.assertEqual(os.path.getsize(self.path), 658280)
        with zipfile.ZipFile(self.path) as z:
            self.assertIsNone(z.testzip())
            # The padding sits outside part0/, so the animation ignores it.
            self.assertEqual(z.namelist()[-1], ms.PAD_NAME)
            self.assertNotIn('/', ms.PAD_NAME)
            self.assertEqual(len([n for n in z.namelist() if n.startswith('part0/')]), 40)

    def test_no_padding_when_already_too_big(self):
        size = ms.write_zip(self.frames, self.path, W, H, 20, 85, pad_to=100)
        self.assertGreater(size, 100)
        with zipfile.ZipFile(self.path) as z:
            self.assertNotIn(ms.PAD_NAME, z.namelist())


@unittest.skipIf(ms is None, 'needs Pillow')
class LogoBinTest(unittest.TestCase):
    def setUp(self):
        boot = ms.rgb565(Image.new('RGB', (W, H), (200, 20, 30)))
        self.charging = [bytes(range(256)) * 2, b'\x01\x02' * 300]
        self.stock = stock_logo_bin(boot, self.charging)
        self.still = Image.new('RGB', (W, H), (0, 0, 0))
        self.still.paste((40, 220, 230), (120, 140, 360, 220))

    def test_rgb565_bit_layout(self):
        # Red in the high bits, little-endian, as the Y2's logo.bin stores it
        # (stock SPYCE red reads back as 0xD105).
        px = lambda c: struct.unpack('<H', ms.rgb565(Image.new('RGB', (1, 1), c)))[0]
        self.assertEqual(px((255, 0, 0)), 0xF800)
        self.assertEqual(px((0, 255, 0)), 0x07E0)
        self.assertEqual(px((0, 0, 255)), 0x001F)
        self.assertEqual(px((213, 32, 41)), 0xD105)

    def test_reads_the_stock_layout(self):
        images = ms.read_logo_bin(self.stock)
        self.assertEqual(len(images), 4)
        self.assertEqual(images[1:3], self.charging)

    def test_replaces_only_the_boot_logo(self):
        out = ms.write_logo_bin(self.stock, self.still, W, H)
        old, new = ms.read_logo_bin(self.stock), ms.read_logo_bin(out)
        self.assertEqual(len(new), len(old))
        self.assertEqual(new[1:3], old[1:3])          # charging screens untouched
        self.assertEqual(new[0], new[-1])             # bootloader and kernel copies
        self.assertEqual(new[0], ms.rgb565(self.still))
        self.assertLess(diff(decode565(new[0]), self.still), 2)

    def test_header_matches_the_stock_header(self):
        out = ms.write_logo_bin(self.stock, self.still, W, H)
        magic, size = struct.unpack_from('<II', out)
        self.assertEqual(magic, ms.LOGO_MAGIC)
        self.assertEqual(size, len(out) - 512)
        self.assertEqual(out[8:40], self.stock[8:40])
        self.assertEqual(out[40:512], b'\xff' * 472)
        # The Y2's LOGO partition is 3 MiB.
        self.assertLess(len(out), 0x300000)

    def test_rejects_other_files(self):
        with self.assertRaises(AssertionError):
            ms.read_logo_bin(b'\0' * 1024)


@unittest.skipIf(ms is None, 'needs Pillow')
class CommandLineTest(unittest.TestCase):
    def test_writes_everything_for_the_rom(self):
        with tempfile.TemporaryDirectory() as tmp:
            logo = os.path.join(tmp, 'logo.png')
            make_logo(logo)
            boot = ms.rgb565(Image.new('RGB', (W, H), (200, 20, 30)))
            stock = os.path.join(tmp, 'stock_logo.bin')
            with open(stock, 'wb') as f:
                f.write(stock_logo_bin(boot, [b'\0' * 600]))
            out = os.path.join(tmp, 'out')
            subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'make_splash.py'),
                            logo, out, '--stock-logo-bin', stock, '--pad-to', '658280'],
                           check=True, capture_output=True)
            self.assertEqual(os.path.getsize(os.path.join(out, 'bootanimation.zip')), 658280)
            # The still is the animation's first frame, so the hand-off doesn't jump.
            with open(os.path.join(out, 'logo.bin'), 'rb') as f:
                logo_bin = f.read()
            still = decode565(ms.read_logo_bin(logo_bin)[0])
            with zipfile.ZipFile(os.path.join(out, 'bootanimation.zip')) as z:
                first = Image.open(io.BytesIO(z.read('part0/00000.jpg'))).convert('RGB')
            self.assertLess(diff(still, first), 4)

    def test_fails_when_too_big_for_the_rom(self):
        with tempfile.TemporaryDirectory() as tmp:
            logo = os.path.join(tmp, 'logo.png')
            make_logo(logo)
            r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'make_splash.py'),
                                logo, tmp, '--max-bytes', '1000'], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('too big', r.stderr)


if __name__ == '__main__':
    unittest.main()

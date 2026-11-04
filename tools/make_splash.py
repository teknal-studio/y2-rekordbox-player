#!/usr/bin/env python3
"""Make the Y2's boot splash from a logo: logo.bin and bootanimation.zip.

Logo in (a PNG with transparency), two files out:

  logo.bin           the still shown first, by the bootloader and the kernel.
                     Made from the stock logo.bin: only its boot logo images
                     change, the charging screens stay.
  bootanimation.zip  the logo spinning in 3D about its vertical axis, like the
                     stock SPYCE animation, looping until boot completes.

The still and the animation's first frame are the same picture, so the hand-off
between them doesn't jump.

    python3 -I tools/make_splash.py LOGO.png build/out/splash \
        --stock-logo-bin logo.bin --pad-to 658280 --gif

Needs Pillow. Frames are JPEG, so there's no transparency: everything sits on
a solid background colour. The zip is stored (uncompressed), as Android needs.
"""
import argparse
import io
import math
import os
import struct
import zipfile
import zlib

from PIL import Image

SS = 2  # supersampling factor for clean edges
LOGO_MAGIC = 0x58881688


def parse_colour(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def load_logo(path, width):
    """The logo trimmed to its visible pixels and scaled to width."""
    logo = Image.open(path).convert('RGBA')
    logo = logo.crop(logo.getchannel('A').getbbox())
    h = round(logo.height * width / logo.width)
    return logo.resize((width, h), Image.LANCZOS)


def perspective_coeffs(dst, src):
    """Coefficients for Image.transform(PERSPECTIVE) mapping dst quad to src."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); rhs.append(u)
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y]); rhs.append(v)
    # Solve the 8x8 system by Gaussian elimination.
    n = 8
    m = [r + [b] for r, b in zip(rows, rhs)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [a - f * b for a, b in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def spin_frame(logo, W, H, angle, bg, depth):
    """The logo turned angle degrees about its vertical axis, in perspective."""
    frame = Image.new('RGBA', (W, H), bg + (255,))
    w, h = logo.size
    c = math.cos(math.radians(angle))
    s = math.sin(math.radians(angle))
    if abs(c) < 0.02:  # edge-on: nothing to draw
        return frame.convert('RGB')
    f = w * depth  # viewing distance; smaller means stronger perspective
    cx, cy = W / 2, H / 2
    quad = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        z = x * s
        k = f / (f + z)
        quad.append((cx + x * c * k, cy + y * k))
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    coeffs = perspective_coeffs(quad, src)
    turned = logo.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    frame.alpha_composite(turned)
    return frame.convert('RGB')


def render_frames(logo_path, width, height, frames, bg, logo_width, depth):
    W, H = width * SS, height * SS
    logo = load_logo(logo_path, logo_width * SS)
    out = []
    for i in range(frames):
        frame = spin_frame(logo, W, H, 360.0 * i / frames, bg, depth)
        out.append(frame.resize((width, height), Image.LANCZOS))
    return out


PAD_NAME = 'padding.bin'  # top-level, so the boot animation ignores it


def write_zip(frames, path, width, height, fps, quality, pad_to=0):
    """Write the zip. With pad_to, add a padding entry so the zip is exactly
    pad_to bytes: make_rom.py replaces files in place and needs the same size
    in blocks as the stock file."""
    desc = f'{width} {height} {fps}\np 0 0 part0\n'
    jpegs = []
    for f in frames:
        buf = io.BytesIO()
        f.save(buf, 'JPEG', quality=quality, optimize=True)
        jpegs.append(buf.getvalue())

    def build(pad):
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as z:
            z.writestr('desc.txt', desc)
            for i, data in enumerate(jpegs):
                z.writestr(f'part0/{i:05d}.jpg', data)
            if pad is not None:
                z.writestr(PAD_NAME, b'\0' * pad)
        return os.path.getsize(path)

    size = build(None)
    if pad_to and size < pad_to:
        empty = build(0)  # the cost of an empty padding entry
        if empty <= pad_to:
            size = build(pad_to - empty)
        else:
            size = build(None)
    return size


def rgb565(img):
    """RGB565 little-endian, red in the high bits, as MTK logo.bin stores it."""
    px = img.convert('RGB').tobytes()
    out = bytearray()
    for i in range(0, len(px), 3):
        r, g, b = px[i], px[i + 1], px[i + 2]
        out += struct.pack('<H', ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3))
    return bytes(out)


def read_logo_bin(data):
    """The list of raw images in an MTK logo.bin."""
    magic, size = struct.unpack_from('<II', data)
    assert magic == LOGO_MAGIC and data[8:12] == b'LOGO', 'not an MTK logo.bin'
    body = data[512:512 + size]
    n, total = struct.unpack_from('<II', body)
    offs = list(struct.unpack_from(f'<{n}I', body, 8)) + [total]
    return [zlib.decompress(body[offs[i]:offs[i + 1]]) for i in range(n)]


def write_logo_bin(stock, still, width, height):
    """stock logo.bin with every copy of its first (boot logo) image replaced."""
    images = read_logo_bin(stock)
    assert len(images[0]) == width * height * 2, 'unexpected boot logo size'
    boot = images[0]
    new = rgb565(still)
    images = [new if raw == boot else raw for raw in images]
    blobs = [zlib.compress(raw, 9) for raw in images]
    n = len(blobs)
    offs, pos = [], 8 + 4 * n
    for b in blobs:
        offs.append(pos)
        pos += len(b)
    body = struct.pack(f'<II{n}I', n, pos, *offs) + b''.join(blobs)
    header = struct.pack('<II', LOGO_MAGIC, len(body)) + b'LOGO'
    header = header.ljust(40, b'\0').ljust(512, b'\xff')
    assert stock[:40][8:12] == b'LOGO' and stock[40:512] == b'\xff' * 472
    return header + body


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('logo', help='logo image, ideally a transparent PNG')
    ap.add_argument('outdir')
    ap.add_argument('--stock-logo-bin', help='stock logo.bin; also write logo.bin')
    ap.add_argument('--width', type=int, default=480)
    ap.add_argument('--height', type=int, default=360)
    ap.add_argument('--fps', type=int, default=20)
    ap.add_argument('--seconds', type=float, default=2.0,
                    help='time for one turn (stock: 2)')
    ap.add_argument('--logo-width', type=int, default=240,
                    help='logo width in pixels (stock SPYCE: 228)')
    ap.add_argument('--depth', type=float, default=2.5,
                    help='perspective: viewing distance in logo widths')
    ap.add_argument('--bg', default='000000', help='background, hex RGB')
    ap.add_argument('--quality', type=int, default=85, help='JPEG quality')
    ap.add_argument('--max-bytes', type=int, default=161 * 4096,
                    help="fail if the zip is bigger (default: the stock file's 161 blocks)")
    ap.add_argument('--pad-to', type=int, default=0,
                    help='pad the zip to exactly this many bytes; for the ROM use '
                         'the stock size, 658280')
    ap.add_argument('--gif', action='store_true', help='also write preview.gif')
    a = ap.parse_args()

    frames_n = round(a.fps * a.seconds)
    bg = parse_colour(a.bg)
    frames = render_frames(a.logo, a.width, a.height, frames_n, bg,
                           a.logo_width, a.depth)
    os.makedirs(a.outdir, exist_ok=True)

    zpath = os.path.join(a.outdir, 'bootanimation.zip')
    size = write_zip(frames, zpath, a.width, a.height, a.fps, a.quality,
                     a.pad_to)
    print(f'{zpath}: {frames_n} frames, {frames_n / a.fps:.2f} s a turn, '
          f'{size} bytes ({math.ceil(size / 4096)} blocks)')
    if a.pad_to and size != a.pad_to:
        raise SystemExit(f'could not pad to {a.pad_to} bytes (got {size})')
    if size > a.max_bytes:
        raise SystemExit(f'too big: {size} > {a.max_bytes} bytes; '
                         'lower --quality or extend make_rom.py')

    if a.stock_logo_bin:
        stock = open(a.stock_logo_bin, 'rb').read()
        lpath = os.path.join(a.outdir, 'logo.bin')
        with open(lpath, 'wb') as f:
            f.write(write_logo_bin(stock, frames[0], a.width, a.height))
        frames[0].save(os.path.join(a.outdir, 'still.png'))
        print(f'{lpath}: {os.path.getsize(lpath)} bytes')

    if a.gif:
        gpath = os.path.join(a.outdir, 'preview.gif')
        frames[0].save(gpath, save_all=True, append_images=frames[1:],
                       duration=round(1000 / a.fps), loop=0)
        print(gpath)


if __name__ == '__main__':
    main()

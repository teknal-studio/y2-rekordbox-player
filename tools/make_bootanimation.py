#!/usr/bin/env python3
"""Make an Android bootanimation.zip of a logo spinning flat, like a record.

Logo in (a PNG with transparency), bootanimation.zip out. The animation is
one seamless clockwise turn, so it loops cleanly until boot completes.

    python3 -I tools/make_bootanimation.py LOGO.png build/out/splash \
        --style record --gif

Styles:
  logo    the logo alone, spinning on the background
  record  the logo on a vinyl record, with a fixed light sheen on top

Needs Pillow. Frames are JPEG, so there's no transparency: everything sits on
a solid background colour. The zip is stored (uncompressed), as Android needs.
"""
import argparse
import io
import math
import os
import zipfile

from PIL import Image, ImageDraw, ImageFilter

SS = 2  # supersampling factor for clean edges


def parse_colour(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def trimmed_logo(path):
    logo = Image.open(path).convert('RGBA')
    return logo.crop(logo.getchannel('A').getbbox())


def fit_logo(logo, max_diameter):
    """Scale the logo so its whole diagonal fits in a circle, for any angle."""
    w, h = logo.size
    scale = max_diameter / math.hypot(w, h)
    return logo.resize((round(w * scale), round(h * scale)), Image.LANCZOS)


def record_layers(diameter, bg):
    """A vinyl disc (rotates) and a light sheen (stays fixed)."""
    d = diameter
    disc = Image.new('RGBA', (d, d), (0, 0, 0, 0))
    draw = ImageDraw.Draw(disc)
    draw.ellipse((0, 0, d - 1, d - 1), fill=(14, 14, 16, 255))
    # Grooves: thin rings, slightly lighter, between the rim and the label.
    c = d / 2
    for r in range(int(c * 0.40), int(c * 0.97), max(1, SS * 2)):
        shade = 22 + (r * 7) % 9
        draw.ellipse((c - r, c - r, c + r, c + r),
                     outline=(shade, shade, shade + 2, 255), width=1)
    # A faint off-centre mark so the spin reads even where the logo is thin.
    mark = int(c * 0.93)
    draw.arc((c - mark, c - mark, c + mark, c + mark), 80, 100,
             fill=(60, 60, 66, 255), width=SS * 2)
    # Spindle hole.
    hole = max(2, int(d * 0.012))
    draw.ellipse((c - hole, c - hole, c + hole, c + hole), fill=bg + (255,))

    # Sheen: two soft opposite wedges of light, fixed while the disc turns.
    sheen = Image.new('L', (d, d), 0)
    sd = ImageDraw.Draw(sheen)
    for start in (300, 120):
        sd.pieslice((0, 0, d - 1, d - 1), start, start + 28, fill=34)
    sheen = sheen.filter(ImageFilter.GaussianBlur(d * 0.04))
    rim = Image.new('L', (d, d), 0)
    ImageDraw.Draw(rim).ellipse((0, 0, d - 1, d - 1), fill=255)
    sheen = Image.composite(sheen, Image.new('L', (d, d), 0), rim)
    light = Image.new('RGBA', (d, d), (255, 255, 255, 0))
    light.putalpha(sheen)
    return disc, light


def render_frames(logo_path, width, height, frames, style, bg, logo_frac):
    W, H = width * SS, height * SS
    diameter = int(min(W, H) * 0.94)
    logo = trimmed_logo(logo_path)
    disc = light = None
    if style == 'record':
        disc, light = record_layers(diameter, bg)
        logo = fit_logo(logo, diameter * logo_frac)
    else:
        logo = fit_logo(logo, diameter)

    # One square layer that turns: the disc (if any) with the logo centred.
    spin = Image.new('RGBA', (diameter, diameter), (0, 0, 0, 0))
    if disc:
        spin.alpha_composite(disc)
    spin.alpha_composite(logo, ((diameter - logo.width) // 2,
                                (diameter - logo.height) // 2))

    out = []
    for i in range(frames):
        angle = -360.0 * i / frames  # negative = clockwise, like a platter
        turned = spin.rotate(angle, resample=Image.BICUBIC)
        frame = Image.new('RGBA', (W, H), bg + (255,))
        pos = ((W - diameter) // 2, (H - diameter) // 2)
        frame.alpha_composite(turned, pos)
        if light:
            frame.alpha_composite(light, pos)
        out.append(frame.convert('RGB').resize((width, height), Image.LANCZOS))
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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('logo', help='logo image, ideally a transparent PNG')
    ap.add_argument('outdir')
    ap.add_argument('--style', choices=('logo', 'record'), default='record')
    ap.add_argument('--width', type=int, default=480)
    ap.add_argument('--height', type=int, default=360)
    ap.add_argument('--fps', type=int, default=20)
    ap.add_argument('--rpm', type=float, default=100 / 3,
                    help='turn speed; default 33 1/3 (1.8 s a turn)')
    ap.add_argument('--bg', default='000000', help='background, hex RGB')
    ap.add_argument('--logo-size', type=float, default=0.80,
                    help='record style: logo diagonal as a share of the disc')
    ap.add_argument('--quality', type=int, default=85, help='JPEG quality')
    ap.add_argument('--max-bytes', type=int, default=161 * 4096,
                    help="fail if the zip is bigger (default: the stock file's 161 blocks)")
    ap.add_argument('--pad-to', type=int, default=0,
                    help='pad the zip to exactly this many bytes; for the ROM use '
                         'the stock size, 658280')
    ap.add_argument('--gif', action='store_true', help='also write preview.gif')
    a = ap.parse_args()

    frames_n = round(a.fps * 60 / a.rpm)
    bg = parse_colour(a.bg)
    frames = render_frames(a.logo, a.width, a.height, frames_n, a.style, bg,
                           a.logo_size)
    os.makedirs(a.outdir, exist_ok=True)
    zpath = os.path.join(a.outdir, 'bootanimation.zip')
    size = write_zip(frames, zpath, a.width, a.height, a.fps, a.quality,
                     a.pad_to)
    if a.pad_to and size != a.pad_to:
        raise SystemExit(f'could not pad to {a.pad_to} bytes (got {size})')
    print(f'{zpath}: {frames_n} frames, {frames_n / a.fps:.2f} s a turn, '
          f'{size} bytes ({math.ceil(size / 4096)} blocks)')
    if a.gif:
        gpath = os.path.join(a.outdir, 'preview.gif')
        frames[0].save(gpath, save_all=True, append_images=frames[1:],
                       duration=round(1000 / a.fps), loop=0)
        print(gpath)
    if size > a.max_bytes:
        raise SystemExit(f'too big: {size} > {a.max_bytes} bytes; '
                         'lower --quality or extend make_rom.py')


if __name__ == '__main__':
    main()

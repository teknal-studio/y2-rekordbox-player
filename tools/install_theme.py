#!/usr/bin/env python3
"""Put the y2-rekordbox-player Now Playing theme on a mounted Y2, without flashing.

The ROM ships themes/MacClassic-Dark-Y2DJ.wps as the default MacClassic-Dark
theme. This writes the same file to the Y2's internal storage, so a theme
change can be tried before the next flash:

  .rockbox/wps/MacClassic-Dark.wps        the default theme (stock images)
  .rockbox/wps/MacClassic-Dark-Y2DJ.wps   kept in step if an earlier install made it
  y2dj-theme.cfg                          open it on the Y2 to select the theme

Both theme files are always rewritten, so neither can go stale.

usage: install_theme.py /Volumes/<Y2 internal storage>
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME_SRC = os.path.join(HERE, '..', 'themes', 'MacClassic-Dark-Y2DJ.wps')
DEFAULT = 'MacClassic-Dark'
COPY = 'MacClassic-Dark-Y2DJ'  # the name earlier installs used


def install(storage, theme_src=THEME_SRC):
    wps = os.path.join(storage, '.rockbox', 'wps')
    if not os.path.isdir(os.path.join(wps, DEFAULT)):
        raise SystemExit(f'{wps}/{DEFAULT} not found: is this the Y2 internal storage?')
    written = []

    targets = [DEFAULT]
    if os.path.exists(os.path.join(wps, COPY + '.wps')):
        targets.append(COPY)
        if not os.path.isdir(os.path.join(wps, COPY)):
            shutil.copytree(os.path.join(wps, DEFAULT), os.path.join(wps, COPY),
                            copy_function=shutil.copyfile)
        written.append(os.path.join(wps, COPY))
    for name in targets:
        dst = os.path.join(wps, name + '.wps')
        shutil.copyfile(theme_src, dst)
        written.append(dst)

    cfg = os.path.join(storage, 'y2dj-theme.cfg')
    with open(cfg, 'w', newline='\n') as f:
        f.write(f'wps: /.rockbox/wps/{DEFAULT}.wps\n')
    written.append(cfg)

    remove_appledouble(written)
    return written


def remove_appledouble(paths):
    """macOS writes ._name files beside what it copies to FAT; drop ours."""
    for path in paths:
        targets = [path]
        if os.path.isdir(path):
            targets += [os.path.join(path, n) for n in os.listdir(path)]
        for t in targets:
            junk = os.path.join(os.path.dirname(t), '._' + os.path.basename(t))
            if os.path.basename(t).startswith('._'):
                junk = t
            if os.path.isfile(junk):
                os.remove(junk)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    for path in install(sys.argv[1]):
        print('wrote', path)
    print('On the Y2, open y2dj-theme.cfg in Files (internal storage) to select the theme.')


if __name__ == '__main__':
    main()

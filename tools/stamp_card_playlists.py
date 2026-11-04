#!/usr/bin/env python3
"""Clean a card's Playlists tree and restore the rekordbox order timestamps.

macOS drops ._ files on exFAT, and removing them changes folder times, so the
times are applied last, children first.

usage: stamp_card_playlists.py <local Playlists> <card>
"""
import os
import sys


def main():
    local, card = sys.argv[1:3]
    target = os.path.join(card, "Playlists")
    removed = stuck = 0
    for d, _, fs in os.walk(target):
        for f in fs:
            if f.startswith("._"):
                try:
                    os.remove(os.path.join(d, f))
                    removed += 1
                except FileNotFoundError:  # NFD/NFC name mismatch on exFAT
                    stuck += 1
    print(f"removed ._ {removed}, could not remove {stuck}")

    for d, ds, fs in os.walk(local, topdown=False):
        rel = os.path.relpath(d, local)
        dst = os.path.normpath(os.path.join(target, rel))
        for x in fs + ds:
            t = os.stat(os.path.join(d, x)).st_mtime
            os.utime(os.path.join(dst, x), (t, t))
    os.sync()

    wrong = missing = files = 0
    for d, ds, fs in os.walk(local):
        rel = os.path.relpath(d, local)
        dst = os.path.normpath(os.path.join(target, rel))
        for x in fs + ds:
            if abs(os.stat(os.path.join(d, x)).st_mtime - os.stat(os.path.join(dst, x)).st_mtime) > 2:
                wrong += 1
        for f in fs:
            files += 1
            with open(os.path.join(dst, f), encoding="utf-8") as h:
                for line in h:
                    line = line.rstrip("\n")
                    if line.startswith("/") and not os.path.exists(card + line[len("/storage/sdcard1"):]):
                        missing += 1
    print(f"playlists {files}, wrong times {wrong}, missing tracks {missing}")


if __name__ == "__main__":
    main()

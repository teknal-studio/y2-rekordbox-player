#!/usr/bin/env python3
"""Check a built ROM against the stock V2.5 ROM and the patched files.

Runs inside the build image (needs simg2img, debugfs and e2fsck). build_all.sh
runs it after every build.
usage: verify_rom.py stock_rom.zip built_rom.zip patched_dir [themes_dir resource_version]
"""
import io
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_vold  # noqa: E402

SYSTEM_FILES = {"/lib/librockbox.so": "librockbox.so", "/lib/libaiff.so": "libaiff.so",
                "/app/Rockbox.apk": "Rockbox.apk", "/bin/vold": "vold"}
BOOTANIM = "/media/bootanimation.zip"
LIBMISC = "/lib/libmisc.so"
THEME_ENTRY = ".rockbox/wps/MacClassic-Dark.wps"
LOGO_MAGIC = 0x58881688
failures = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        failures.append(what)


def run(*a):
    return subprocess.run(a, capture_output=True, text=True)


def dump(img, name, dst):
    run("debugfs", "-R", f"dump {name} {dst}", img)
    with open(dst, "rb") as f:
        return f.read()


def logo_images(data):
    magic, size = struct.unpack_from("<II", data)
    assert magic == LOGO_MAGIC and data[8:12] == b"LOGO"
    body = data[512:512 + size]
    n, total = struct.unpack_from("<II", body)
    offs = list(struct.unpack_from(f"<{n}I", body, 8)) + [total]
    return [zlib.decompress(body[offs[i]:offs[i + 1]]) for i in range(n)]


def main():
    stock_zip, built_zip, patched = sys.argv[1:4]
    themes, resource_version = (sys.argv[4:6] + [None, None])[:2]
    splash = os.path.exists(f"{patched}/bootanimation.zip")
    theme = os.path.exists(f"{patched}/libmisc.so")
    stock, built = zipfile.ZipFile(stock_zip), zipfile.ZipFile(built_zip)

    names = [i.filename for i in stock.infolist()]
    check(names == [i.filename for i in built.infolist()], "same files as the stock ROM, same order")
    changed = sorted(n for n in names if stock.read(n) != built.read(n))
    want = ["logo.bin", "system.img"] if splash else ["system.img"]
    check(changed == want, f"only {', '.join(want)} differ (got {', '.join(changed)})")

    with tempfile.TemporaryDirectory() as tmp:
        for tag, z in (("stock", stock), ("built", built)):
            with open(f"{tmp}/{tag}.img", "wb") as f:
                f.write(z.read("system.img"))
            run("simg2img", f"{tmp}/{tag}.img", f"{tmp}/{tag}.raw")
        raw = f"{tmp}/built.raw"

        fsck = run("e2fsck", "-fn", raw)
        check(fsck.returncode == 0, "system image passes e2fsck")

        files = dict(SYSTEM_FILES)
        if splash:
            files[BOOTANIM] = "bootanimation.zip"
        if theme:
            files[LIBMISC] = "libmisc.so"
        for name, local in files.items():
            with open(f"{patched}/{local}", "rb") as f:
                want_bytes = f.read()
            check(dump(raw, name, f"{tmp}/x") == want_bytes, f"{name} is the patched file")

        stock_vold = dump(f"{tmp}/stock.raw", "/bin/vold", f"{tmp}/v")
        check(dump(raw, "/bin/vold", f"{tmp}/v2") == patch_vold.patch(stock_vold),
              "vold has exactly the LUN swap")

        if theme:
            check_theme(f"{tmp}/stock.raw", raw, tmp, themes, resource_version, patched)

        if splash:
            with zipfile.ZipFile(f"{patched}/bootanimation.zip") as z:
                stored = all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist())
                desc = z.read("desc.txt").decode()
                frames = [n for n in z.namelist() if n.startswith("part0/")]
            check(stored, "boot animation is stored, not compressed")
            check(desc.split("\n")[0] == "480 360 20" and "p 0 0 part0" in desc,
                  "boot animation desc.txt is 480x360 at 20 fps, looping part0")
            check(len(frames) > 0, f"boot animation has frames ({len(frames)})")
            old = stat_size(f"{tmp}/stock.raw", BOOTANIM)
            check(stat_size(raw, BOOTANIM) == old, "boot animation keeps the stock size")

    if splash:
        old, new = logo_images(stock.read("logo.bin")), logo_images(built.read("logo.bin"))
        boot = [i for i, raw in enumerate(old) if raw == old[0]]
        check(len(new) == len(old), "logo.bin keeps its image count")
        check(all(new[i] == old[i] for i in range(len(old)) if i not in boot),
              "logo.bin charging screens are unchanged")
        check(all(new[i] != old[i] and new[i] == new[boot[0]] for i in boot),
              f"logo.bin boot logo replaced in all {len(boot)} places")
        check(len(built.read("logo.bin")) < 0x300000, "logo.bin fits the 3 MiB LOGO partition")

    print(f"{len(failures)} failure(s)")
    sys.exit(1 if failures else 0)


def check_theme(stock_raw, raw, tmp, themes, resource_version, patched):
    old = zipfile.ZipFile(io.BytesIO(dump(stock_raw, LIBMISC, f"{tmp}/m0")))
    new = zipfile.ZipFile(io.BytesIO(dump(raw, LIBMISC, f"{tmp}/m1")))
    check(new.testzip() is None, "resource archive is a valid zip")
    check(old.namelist() == new.namelist(), "resource archive has the same files")
    changed = [n for n in old.namelist() if old.read(n) != new.read(n)]
    check(changed == [THEME_ENTRY], f"resource archive changes only the theme (got {changed})")
    if themes:
        with open(os.path.join(themes, "MacClassic-Dark-Y2DJ.wps"), "rb") as f:
            check(new.read(THEME_ENTRY) == f.read(), "default theme is themes/MacClassic-Dark-Y2DJ.wps")
    if resource_version:
        with zipfile.ZipFile(f"{patched}/Rockbox.apk") as apk:
            dex = apk.read("classes.dex")
        check(resource_version.encode() in dex,
              f"app re-unpacks resources: version {resource_version}")


def stat_size(img, name):
    out = run("debugfs", "-R", f"stat {name}", img).stdout
    return int(out.split("Size: ")[1].split()[0])


if __name__ == "__main__":
    main()

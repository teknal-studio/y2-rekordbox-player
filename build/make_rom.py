#!/usr/bin/env python3
"""Put patched same-size files into the V2.5 system image, in place.

Writing over the existing data blocks keeps every inode, permission, SELinux
label and the rest of the filesystem unchanged. Runs inside the build image.
usage: make_rom.py rom_y2.zip patched_dir out.zip   (patched_dir has FILES values)
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile

rom, patched, out = sys.argv[1:4]
FILES = {"/lib/librockbox.so": "librockbox.so", "/lib/libaiff.so": "libaiff.so",
         "/app/Rockbox.apk": "Rockbox.apk", "/bin/vold": "vold"}
# Optional: a custom boot animation (tools/make_bootanimation.py --pad-to 658280).
if os.path.exists(f"{patched}/bootanimation.zip"):
    FILES["/media/bootanimation.zip"] = "bootanimation.zip"
BLOCK = 4096


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout


def extents(img, name):
    text = run("debugfs", "-R", f"stat {name}", img)
    body = text.split("EXTENTS:")[1]
    return [(int(a), int(b or a), int(c)) for a, b, c in
            re.findall(r"\((\d+)(?:-(\d+))?\):(\d+)", body)]


with zipfile.ZipFile(rom) as z:
    z.extract("system.img", "/tmp/rom")
run("simg2img", "/tmp/rom/system.img", "/tmp/rom/sys.raw")
shutil.copy("/tmp/rom/sys.raw", "/tmp/rom/sys.orig")

touched = []
resized = {}
with open("/tmp/rom/sys.raw", "r+b") as f:
    for name, local in FILES.items():
        data = open(f"{patched}/{local}", "rb").read()
        size = int(re.search(r"Size: (\d+)", run("debugfs", "-R", f"stat {name}", "/tmp/rom/sys.raw")).group(1))
        last = extents("/tmp/rom/sys.raw", name)[-1][1]  # holes are checked by the dump compare below
        assert (len(data) + BLOCK - 1) // BLOCK == (size + BLOCK - 1) // BLOCK == last + 1, (name, size, len(data))
        resized[name] = (len(data), size)
        for lo, hi, phys in extents("/tmp/rom/sys.raw", name):
            for i in range(hi - lo + 1):
                chunk = data[(lo + i) * BLOCK:(lo + i + 1) * BLOCK].ljust(BLOCK, b"\0")
                f.seek((phys + i) * BLOCK)
                f.write(chunk)
                touched.append(phys + i)

for name, (new, old) in resized.items():
    if new != old:
        run("debugfs", "-w", "-R", f"sif {name} size {new}", "/tmp/rom/sys.raw")

run("img2simg", "/tmp/rom/sys.raw", "/tmp/rom/new.img", str(BLOCK))
run("simg2img", "/tmp/rom/new.img", "/tmp/rom/back.raw")
assert hashlib.sha256(open("/tmp/rom/back.raw", "rb").read()).digest() == \
    hashlib.sha256(open("/tmp/rom/sys.raw", "rb").read()).digest()

touched = set(touched)
changed = outside = 0
with open("/tmp/rom/sys.orig", "rb") as a, open("/tmp/rom/sys.raw", "rb") as b:
    n = 0
    while True:
        x, y = a.read(BLOCK), b.read(BLOCK)
        if not x:
            break
        if x != y:
            changed += 1
            outside += n not in touched
        n += 1
print("blocks changed", changed, "outside the replaced files", outside)
assert outside <= 1  # the inode table block when a file size changed

for name, local in FILES.items():
    run("debugfs", "-R", f"dump {name} /tmp/rom/check", "/tmp/rom/back.raw")
    assert open("/tmp/rom/check", "rb").read() == open(f"{patched}/{local}", "rb").read()
print(subprocess.run(["e2fsck", "-fn", "/tmp/rom/back.raw"], capture_output=True, text=True).stdout[-160:])

with zipfile.ZipFile(rom) as src, zipfile.ZipFile(out, "w") as dst:
    for info in src.infolist():
        new = zipfile.ZipInfo(info.filename, info.date_time)
        new.compress_type = info.compress_type
        new.external_attr = info.external_attr
        if info.filename == "system.img":
            with open("/tmp/rom/new.img", "rb") as f:
                dst.writestr(new, f.read())
        else:
            dst.writestr(new, src.read(info.filename))
print("wrote", out)

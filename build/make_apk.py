#!/usr/bin/env python3
"""Repack Rockbox.apk with the patched code and libraries.

usage: make_apk.py original.apk classes.dex patched_dir out.apk
"""
import os
import shutil
import subprocess
import sys
import zipfile

src, dex, patched, out = sys.argv[1:5]
TOOLS = "/opt/sdk/build-tools/28.0.3"
KEY = "/out/y2dj-debug.keystore"
if not os.path.exists(KEY):
    subprocess.run(["keytool", "-genkeypair", "-keystore", KEY, "-storepass", "android",
                    "-keypass", "android", "-alias", "androiddebugkey", "-keyalg", "RSA",
                    "-keysize", "2048", "-sigalg", "SHA1withRSA", "-validity", "10000",
                    "-dname", "CN=y2dj,O=y2dj,C=US"], check=True)
replace = {"classes.dex": dex}
for lib in ("librockbox.so", "libaiff.so"):
    replace["lib/armeabi/" + lib] = os.path.join(patched, lib)
with zipfile.ZipFile(src) as a, zipfile.ZipFile("/tmp/u.apk", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as b:
    for old in a.infolist():
        if old.filename.startswith("META-INF/"):
            continue
        new = zipfile.ZipInfo(old.filename, old.date_time)
        new.compress_type = old.compress_type
        new.external_attr = old.external_attr
        data = open(replace[old.filename], "rb").read() if old.filename in replace else a.read(old.filename)
        b.writestr(new, data, compresslevel=9)
subprocess.run(["jarsigner", "-keystore", KEY, "-storepass", "android", "-keypass", "android",
                "-signedjar", "/tmp/s.apk", "/tmp/u.apk", "androiddebugkey",
                "-sigalg", "SHA1withRSA", "-digestalg", "SHA1"], check=True, capture_output=True)
subprocess.run([TOOLS + "/zipalign", "-f", "4", "/tmp/s.apk", "/tmp/a.apk"], check=True)
print("aligned", os.path.getsize("/tmp/a.apk"), "original", os.path.getsize(src))
subprocess.run(["jarsigner", "-verify", "/tmp/a.apk"], check=True, capture_output=True)
shutil.move("/tmp/a.apk", out)

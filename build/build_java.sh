#!/usr/bin/env bash
# usage: build_java.sh <name> [patch ...] - compiles the V2.5 Java side to /out/<name>/classes.dex
set -euo pipefail
NAME=$1; shift
SRC=/tmp/src/rockbox-y1; B=/tmp/j; SDK=/opt/sdk; T=$SDK/build-tools/28.0.3
mkdir -p /tmp/src "$B/gen" "$B/classes" /out/$NAME
cp -a /v25/11_rockbox_android/rockbox-y1 /tmp/src/
for p in "$@"; do (cd "$SRC" && patch -p1 < "$p"); done
A=$SRC/android
sed -e 's/versionName="1.0"/versionName="x"/' "$A/AndroidManifest.xml" > "$B/AndroidManifest.xml"
"$T/aapt" package -f -m -J "$B/gen" -M "$B/AndroidManifest.xml" -S "$A/res" -I $SDK/platforms/android-19/android.jar
find "$A/src" "$B/gen" -name '*.java' > "$B/files.txt"
javac -nowarn -d "$B/classes" -source 1.7 -target 1.7 -bootclasspath $SDK/platforms/android-19/android.jar -implicit:none @"$B/files.txt" 2>&1 | tail -6
(cd "$B" && jar cf classes.jar -C classes .)
"$T/dx" --dex --output="$B/classes.dex" "$B/classes.jar"
cp "$B/classes.dex" /out/$NAME/; chown -R "${HOST_UID:-0}:${HOST_GID:-0}" /out/$NAME; ls -la /out/$NAME/classes.dex

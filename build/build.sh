#!/usr/bin/env bash
# usage: build.sh <name> [patch ...]  - builds V2.5 native libs into /out/<name>
set -euo pipefail
NAME=$1; shift
SRC=/tmp/src/rockbox-y1; B=/tmp/b
mkdir -p /tmp/src "$B" /out/$NAME
cp -a /v25/11_rockbox_android/rockbox-y1 /tmp/src/
find "$SRC" -type f \( -name "*.sh" -o -name configure -o -name "*.mk" -o -name "*.make" -o -name "*.pl" -o -name "*.pm" \) -print0 | xargs -0 dos2unix -q || true
sed -i 's/--system=windows-x86_64/--system=linux-x86_64/g' "$SRC/tools/configure"
sed -i 's/-c \$^ \$(GCCOPTS)/-c $< $(GCCOPTS)/' "$SRC/android/android.make"
for p in "$@"; do (cd "$SRC" && patch -p1 < "$p"); done
export ANDROID_SDK_PATH=/tmp/fakesdk JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
mkdir -p $ANDROID_SDK_PATH/platforms/android-19 $ANDROID_SDK_PATH/build-tools/19.1.0
export VERSION="${Y2_VERSION:--260728}"
cd "$B"
printf '201\n480\n360\n' | "$SRC/tools/configure" > /out/$NAME/configure.log 2>&1 || { tail -20 /out/$NAME/configure.log; exit 1; }
mkdir -p libs/armeabi
make -j8 BUILDDATE='-DYEAR=2026 -DMONTH=07 -DDAY=28' "$B/libs/armeabi/librockbox.so" "$B/libs/armeabi/libaiff.so" > /out/$NAME/make.log 2>&1 || { tail -30 /out/$NAME/make.log; exit 1; }
cp libs/armeabi/librockbox.so libs/armeabi/libaiff.so /out/$NAME/
chown -R "${HOST_UID:-0}:${HOST_GID:-0}" /out/$NAME
ls -la /out/$NAME

#!/usr/bin/env bash
# Build the y2-dj ROM from the Y2-Rockbox V2.5 release.
#
# Needs Docker, plus two V2.5 release assets in sources/ (see README):
#   sources/rom_y2.zip                   the V2.5 ROM
#   sources/Y2-Rockbox-V2.5-Source.zip   its GPL source
# Output: build/out/rom/rom_y2.zip, flashable with the Innioasis Updater.
# Optional: SPLASH_LOGO=path/to/logo.png replaces the boot still (logo.bin) and
# the boot animation with that logo (needs Pillow on the host). Unset keeps stock.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
IMAGE=y2-rockbox-build
ROM_SHA=bbdd139a9a52f90570ef04dec4aeb143a361a1d28a90f7be6d37d44c554bee9a
SRC_SHA=3873095f72f7be3925f9d538cd63e9e3fae060fc8b76020345fa68b5548bca41

check() {
    [ -f "$1" ] || { echo "missing $1 (see README)"; exit 1; }
    [ "$(shasum -a 256 "$1" | cut -d' ' -f1)" = "$2" ] || { echo "$1 is not the V2.5 release file"; exit 1; }
}
check sources/rom_y2.zip $ROM_SHA
check sources/Y2-Rockbox-V2.5-Source.zip $SRC_SHA

if [ ! -d sources/v2.5/Y2-Rockbox-V2.5-Source ]; then
    mkdir -p sources/v2.5 && unzip -q sources/Y2-Rockbox-V2.5-Source.zip -d sources/v2.5
fi
docker image inspect $IMAGE >/dev/null 2>&1 || docker build --platform linux/amd64 -t $IMAGE build
mkdir -p build/out

# The Now Playing theme ships as the ROM's default MacClassic-Dark theme. Its
# hash is part of Rockbox's resource version, so a Y2 unpacks the resources
# again exactly when the theme changes (V2.5's own version is 29).
THEME=themes/MacClassic-Dark-Y2DJ.wps
RESOURCE_VERSION="29-y2dj-$(shasum -a 256 "$THEME" | cut -c1-8)"

run() {
    docker run --rm --platform linux/amd64 -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
        -e Y2_RESOURCE_VERSION="$RESOURCE_VERSION" \
        -v "$ROOT/sources/v2.5/Y2-Rockbox-V2.5-Source:/v25:ro" -v "$ROOT/sources:/src:ro" \
        -v "$ROOT/build:/bld:ro" -v "$ROOT/themes:/themes:ro" -v "$ROOT/build/out:/out" \
        -w /out $IMAGE bash -c "$1"
}

echo "== native libraries"
run "bash /bld/build.sh patched /bld/patches/y2dj-playlists-aiff.patch /bld/patches/y2dj-title-display.patch /bld/patches/y2dj-volume-keys.patch"
echo "== java"
run "bash /bld/build_java.sh java /bld/patches/y2dj-launch-guard.patch /bld/patches/y2dj-volume-keys.patch"
rm -f build/out/patched/bootanimation.zip build/out/patched/logo.bin
if [ -n "${SPLASH_LOGO:-}" ]; then
    echo "== boot splash from $SPLASH_LOGO"
    unzip -o -q sources/rom_y2.zip logo.bin -d build/out/splash-stock
    python3 -I tools/make_splash.py "$SPLASH_LOGO" build/out/splash \
        --stock-logo-bin build/out/splash-stock/logo.bin --pad-to 658280
    cp build/out/splash/bootanimation.zip build/out/splash/logo.bin build/out/patched/
fi
echo "== app, vold and ROM"
run '
set -e
mkdir -p /tmp/x /tmp/rom /out/rom
cd /tmp/x && unzip -q -o /src/rom_y2.zip system.img && simg2img system.img sys.raw
debugfs -R "dump /app/Rockbox.apk /tmp/x/Rockbox.apk" sys.raw 2>/dev/null
debugfs -R "dump /bin/vold /tmp/x/vold" sys.raw 2>/dev/null
debugfs -R "dump /lib/libmisc.so /tmp/x/libmisc.so" sys.raw 2>/dev/null
rm -f system.img sys.raw
cd /out
python3 /bld/patch_vold.py /tmp/x/vold patched/vold && chmod 755 patched/vold
python3 /bld/patch_libmisc.py /tmp/x/libmisc.so patched/libmisc.so \
    .rockbox/wps/MacClassic-Dark.wps=/themes/MacClassic-Dark-Y2DJ.wps
python3 /bld/make_apk.py /tmp/x/Rockbox.apk java/classes.dex patched patched/Rockbox.apk
python3 /bld/make_rom.py /src/rom_y2.zip patched rom/rom_y2.zip
chown -R "$HOST_UID:$HOST_GID" /out
'
echo "== verify"
run 'python3 /bld/verify_rom.py /src/rom_y2.zip /out/rom/rom_y2.zip /out/patched /themes "$Y2_RESOURCE_VERSION"'
shasum -a 256 build/out/rom/rom_y2.zip

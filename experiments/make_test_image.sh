#!/bin/sh
# EMULATION ONLY: builds a 512 MiB MBR + FAT32 disk image with a rekordbox-style
# skeleton (empty placeholder dirs, no real export.pdb / audio). It shows the
# partitioning a card should have; it proves nothing about CDJ compatibility.
#
# Note: `hdiutil create -fs MS-DOS` silently makes FAT16 (inside a partition
# typed 0x0B FAT32) at this size, so format explicitly with diskutil FAT32.
set -eu
IMG=${1:-y2-test-fat32.dmg}
rm -f "$IMG"
hdiutil create -size 512m -layout NONE "$IMG" >/dev/null
DEV=$(hdiutil attach -nomount "$IMG" | awk 'NR==1{print $1}')
diskutil eraseDisk FAT32 Y2TEST MBRFormat "$DEV" >/dev/null
MNT=/Volumes/Y2TEST
mkdir -p "$MNT/PIONEER/rekordbox" "$MNT/PIONEER/USBANLZ" "$MNT/Contents" "$MNT/Music"
echo "placeholder: real export comes from desktop rekordbox" > "$MNT/PIONEER/README.txt"
diskutil info "${DEV}s1" | grep -E "File System Personality|Partition Type|Volume Name|Disk Size"
fdisk "$DEV" 2>/dev/null | sed -n '5,6p'
python3 -I "$(dirname "$0")/../tools/card_manifest.py" snap "$MNT" manifest-before.json
date > "$MNT/Contents/fake-cdj-write.txt"   # simulate an owner writing
python3 -I "$(dirname "$0")/../tools/card_manifest.py" snap "$MNT" manifest-after.json
python3 -I "$(dirname "$0")/../tools/card_manifest.py" diff manifest-before.json manifest-after.json || true
hdiutil detach "$DEV" >/dev/null

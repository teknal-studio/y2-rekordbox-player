# y2-dj

Turn an Innioasis Y2 pocket player into a mini rekordbox: browse your rekordbox playlists on the Y2, and plug the same microSD into a CDJ.

Prototype. It runs on one Y2 so far; expect rough edges.

## What works

- Rekordbox playlists and folders on the Y2, nested and in rekordbox order (see `tools/pdb_playlists.py`)
- AIFF files exported by rekordbox, which stock Y2-Rockbox skips
- Track titles in playlist lists, like a CDJ
- The Y2 in USB storage mode on a CDJ-3000, an OPUS-QUAD and over Pro DJ Link
- The microSD shows up as the first USB drive

Not working yet: one XDJ-RX3 did not read it (untested since the drive order change), and playlists must be regenerated on a computer after each rekordbox export.

## How it fits together

- **Firmware:** [Y2-Rockbox](https://github.com/SPYCEMAGIC/Y2-Rockbox) V2.5 with the patches in `build/patches/`, plus a small change to Android's storage service so the card is the first USB drive.
- **Playlists:** `tools/pdb_playlists.py` reads `PIONEER/rekordbox/export.pdb` from the card and writes a `Playlists/` folder that Rockbox browses.
- **Flashing:** the [Innioasis Updater](https://github.com/y1-community/Innioasis-Updater).

Details and device findings are in `docs/device-notes.md`; the original research is in `docs/research.md`.

## Build the ROM

You need Docker. The build runs an x86_64 Linux container, which works under Rosetta on Apple silicon.

1. Download two assets from the [Y2-Rockbox v0.2.5-beta release](https://github.com/SPYCEMAGIC/Y2-Rockbox/releases/tag/v0.2.5-beta) into `sources/`: `rom_y2.zip` and `Y2-Rockbox-V2.5-Source.zip`. The script checks their SHA-256.
2. Run `./build/build_all.sh`. The first run builds the toolchain image, which takes a while.
3. The ROM is `build/out/rom/rom_y2.zip`.

The Rockbox app is re-signed with a key generated on your machine at `build/out/y2dj-debug.keystore`. Keep using the same key for later builds. Never commit it.

## Install

Flashing replaces the Y2's firmware and erases its internal storage. Back up first if you care about anything on it.

1. Turn the Y2 off and take the microSD card out.
2. In the Innioasis Updater, choose your built `rom_y2.zip`, click Start Flash, then plug the Y2 in without holding any buttons.
3. After "Flash Complete", unplug, press the pinhole once, and power on.
4. Put the card back in.

## Put your playlists on the card

After exporting your library to the card from rekordbox, with the card mounted on your computer:

```sh
python3 -I tools/pdb_playlists.py /Volumes/CARD/PIONEER/rekordbox/export.pdb --playlists /tmp/Playlists
cp -R /tmp/Playlists /Volumes/CARD/
python3 -I tools/stamp_card_playlists.py /tmp/Playlists /Volumes/CARD
```

Then, on the Y2, open a `.cfg` file containing these lines from the file browser once:

```
playlist catalog directory: /storage/sdcard1/Playlists
sort playlists: oldest
```

## License

GPL-3.0-or-later. See `LICENSE` and `NOTICE.md`. This repo contains no firmware images; you build the ROM from the official V2.5 release yourself.

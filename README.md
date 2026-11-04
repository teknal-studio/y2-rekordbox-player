# y2-rekordbox-player

**Your rekordbox crate, in your pocket.**

Turn an Innioasis Y2 MP3 player into a personal listening device for your rekordbox library. Study your tracks on the way to the gig, then plug the same device into a CDJ when you get there and DJ from a knockoff iPod like a baller. How rad is that?

This is a little passion project, inspired by watching Dammit Jeff on YouTube.

> [!WARNING]
> **Disclaimer:** this is a prototype. It has been tested on one Y2 so far, so expect rough edges. Flashing replaces your Y2's firmware and erases its internal storage.
>
> This project is not affiliated with rekordbox, AlphaTheta, Pioneer DJ or Innioasis. Pull requests are welcome.

## Yes, it's funny to DJ from a knockoff iPod. But why?

Hyper-convenient streaming services and online stores like Beatport have cost us something special in our relationship with music. Sometimes doing things the hard way, with more friction, is better.

Much of the music I play in my sets has a personal story behind it. We don't hear "I found this track at Media Play" or "I found this album at a record store" anymore. We're fed music by algorithms on Spotify, Apple Music and Tidal. I appreciate the convenience, but "I found this track on Spotify" isn't a compelling or heartwarming story.

This is how I'm fighting back against the loss of ownership in media. I'm a DJ. I hunt, dig and curate music so that whoever shows up to my sets has the best night of their life. That's my job as a DJ and a musician. I still want to share the journey of these tracks and why I love them, and who better to share it with than the people who come to my shows?

**Own your media. Reject "you will own nothing and be happy."**

The music you put on this device is *yours*. And if you DJ, you can share your journey and your story through curated sound and intentional listening.

## What is this?

This code turns your Innioasis Y2 into a mini rekordbox. Browse your rekordbox playlists on the Y2, then put the same microSD into a CDJ, or plug the Y2 straight into one.

## What works

- Rekordbox playlists and folders on the Y2, nested and in rekordbox order (see `tools/pdb_playlists.py`)
- AIFF files exported by rekordbox, which stock Y2-Rockbox skips
- Track titles in playlist lists, like a CDJ
- The Y2 in USB storage mode on a CDJ-3000, an OPUS-QUAD and over Pro DJ Link
- The microSD shows up as the first USB drive

**Not working yet:** one XDJ-RX3 did not read it (untested since the drive order change), and playlists must be regenerated on a computer after each rekordbox export.

## How it fits together

- **Firmware:** [Y2-Rockbox](https://github.com/SPYCEMAGIC/Y2-Rockbox) V2.5 with the patches in `build/patches/`, plus a small change to Android's storage service so the card is the first USB drive.
- **Playlists:** `tools/pdb_playlists.py` reads `PIONEER/rekordbox/export.pdb` from the card and writes a `Playlists/` folder that Rockbox browses.
- **Flashing:** the [Innioasis Updater](https://github.com/y1-community/Innioasis-Updater).

Details and device findings are in `docs/device-notes.md`; the original research is in `docs/research.md`.

## Build the ROM

You need Docker. The build runs an x86_64 Linux container, which works under Rosetta on Apple silicon.

1. Download two assets from the [Y2-Rockbox v0.2.5-beta release](https://github.com/SPYCEMAGIC/Y2-Rockbox/releases/tag/v0.2.5-beta) into `sources/`: `rom_y2.zip` and `Y2-Rockbox-V2.5-Source.zip`. The script checks their SHA-256.
2. Run `./build/build_all.sh`. The first run builds the toolchain image, which takes a while.
   To use your own boot splash, pass a transparent PNG logo: `SPLASH_LOGO=path/to/logo.png ./build/build_all.sh`. It replaces the boot still (`logo.bin`) and the spinning boot animation.
3. The ROM is `build/out/rom/rom_y2.zip`. The build checks it against the stock ROM with `build/verify_rom.py` before it finishes.

The Rockbox app is re-signed with a key generated on your machine at `build/out/y2dj-debug.keystore`. Keep using the same key for later builds. Never commit it.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The tests need Python 3 with Pillow, and a C compiler for the playlist navigation test. Two groups skip themselves unless their inputs are there: the patch tests need the V2.5 source in `sources/v2.5` (the build unpacks it), and the ROM test needs Docker and a finished build. The tests use synthetic data only, never a real library or device dump.

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

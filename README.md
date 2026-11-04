# y2-rekordbox-player

Use your Innioasis Y2 MP3 Media Player as both a personal listening device for your Rekordbox compatible library. Then plug your device into a CDJ like a baller when you show up and DJ from a knockoff iPod. How rad would that be? 

Study your tracks and get intentionally intimate with a dedicated device specifically for listening to your DJ Crate on your way to a gig

This is a little passion project inspired by watching Dammit Jeff on YouTube. 

## Yes, it's funny to DJ from a knockoff iPod, but why?
With the advent of hyper convenient streaming services and online music store like Beatport, we've unfortunately lost something special with our relationship to music. Sometimes doing things the hard way with more friction is better. Much of the music that I play in my DJ sets has a personal relationship to me. 

We don't hear stories of "I found this track at Media Play" or "I found this album at a record store." We're algorithmically fed music on Spotify, Apple Music, Tidal, etc. and while I can appreciate the convenience of these services, "I found this track on Spotify" isn't really a compelling or heartwarming story about how I found a track.

This is how I'm fighting back against the loss of ownership in media. I'm a DJ. I hunt, dig, and curate music so I can deliver to whoever shows up to my sets the best night of their life. It's my job to do that as both a DJ and musician. I still want to share the journey of these tracks and why I love them so much, and who better to share that with that those who come to my shows?

Own your media. Reject "you will own nothing and be happy."

The music you put on this device is YOURS. And if you're DJing, you can share your journey and story through the power of curated sound and intentional listening.

## What is this?
This code turns your Innioasis Y2 pocket player into a mini rekordbox: browse your rekordbox playlists on the Y2, and plug the same microSD into a CDJ, or plug the device directly into a CDJ.

DISCLAIMER: This is a prototype. I've tested it on one Y2 so far; expect rough edges. Pull requests are welcome. This project is not affiliated with Rekordbox, AlphaTheta, or Pioneer DJ.

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

# Device notes

Results from one Innioasis Y2 (stock firmware FM_3.2.4, MT6582, Android 4.4.2) with a 512 GB exFAT microSD holding a full rekordbox USB export, October–November 2026.

## USB storage

- Stock and Y2-Rockbox present pure USB mass storage (`0BB4:0001`), no ADB, with two LUNs: LUN 0 is internal storage (5.9 GB FAT32, no partition table), LUN 1 is the microSD as a whole disk (MBR).
- Works as a rekordbox device on a CDJ-3000, over Pro DJ Link, and on an OPUS-QUAD.
- Did not work on one XDJ-RX3 at a venue. Not reproduced. Pioneer says its players read only the first partition, so the card being LUN 1 is the main suspect. AlphaTheta lists exFAT as supported on the XDJ-RX3 (a forum post says from firmware 1.11).
- `build/patch_vold.py` makes the card LUN 0 and internal storage LUN 1. The kernel fixes the LUN count at two, so a second slot remains.
- The CDJ writes to the card: `export.pdb` grew from 774,144 to 790,528 bytes after use and still parses.
- macOS writes `._` files on exFAT and FAT. Removing them changes folder times, which matters for playlist order (see below).

## Playlists

- The stock player shows `.m3u8` files but does nothing when one is opened, so Rockbox is required.
- `tools/pdb_playlists.py` reads `PIONEER/rekordbox/export.pdb` and writes a nested `Playlists/` tree that mirrors the rekordbox folders and playlists.
- Track paths must be absolute (`/storage/sdcard1/Contents/...`). Rockbox's `path_remove_dot_segments` removes only one level of consecutive `..`, so relative paths from nested playlists fail.
- Order: Rockbox sorts the catalog by name or date. The generator stamps modified times in rekordbox order (10 seconds apart, wider than FAT's 2-second resolution), and `sort playlists: oldest` in the Rockbox config uses them. `tools/stamp_card_playlists.py` reapplies the times after copying to a card and cleaning `._` files.
- Settings to load once from Files (a `.cfg` opened in the file browser is applied):

  ```
  playlist catalog directory: /storage/sdcard1/Playlists
  sort playlists: oldest
  ```

- After a new rekordbox export, regenerate and restamp. The goal is to read `export.pdb` on the device instead, so a plain rekordbox sync is enough.

## Rockbox fixes in this repo

| Patch | Problem | Fix |
|---|---|---|
| `y2dj-playlists-aiff.patch` | 455 of 696 AIFFs skipped: rekordbox/Core Audio writes a 4 KiB `FLLR` chunk and the codec only searched the first 1024 bytes | Search the first 8192 bytes |
| same | Playlist catalog hid folders | Show directories when the M3U filter is on, sorted with playlists |
| same | Back from a nested playlist went to the top-level Playlists folder | Reopen the folder that holds the playlist, and count levels from the Playlists folder, so Back goes up one level at a time |
| `y2dj-launch-guard.patch` | After turning USB storage off, Rockbox sometimes stuck on "Restoring storage..." because a stale preference denied its own restart | Allow Rockbox's own restart when both saved routes are blank and the boot route property says Rockbox |
| `y2dj-title-display.patch` | Playlist track lists showed file names | Default Track Display to "Title from ID3 tags" (falls back to the file name) |
| `y2dj-volume-keys.patch` | The volume buttons did nothing. The keypad reports each press as a 40–75 ms down/up pair (seen in `y2_p12_volume_hold_v5.log`), and the polled button path can miss it | Post volume presses through the button queue, like the wheel, and log `RockboxVolume:` markers for each volume key |
| `y2dj-storage-guard.patch` | After unplugging from a CDJ-3000, Rockbox came up with default settings (yellow menus, small font). Android restarted the `START_STICKY` Rockbox service while internal storage was still shared over USB; it found no `config.cfg` and began saving defaults (`config.cfg.new`). `y2dj-launch-guard.patch` let that restart through, because the restarted process reads blank route preferences | `RockboxService.doStart` refuses to start Rockbox, and stops the service, unless `/storage/sdcard0` is mounted and writable. The activity's storage gate starts it once storage is back |

Titles come from file tags, not from rekordbox, so titles edited only in rekordbox will differ.

The launch guard fix can't be triggered on demand. Look for `staleRouteRecovered=true` in the marker log to see it act.

## Flashing

- The Innioasis Updater flashes a full ROM over a plain plug-in (no buttons): it drives mtkclient with the Y2 preloader and `MTK_AllInOne_DA.bin`. Take the card out first. After "Flash Complete", unplug, press the pinhole once, then power on.
- A full ROM flash resets internal storage, including Rockbox settings.
- Boot keys: Volume Up boots the other player (stock), Volume Down opens Boot Settings.

## Backup

- mtkclient can read the whole eMMC (`rf`, about 2.4 MB/s, 7.8 GB). The eMMC has no GPT; the MBR sits at 12 MiB.
- So far it has only worked in BROM mode (hold Volume Up + Volume Down while plugging in) with `--preloader preloader_eastaeon82_wet_kk.bin`. The next test is the Updater's plain plug-in method with its DA loader.
- A backup includes `/data` and device identifiers. Keep it private.
- Restoring from a backup has not been tested.

# Notices

y2-dj is licensed under the GNU General Public License, version 3 or (at your option) any later version. See `LICENSE`.

It builds on, and its patches modify:

| Project | License | Use here |
|---|---|---|
| [Rockbox](https://www.rockbox.org/) | GPL-2.0-or-later | Player firmware the patches apply to |
| [SPYCEMAGIC/Y2-Rockbox](https://github.com/SPYCEMAGIC/Y2-Rockbox) and its `rockbox-y1` fork | GPL-2.0-or-later | The V2.5 release this repo builds on |
| [y1-community/Innioasis-Updater](https://github.com/y1-community/Innioasis-Updater) | GPL-3.0 | Flashing tool used to install the ROM |
| [mtkclient](https://github.com/bkerler/mtkclient) | GPL-3.0 | Backup and flashing over USB |

The `export.pdb` parser follows Deep Symmetry's published analysis of the rekordbox DeviceSQL format ([crate-digger](https://github.com/Deep-Symmetry/crate-digger)).

## Not included

This repo contains no firmware images or vendor binaries. The V2.5 ROM includes Android, MediaTek and Innioasis components that are not covered by the licenses above. `build/build_all.sh` patches a copy of the V2.5 ROM that you download yourself, and the built ROM stays on your machine.

Rockbox, rekordbox, CDJ, Pioneer DJ, AlphaTheta and Innioasis are trademarks of their owners. This project is not affiliated with any of them.

# Y2 ↔ rekordbox/CDJ shared-library research

Investigation date 2026-10-27, before the device arrived. Later device results are in `docs/device-notes.md`.

Tags: **[E]** evidence (file:line or URL, SHA pinned below) · **[I]** inference · **[P]** needs physical test.

## Pinned sources

| Repo | SHA (inspected) | Role |
|---|---|---|
| SPYCEMAGIC/Y2-Rockbox (`main`) | `c294e90843f5aeefa887e7ed43cc53b8e05973e3` (commit 2026-09-06; = Beta V2 docs, **not** the V2.5 release) | Community Y2 adaptation wrapper: build/packaging scripts, docs, submodule |
| SPYCEMAGIC/Y2-Rockbox tag `v0.2.5-beta` | tag object `ef4b0d4d…`, commit **`cc5cde73b452ea545cfd11943db2955d297fc385`** (on branch `release/v2.5-public-full-3.2fm`, head `329203e2…`; not on `main`) | V2.5 release wrapper tree |
| SPYCEMAGIC/rockbox-y1 (submodule, published) | `5073cc9d380f8d01016ace6dceea89e0684038c1` (branch `beta2/p17-centre-context-transport`; pinned by `v0.2.0-beta` = `a2fdf49d…` and by `main`) | Rockbox source with the Y2 Android-hosted changes |
| SPYCEMAGIC/rockbox-y1 (submodule pinned by `v0.2.5-beta`) | **`573485e9903ee01d0039558c355bb259cb509e1e` — not published** (GitHub API 422 on SPYCEMAGIC, multiwirth and rockbox-y1 forks; not reachable via upload-pack) | Exists only as the `Y2-Rockbox-V2.5-Source.zip` tree |
| `Y2-Rockbox-V2.5-Source.zip` (release asset) | sha256 `3873095f72f7be3925f9d538cd63e9e3fae060fc8b76020345fa68b5548bca41` (matches release SHA256SUMS.txt) | GPL corresponding source for V2.5 |
| y1-community/rockbox-y2-rom | `88b5a6112cf8ba910009bb8c98f573a32c3524f5` | Mirror/repackaging CI only (no source) |
| rockbox-y1/rockbox | `y1` = `e8992f60d34eddf3a84902a4e9c5a282a2e9f2d4`, `rebase-upstream` = `9c92b93a5d582b3819a119162a14ad0b4178d2cd` (API only, not cloned) | Y1 Android fork, grandparent of the Y2 code |
| SchulzCode/Y2Linux (`main`) | `36ed3d879986ec46f3d9ecd1a6ce33f7f34974da` | Alternative native Linux 6.18 + Buildroot OS |
| y1-community/Innioasis-Updater | `63444c8ea2bc9efe89b5cf46614880f3b7fabd92` | Flashing GUI (bundles SP Flash Tool + mtkclient) |
| SPYCEMAGIC/Y2-Rockbox release `v0.2.5-beta` `rom_y2.zip` | sha256 `bbdd139a9a52f90570ef04dec4aeb143a361a1d28a90f7be6d37d44c554bee9a` (matches release SHA256SUMS.txt) | Stock 3.2FM-based full ROM; boot.img/system.img inspected offline |

Clones are in `sources/` (gitignored). The submodule is a blob-less sparse checkout in `sources/rockbox-y1-spyce`, with a full depth-1 checkout of `5073cc9` in `sources/rockbox-y1-5073cc9`. The V2.5 source zip is unpacked at `sources/v2.5-source-zip/`, and a Git export of `cc5cde7` + `5073cc9` is at `sources/v2.5-git-export/`.

## Provenance

**Bottom line:** provenance checks out. This is a **community-linked Y2 adaptation of Rockbox by one developer (SPYCEMAGIC)**, not upstream Rockbox and not an Innioasis/vendor project. Provenance is the only thing verified here. These remain **unverified**:
- that the source reproduces the release binaries;
- the release-source vs Git match beyond what the diff below shows;
- any CDJ compatibility.

- **[E]** The community distribution points here: `y1-community/rockbox-y2-rom` `mirror-release.yml:18` sets `UPSTREAM_REPO: SPYCEMAGIC/Y2-Rockbox`, and its README credits SPYCEMAGIC.
- **[E]** Fork chain (GitHub `parent`/`source` fields): `Rockbox/rockbox` → `rockbox-y1/rockbox` → `multiwirth/rockbox-y1` → `SPYCEMAGIC/rockbox-y1` (`source` = Rockbox/rockbox for all three). Y2-Rockbox `.gitmodules` points `11_rockbox_android/rockbox-y1` at `SPYCEMAGIC/rockbox-y1`. Y2-Rockbox itself is not a fork.
- **[E]** Release `v0.2.5-beta` ships `rom_y2.zip`, `SHA256SUMS.txt` and `Y2-Rockbox-V2.5-Source.zip`, plus docs and license files. The SHA-256s of both zips match `SHA256SUMS.txt`. Caveat: the sums come from the same release, so they prove integrity, not authenticity.
- **Contributor / commit-author counts** (the "one contributor" observation applies only to the wrapper):

| Repo | Contributors (GitHub API, incl. anonymous) | Commit authors |
|---|---|---|
| SPYCEMAGIC/Y2-Rockbox (wrapper) | 1 (SPYCEMAGIC, 7 commits on `main`) | All 352 commits on all refs: SPYCEMAGIC/SPYCE |
| SPYCEMAGIC/rockbox-y1 (submodule) | 281 (inherited Rockbox + Y1 history) | Y2 work = **75 commits, all SPYCEMAGIC**, on top of `multiwirth/rockbox-y1` `y1` (`8584feb0`, ahead 75 / behind 0). The fork's own `y1` branch is identical to multiwirth's. |
| multiwirth/rockbox-y1 | 281 | — |
| rockbox-y1/rockbox (Y1 fork) | 313 | vs its `y1`: 79 ahead (SPYCEMAGIC 75, rockbox-y1 3, Patrick 1) / 179 behind |
| Rockbox/rockbox `master` | (upstream) | vs `5073cc9`: 110 ahead / 1762 behind, merge base `648675dd0c` (of the first 100 listed: SPYCEMAGIC 65, rockbox-y1 34, Patrick 1) |

  So the code base carries hundreds of upstream Rockbox authors, but **all Y2-specific code and every release is from one person.** That is normal for a hobby port, but there's no second reviewer: bus factor 1.
- **[E] V2.5 release source vs Git** (`diff -rq` of the unpacked zip vs `git archive cc5cde7` with `5073cc9` in the submodule slot; 12,462 files in the zip):
  - **Wrapper:** byte-identical to tag commit `cc5cde7`. The only extra file is `SOURCE-COMMITS.txt`, which itself states parent `cc5cde7…` and submodule `573485e…`.
  - **Submodule:** the zip equals published `5073cc9` except for **3 files**: `android/AndroidManifest.xml` (versionCode 127→137, versionName → `1.0-beta-v2.5-stock-3.2.0-dark-default-rc1`), `RockboxService.java` (build string, plus a default theme of MacClassic-Dark with inverted colours) and `Y2Marker.java` (build string). So the unpublished `573485e` appears to be `5073cc9` plus a version/theme-default commit **[I]**: no functional, USB or storage changes.
  - **Only in Git:** 7 symlinks the zip dropped (`manual/rockbox_interface/images/iaudio{m5,x5}-remote.{pdf,png,svg}`, `uisimulator/bitmaps/UI-erosqnative.bmp`). These are manual and simulator assets, harmless, but recreate them for manual/sim builds.
  - **`c294e90` vs the release:** `main` is 10 commits behind the tag line (`699f101`…`cc5cde7` are V2.5 RC/release commits; the diff is 1,679 files, mostly `config/`, `00_tools/` and `Progress logs/`). `c294e90` is **not** the release wrapper, and `5073cc9` is the V2.0 pin, the published parent of the V2.5 pin.
  - **Binaries/prebuilts in the zip:** no APK, `.so`, `.dex`, `.jar` or firmware images. The wrapper has only text/scripts/JSON/images plus one log blob (`Progress logs/…/05-route-environment.bin`). The submodule's binaries are inherited from upstream Rockbox and identical to Git: `firmware/drivers/libertas/firmware/*`, `utils/jz4740_tools/windows_driver/*`, `apps/plugins/puzzles/fonts.zip`, beecrypt and MTP util files. The zip also carries project working files: `Progress logs/` (about 500 test logs), `04_theme_analysis/` (8 MB, including listings and extracted source text from the stock Innioasis launcher; vendor material, licensing unclear), and agent handoff notes (`CODEX.md`, `AGENTS.md`, `*_Codex_Handoff.md`, read as data only).
  - **Not verified:** that building this tree reproduces the V2.5 APK or `system.img` byte for byte. There's no build-reproducibility evidence, and no build was run.


---

## 1. Buildable source vs ROM packaging; hosted vs native

- **[E]** `y1-community/rockbox-y2-rom` is packaging only. The tree is `README.md`, `agents.md` and one workflow. `mirror-release.yml:18` sets `UPSTREAM_REPO: SPYCEMAGIC/Y2-Rockbox`. The workflow downloads SPYCEMAGIC's `*Innioasis*.zip`, overlays it on a base ROM, converts the images with `simg2img` and republishes `rom_y2.zip`.
- **[E]** The Y2 project with buildable source is **SPYCEMAGIC/Y2-Rockbox** (whether it actually builds and reproduces the releases is unverified; see Provenance). Its README:3 says "Rockbox for the Innioasis Y2, hosted inside its original Android 4.4.2 firmware". `.gitmodules` points `11_rockbox_android/rockbox-y1` at `SPYCEMAGIC/rockbox-y1`, and `00_tools/` holds about 94 build, assemble and validate scripts.
- **[E]** Lineage is `rockbox-y1/rockbox` → `multiwirth/rockbox-y1` → `SPYCEMAGIC/rockbox-y1` (GitHub fork parents). Compared with rockbox-y1/rockbox `y1`, the pinned commit is 79 commits ahead and 179 behind (diverged). So rockbox-y1/rockbox is the Y1 ancestor, not the Y2 source.
- **[E]** It is a **hosted target** (Rockbox as an Android APK), not native. It uses `android/` (APK, ant build), `firmware/target/hosted/android/` and `firmware/export/config/android.h`. Y2-specific Java lives at `android/src/org/rockbox/Y2*.java`.
- **[E]** Hardware per README:55-57: Android 4.4.2 / SDK 19, MediaTek **MT6582**, board `eastaeon82_wet_kk`. Beta V2 needs Stock 3.1.7. The V2.5 prerelease (`v0.2.5-beta`, 2026-09-29) rebases onto Stock 3.2FM and ships `Y2-Rockbox-V2.5-Source.zip`.
- **[E]** Git `main` (2026-09-06) lags V2.5. The release is tag `v0.2.5-beta` → `cc5cde7` on a release branch; see Provenance for the zip diff.
- **Responsibilities [E/I]:**
  - The stock Innioasis vendor blobs own boot, kernel, USB and vold: preloader, LK/UBOOT, BOOTIMG (kernel) and the Android system.
  - Y2-Rockbox repacks the UBOOT, BOOTIMG, RECOVERY, LOGO and ANDROID payloads (README "accepted archive"), but its source changes are the APK plus boot-route brokers (`00_tools/y2_v8x_boot_*_broker.sh`).
  - **[I]** No kernel source for the stock MT6582 Y2 kernel was found in any inspected repo. The USB gadget stack is therefore a vendor binary we cannot rebuild on the Rockbox route.
- **Y2Linux [E]:** a mainline Linux 6.18 port, kernel config in-tree (`kernel/config/production.config`). It keeps the stock preloader and LK and replaces Android (README). This is the only route where the kernel, and so the USB gadget, is under our control.

## 2. USB device controller, kernel config, mass storage (UMS) vs MTP

**Verdict:**

| Route | SD as USB mass storage (block device) | Status |
|---|---|---|
| Stock Android / Y2-Rockbox | Android 4.4 UMS (`UsbStorageActivity`, vold "share") | **Supported** [E]; microSD-as-own-LUN and CDJ-as-host still **[P]** |
| Y2Linux | `CONFIG_USB_CONFIGFS_MASS_STORAGE=n`; MTP+ECM only, by design | **Missing-but-buildable** [E for the config, I for buildability] |

Evidence:
- **[E]** Y2-Rockbox handles the legacy UMS lifecycle:
  - `android/AndroidManifest.xml:107,111` registers `MEDIA_SHARED` and `UMS_CONNECTED`.
  - `Y2StorageReceiver.java` launches `com.android.systemui.usb.UsbStorageActivity` on `UMS_CONNECTED` (around lines 23-51 and 149-168).
  - The same file treats `MEDIA_UNMOUNTED`/`EJECT`/`SHARED` as an "expected Rockbox exit" and a "single-owner storage event", then returns once the volume is mounted again.
  - That is the Android 4.x UMS model: vold unmounts the volume from Android and exports the raw block device to the host.
- **[E, project-reported]** The developer reports observing it physically on a Y2 as a block device, not MTP (not independently reproduced). `00_project_docs/Y2_FIRMWARE_FLASH_RUNBOOK.md:137,141` says the probe "exposed USB mass storage, and wrote `F:\y2_probe_v7_boot_marker.txt`". A Windows drive letter means MSC; MTP gets no drive letter.
- **[E]** Release notes claim "USB storage enable, file transfer, safe eject, disable and Rockbox return" and "microSD playback" (`Y2_ROCKBOX_BETA_V0.1.0_RELEASE.md:51-52`). README:127 says "safely eject every mounted Y2 volume". The plural suggests internal and microSD as separate LUNs **[I]**.
- **[E]** Y2Linux, in `kernel/config/production.config`:
  - Lines 104-126: `CONFIG_USB_GADGET=y`, `CONFIG_USB_MUSB_HDRC=y`, `CONFIG_USB_MUSB_DUAL_ROLE=y`, `CONFIG_USB_INVENTRA_DMA=y`, `CONFIG_USB_CONFIGFS=y`, `CONFIG_USB_CONFIGFS_F_FS=y` (used for MTP).
  - Lines 122-123 explicitly set **`CONFIG_USB_CONFIGFS_MASS_STORAGE=n`** and **`CONFIG_USB_MASS_STORAGE=n`**.
  - `tools/platform/y2_platform/usb.py:1-3` says "Linux is the only block/filesystem owner. No block-export function is selectable." `capabilities.json:92` has `"filesystem_mass_storage": false`. `docs/architecture/platform-usb-v1.md:33` says "No writable Linux filesystem is exported as USB mass storage."
  - The controller is MUSB, peripheral-only in practice (platform-usb-v1.md:15). Host/OTG is not enabled. That doesn't matter here because the CDJ is the host.
- **[I]** On Y2Linux, adding `f_mass_storage` means enabling `CONFIG_USB_CONFIGFS_MASS_STORAGE`, creating `functions/mass_storage.0/lun.0/file=/dev/mmcblk1` ([kernel docs](https://docs.kernel.org/usb/mass-storage.html)) and unmounting `/media/sd` first. The MUSB UDC has no known blocker for MSC bulk endpoints. The maintainer's single-owner design is a policy choice, not a hardware block. Y2Linux also notes USB transfer stability under load is not yet qualified (platform-usb-v1.md "Historical physical note").
- **[E] Stock USB stack, from the V2.5 ROM** (`rom_y2.zip` above; boot.img unpacked with `tools/unboot.py`). File paths are inside the ramdisk:
  - Kernel `Linux version 3.4.67 ... Mon Jun 1 2026`, MediaTek `mt6582_kk/alps` tree. It contains `drivers/usb/gadget/f_mass_storage.c` and the MediaTek `usb20` MUSB driver (path strings in the zImage). There's no embedded `/proc/config.gz`.
  - `default.prop:9`: **`persist.sys.usb.config=mass_storage,adb`**. Stock boots with the UMS function present by default, as a **composite with ADB**.
  - `init.usb.rc:1-10` sets `sys.usb.vid 0BB4` and chowns `f_mass_storage/lun/file`. `init.usb.rc:66-82` defines `mass_storage` alone (PID `0001`) and `mass_storage,adb` (PID `0C03`). MTP configs (`2008`, `0C02`) also exist.
  - `fstab:9-10`: internal `sdcard0` (`mtk-msdc.0`, `emmc@fat`) and microSD **`sdcard1`** (`mtk-msdc.1`, `auto`), both vold-managed. `init.project.rc:99` sets `SECONDARY_STORAGE /storage/sdcard1`.
  - `system.img` (sparse) contains the strings `/sys/class/android_usb/android0/f_mass_storage/lun/file` **and `.../lun1/file`**. **[I, strong]** vold exports internal storage and microSD as two separate LUNs, so the microSD is its own block device to the host.
- **[I]** CDJ risk: the default composite (MSC + ADB interface). If the CDJ refuses composite devices, `mass_storage`-only (PID 0001) already exists in `init.usb.rc`. It's reachable with `setprop persist.sys.usb.config mass_storage` over ADB or by disabling USB debugging **[P]**.
- **[P]** Still to confirm on hardware:
  - Stock UMS exports the microSD as its own LUN (versus internal only).
  - What VID/PID and interface class the gadget enumerates with: is MSC alone, or composite with ADB/MTP? Some hosts reject composites.
  - Whether a non-PC host (CDJ) triggers `UMS_CONNECTED` and lets the user tap "Turn on USB storage".
  - Whether the CDJ copes with a LUN whose medium appears only after the user enables sharing (empty-reader → media-present Unit Attention).

## 3. SD slot, filesystems, library size, CDJ-3000 requirements

- **[E]** The Y2 has a microSD slot; both projects document microSD playback (Y2-Rockbox v0.1.0 release notes :51; Y2Linux `docs/STORAGE.md`). Y2Linux mounts `vfat`, `exfat` and `ext4` cards (`capabilities.json:29-30`; `media.py:189`) and has FAT/exFAT read-only fallback and repair.
- **[E]** Stock (V2.5 ROM) has an exFAT kernel driver (`[EXFAT] mounted successfully` etc. strings in the 3.4.67 zImage). `system.img` references `/system/bin/mount.exfat` and `/system/bin/fsck.exfat`, and fstab says `vfat`/`auto`. **[I]** vold probably mounts exFAT microSD too. **[P]** confirm with a real exFAT card. Still plan on **FAT32** for the shared card as the safest common format; exFAT is plan B if large files or cards demand it.
- **[E]** The CDJ-3000 manual p.12 says "The unit can play audio files saved on USB mass storage class devices" (manualslib 1909473; B&H PDF 630695). p.34 says not to disconnect while the USB indicator is blinking, because "management data may be deleted or the USB device may become unreadable". p.41 says "A new History is automatically created on a storage device (SD, USB) when it is connected". p.81 says My Settings can be saved to the device.
- **[E, unverified wording]** File systems: third-party spec sheets list FAT16/FAT32/HFS+, and some add exFAT. I could not extract the official spec table this session. **FAT32 is the common denominator of the Y2-stock and CDJ lists [I].** A third-party tester ([djban USB tester](https://djban.com.br/en/rekordbox-usb-tester/)) says the CDJ needs **MBR** rather than GPT. Treat that as [I] until it's confirmed in the manual.
- **[E]** rekordbox USB export page (https://rekordbox.com/en/support/usb-export/): it lists the CDJ-3000 and CDJ-3000X under both the "Device Library" (conventional) and "OneLibrary" formats. The ✓/✗ marks are images I couldn't read via CLI **[P: check in a browser]**.
- **[E]** The CDJ-3000X manual says USB hubs are unsupported and only 8 folder levels are read. Reading is slow with many files.
- **Capacity: no guarantees.**
  - **[E]** FAT32 caps files at 4 GiB.
  - **[I]** microSDXC (>32 GB) arrives exFAT from the factory and must be reformatted to FAT32 (MBR, 32 KiB clusters). The Y2 stock vold and the CDJ must both accept the large FAT32 volume **[P]**.
  - **[E]** Y2Linux claims 120,000-song libraries stay quick (README Beta 8.39). Y2-Rockbox lists "larger internal and microSD libraries" as future work (`FUTURE_FEATURES.md:40`). Rockbox database build time on a large card is **[P]**.
- **[I]** Directory layout: rekordbox writes `PIONEER/` (export DB, `USBANLZ` analysis) and `Contents/<artist>/<album>/` audio. Rockbox plays `Contents/` via file browser or its own tagcache DB in `.rockbox` (on internal storage). The two libraries are independent, so nothing needs regenerating.

## 4. Exclusive filesystem ownership

Model: one owner at a time. The owners are desktop rekordbox (via card reader), the CDJ (via Y2 UMS), and Y2 Android/Rockbox (local mount).

- **[E]** Android UMS gives the host exclusive ownership. Sharing makes vold unmount the volume from Android (`MEDIA_UNMOUNTED`/`MEDIA_SHARED`) before export, and Y2-Rockbox explicitly holds and exits on those (`Y2StorageReceiver.java` "hold for usb-storage", `noteExpectedRockboxExit`). Rockbox therefore cannot write while the CDJ owns the card.
- **[I]** Rockbox keeps its own state (`.rockbox`: settings, tagcache, playlists) on **internal** storage. Keeping it off the shared microSD makes Rockbox a read-mostly owner of the card. Rockbox can still write playlists and bookmarks if asked, so don't save them to the card.
- **[E]** The CDJ writes to the card: History playlists (manual p.41), My Settings (p.81), management data (p.34). **[I]** The rekordbox export DB under `PIONEER/` may also be modified (history, possibly hot-cue banks). Expect writes under `PIONEER/` and none under `Contents/` **[P]**. `tools/card_manifest.py` checks exactly this.
- **[E, emulation]** macOS itself writes `._*` AppleDouble files when it touches the card. The Mac is a writer too, so eject it properly.
- **[P]** Is the CDJ's "stop using USB" / indicator-not-blinking state enough before the user taps "Turn off USB storage" on the Y2? And does the Y2 re-mount cleanly without a fsck prompt?

## 5. Toolchain

- **[E]** The Y2-Rockbox build scripts are WSL/Linux x86_64 bash (`00_tools/build_*_wsl.sh`, `build_y2_simulator_wsl.sh`). They need Android SDK + **NDK r10e** (`ANDROID_NDK_PATH=$HOME/android/android-ndk-r10e`), ant, dos2unix and `apt-get download` SDL debs.
- **[I]** Feasible path: an x86_64 Ubuntu container (Docker/OrbStack under Rosetta) running the WSL scripts unchanged. Native macOS builds of NDK r10e are possible in principle but untested. The Rockbox SDL simulator (`build_y2_simulator_wsl.sh`) is the useful no-hardware target for UI work only. It says nothing about USB.
- Y2Linux builds need Linux with bubblewrap and user namespaces (`docs/BUILDING.md`), so a container or VM is required.

## No-hardware experiment (EMULATION ONLY)

`tools/unboot.py` and `tools/zimg.py` unpack the MTK boot.img and zImage offline; they produced the Section 2 ROM evidence.

`experiments/make_test_image.sh` builds a 512 MiB **MBR + FAT32** image with a `PIONEER/` + `Contents/` skeleton, then exercises `tools/card_manifest.py` snapshot/diff. Results:

- **[E]** `hdiutil create -fs MS-DOS` silently produced **FAT16** inside a partition typed 0x0B (FAT32). Format cards explicitly as FAT32 (`diskutil eraseDisk FAT32 NAME MBRFormat`) and verify with `diskutil info`.
- The manifest diff flags owner writes and macOS `._` noise, and fails only if existing `Contents/` audio changes.
- This shows image layout and tooling only. **It is not CDJ compatibility evidence.**

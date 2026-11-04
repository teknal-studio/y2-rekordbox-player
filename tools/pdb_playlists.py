#!/usr/bin/env python3
"""Read playlists out of a rekordbox USB export (PIONEER/rekordbox/export.pdb).

Read-only. Layout per Deep Symmetry's crate-digger analysis of the DeviceSQL
format. Only the tables needed for playlists are parsed: tracks (0),
artists (2), playlist tree (7), playlist entries (8).

usage: pdb_playlists.py export.pdb [--tree] [--dump-track N] [--m3u OUTDIR]
"""
import argparse
import os
import re
import struct
import sys

T_TRACKS, T_ARTISTS, T_TREE, T_ENTRIES = 0, 2, 7, 8

# Modified times carry the rekordbox order, for "sort playlists: oldest".
ORDER_EPOCH = 1577836800  # 2020-01-01
ORDER_STEP = 10           # seconds, wider than FAT's 2 second resolution


def u8(b, o):
    return b[o]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def dstring(b, o):
    """DeviceSQL string at offset o."""
    kind = b[o]
    if kind & 1:  # short ASCII, length includes this byte
        n = kind >> 1
        return b[o + 1:o + n].decode("ascii", "replace")
    n = u16(b, o + 1)
    raw = b[o + 4:o + n]
    if kind == 0x90:
        return raw.decode("utf-16-le", "replace")
    return raw.decode("latin-1", "replace")


class Pdb:
    def __init__(self, data):
        self.d = data
        self.page_len = u32(data, 4)
        ntables = u32(data, 8)
        self.tables = {}
        for i in range(ntables):
            t, _empty, first, last = struct.unpack_from("<IIII", data, 28 + 16 * i)
            self.tables[t] = (first, last)

    def pages(self, table):
        first, last = self.tables[table]
        seen, idx = set(), first
        while idx not in seen and idx * self.page_len < len(self.d):
            seen.add(idx)
            base = idx * self.page_len
            yield base
            if idx == last:
                break
            idx = u32(self.d, base + 0x0C)

    def rows(self, table):
        d, L = self.d, self.page_len
        for base in self.pages(table):
            if u32(d, base + 0x08) != table:
                continue
            flags = d[base + 0x1B]
            if flags & 0x40:  # index/strange page, no rows
                continue
            small = d[base + 0x18]
            large = u16(d, base + 0x22)
            n = large if (large > small and large != 0x1FFF) else small
            heap = base + 0x28
            groups = (n + 15) // 16
            for g in range(groups):
                gbase = base + L - g * 0x24
                present = u16(d, gbase - 4)
                for i in range(16):
                    if g * 16 + i >= n:
                        break
                    if present & (1 << i):
                        yield heap + u16(d, gbase - 6 - 2 * i)


def load(path):
    with open(path, "rb") as f:
        db = Pdb(f.read())
    d = db.d

    artists = {}
    for r in db.rows(T_ARTISTS):
        sub = u16(d, r)
        aid = u32(d, r + 4)
        ofs = u16(d, r + 0x0A) if sub == 0x64 else d[r + 9]
        artists[aid] = dstring(d, r + ofs)

    tracks = {}
    for r in db.rows(T_TRACKS):
        tid = u32(d, r + 0x48)
        strs = [dstring(d, r + u16(d, r + 0x5E + 2 * i)) for i in range(21)]
        tracks[tid] = {
            "id": tid,
            "artist": artists.get(u32(d, r + 0x44), ""),
            "duration": u16(d, r + 0x54),
            "strings": strs,
            "title": strs[17],
            "path": strs[20],
        }

    tree = {}
    for r in db.rows(T_TREE):
        tree[u32(d, r + 0x0C)] = {
            "id": u32(d, r + 0x0C),
            "parent": u32(d, r),
            "sort": u32(d, r + 8),
            "folder": u32(d, r + 0x10) != 0,
            "name": dstring(d, r + 0x14),
        }

    entries = {}
    for r in db.rows(T_ENTRIES):
        idx, tid, pid = struct.unpack_from("<III", d, r)
        entries.setdefault(pid, []).append((idx, tid))
    for v in entries.values():
        v.sort()
    return db, tracks, tree, entries


def children(tree, parent):
    return sorted((n for n in tree.values() if n["parent"] == parent), key=lambda n: n["sort"])


def walk(tree, parent=0, prefix=()):
    for n in children(tree, parent):
        path = prefix + (n["name"],)
        yield n, path
        if n["folder"]:
            yield from walk(tree, n["id"], path)


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or "_"


def fs_name(name):
    """A FAT/exFAT-legal name that still reads like the rekordbox one."""
    name = re.sub(r"[\\/]", "-", name)
    return re.sub(r'[:*?"<>|]', "_", name).strip().rstrip(". ") or "_"


def write_playlists(outdir, tree, tracks, entries, numbered, card_root):
    """Mirror the rekordbox tree. Returns (folders, playlists).

    Track paths are absolute: Rockbox's path_remove_dot_segments only removes
    one level of consecutive "..", so "../../../Contents" never resolves.
    """
    counts = [0, 0]

    def visit(parent, rel):
        used = set()
        kids = children(tree, parent)
        width = len(str(len(kids)))
        for pos, n in enumerate(kids, 1):
            name = fs_name(n["name"])
            if numbered:
                name = f"{pos:0{width}} {name}"
            base, i = name, 2
            while name.casefold() in used:
                name, i = f"{base} ({i})", i + 1
            used.add(name.casefold())
            stamp = ORDER_EPOCH + pos * ORDER_STEP
            if n["folder"]:
                counts[0] += 1
                os.makedirs(os.path.join(outdir, rel, name), exist_ok=True)
                visit(n["id"], os.path.join(rel, name))
                os.utime(os.path.join(outdir, rel, name), (stamp, stamp))
                continue
            counts[1] += 1
            lines = ["#EXTM3U"]
            for _, tid in entries.get(n["id"], []):
                t = tracks[tid]
                lines.append(f"#EXTINF:{t['duration']},{t['artist']} - {t['title']}")
                lines.append(card_root.rstrip("/") + t["path"])
            os.makedirs(os.path.join(outdir, rel), exist_ok=True)
            path = os.path.join(outdir, rel, name + ".m3u8")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines) + "\n")
            os.utime(path, (stamp, stamp))

    visit(0, "")
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdb")
    ap.add_argument("--tree", action="store_true")
    ap.add_argument("--dump-track", type=int)
    ap.add_argument("--m3u", metavar="OUTDIR")
    ap.add_argument("--playlists", metavar="OUTDIR",
                    help="write the nested tree for Rockbox, OUTDIR being <card>/Playlists")
    ap.add_argument("--card-root", default="/storage/sdcard1",
                    help="where the card is mounted as seen by Rockbox on the Y2")
    ap.add_argument("--numbered", action="store_true",
                    help="prefix names with their rekordbox position, since Rockbox sorts by name")
    ap.add_argument("--prefix", default="/",
                    help="replace the leading / of track paths, e.g. '' (playlist at card root) or '../'")
    a = ap.parse_args()

    db, tracks, tree, entries = load(a.pdb)
    print(f"page_len={db.page_len} tables={sorted(db.tables)} tracks={len(tracks)} "
          f"playlist_nodes={len(tree)} playlists_with_entries={len(entries)}", file=sys.stderr)

    if a.dump_track is not None:
        t = tracks.get(a.dump_track) or next(iter(tracks.values()))
        for i, s in enumerate(t["strings"]):
            print(f"  str[{i:2}] {s!r}")
        print(f"  artist={t['artist']!r} duration={t['duration']}")

    if a.tree:
        for n, path in walk(tree):
            depth = len(path) - 1
            count = "" if n["folder"] else f"  ({len(entries.get(n['id'], []))} tracks)"
            print("  " * depth + ("[+] " if n["folder"] else "- ") + n["name"] + count)

    if a.playlists:
        folders, lists = write_playlists(a.playlists, tree, tracks, entries, a.numbered, a.card_root)
        print(f"wrote {folders} folders and {lists} playlists to {a.playlists}", file=sys.stderr)

    if a.m3u:
        missing = 0
        for n, path in walk(tree):
            if n["folder"]:
                continue
            fn = " - ".join(safe(p) for p in path) + ".m3u8"
            lines = ["#EXTM3U"]
            for _, tid in entries.get(n["id"], []):
                t = tracks.get(tid)
                if not t:
                    missing += 1
                    continue
                lines.append(f"#EXTINF:{t['duration']},{t['artist']} - {t['title']}")
                lines.append(a.prefix + t["path"].lstrip("/"))
            os.makedirs(a.m3u, exist_ok=True)
            with open(os.path.join(a.m3u, fn), "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines) + "\n")
        print(f"wrote m3u8 files to {a.m3u} (missing track refs: {missing})", file=sys.stderr)


if __name__ == "__main__":
    main()

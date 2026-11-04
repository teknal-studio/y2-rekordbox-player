#!/usr/bin/env python3
"""Read-only scan: which audio files will Rockbox's AIFF codec refuse?

Mirrors the header walk in lib/rbcodec/codecs/aiff.c, which only looks at the
first 1024 bytes of the file.

usage: card_audio_scan.py <card> [--json OUT]
"""
import argparse
import collections
import json
import os
import struct


def chunks(f, size):
    f.seek(12)
    pos = 12
    while pos + 8 <= size:
        f.seek(pos)
        h = f.read(8)
        if len(h) < 8:
            break
        cid, n = h[:4], struct.unpack(">I", h[4:])[0]
        yield cid, pos, n
        pos += 8 + n + (n & 1)


def codec_walk(head):
    """The first-1024-bytes loop. Returns None if playable, else a reason."""
    pos, n, numbytes, comm = 12, len(head) - 12, 0, False
    while numbytes == 0 and n >= 8:
        cid = head[pos:pos + 4]
        size = struct.unpack(">I", head[pos + 4:pos + 8])[0]
        if cid == b"COMM":
            comm = True
        elif cid == b"SSND":
            offset = struct.unpack(">I", head[pos + 8:pos + 12])[0]
            numbytes = size - 8 - offset
            size = 8 + offset
        size += 8 + (size & 1)
        if n < size:
            return f"{cid.decode('latin-1')} chunk of {size} bytes overruns the 1024 byte header"
        pos += size
        n -= size
    if not comm:
        return "no COMM before SSND"
    if numbytes == 0:
        return "no SSND in the first 1024 bytes"
    return None


def scan_aiff(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        head = f.read(1024)
        if head[:4] != b"FORM" or head[8:11] != b"AIF":
            return {"bad_form": head[:12].hex()}
        layout = [(c.decode("latin-1"), p, n) for c, p, n in chunks(f, size)]
        info = {"form": head[8:12].decode(), "layout": layout, "reason": codec_walk(head)}
        for cid, pos, n in layout:
            if cid == "COMM":
                f.seek(pos + 8)
                c = f.read(26)
                info["channels"], info["bits"] = struct.unpack(">H", c[:2])[0], struct.unpack(">H", c[6:8])[0]
                info["compression"] = c[18:22].decode("latin-1") if info["form"] == "AIFC" else "NONE"
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("card")
    ap.add_argument("--json")
    a = ap.parse_args()
    out, ext = {}, collections.Counter()
    for d, _, fs in os.walk(os.path.join(a.card, "Contents")):
        for f in fs:
            if f.startswith("._"):
                continue
            e = f.rsplit(".", 1)[-1].lower()
            ext[e] += 1
            if e in ("aiff", "aif"):
                p = os.path.join(d, f)
                out[os.path.relpath(p, a.card)] = scan_aiff(p)
    bad = {k: v for k, v in out.items() if v.get("reason") or "bad_form" in v}
    print("extensions", dict(ext))
    print("aiff", len(out), "refused", len(bad))
    print("reasons", collections.Counter((v.get("reason") or "bad form").split(" overruns")[0][:24] for v in bad.values()).most_common(8))
    print("formats", collections.Counter((v.get("form"), v.get("bits"), v.get("compression")) for v in out.values()).most_common())
    print("first chunks", collections.Counter(tuple(c[0] for c in v.get("layout", []))[:4] for v in out.values()).most_common(8))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()

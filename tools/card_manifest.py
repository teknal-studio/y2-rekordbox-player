#!/usr/bin/env python3
"""Snapshot and diff a mounted test card, to see what each owner (rekordbox,
CDJ, Y2/Rockbox, macOS) wrote between hand-offs.

  card_manifest.py snap /Volumes/Y2TEST out.json
  card_manifest.py diff before.json after.json
"""
import hashlib, json, os, sys

# macOS litter; reported separately so it doesn't hide real changes.
MAC_NOISE = ('.Spotlight-V100', '.fseventsd', '.Trashes', '.TemporaryItems', '._', '.DS_Store')


def snap(root):
    out = {}
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root)
            h = hashlib.sha256()
            with open(p, 'rb') as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b''):
                    h.update(chunk)
            st = os.stat(p)
            out[rel] = {'sha256': h.hexdigest(), 'size': st.st_size, 'mtime': int(st.st_mtime)}
    return out


def noisy(rel):
    return any(part.startswith(MAC_NOISE) for part in rel.split(os.sep))


def diff(a, b):
    rows = []
    for rel in sorted(set(a) | set(b)):
        if rel not in a:
            rows.append(('ADDED', rel))
        elif rel not in b:
            rows.append(('REMOVED', rel))
        elif a[rel]['sha256'] != b[rel]['sha256']:
            rows.append(('CHANGED', rel))
    for kind, rel in rows:
        print('%-8s %s%s' % (kind, rel, '  (macOS noise)' if noisy(rel) else ''))
    audio = [r for k, r in rows if k != 'ADDED' and r.startswith('Contents' + os.sep)]
    if audio:
        print('\nFAIL: audio under Contents/ changed or vanished:', *audio, sep='\n  ')
        return 1
    print('\nOK: no existing file under Contents/ changed (%d differences total)' % len(rows))
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'snap':
        json.dump(snap(sys.argv[2]), open(sys.argv[3], 'w'), indent=1, sort_keys=True)
    elif len(sys.argv) == 4 and sys.argv[1] == 'diff':
        sys.exit(diff(json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))))
    else:
        sys.exit(__doc__)

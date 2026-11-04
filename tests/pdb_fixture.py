"""Build small synthetic rekordbox export.pdb files for tests.

Follows the DeviceSQL layout from Deep Symmetry's crate-digger analysis, as far
as tools/pdb_playlists.py reads it. Only test data goes in: never a real
library.
"""
import struct

PAGE = 4096
T_TRACKS, T_ARTISTS, T_TREE, T_ENTRIES = 0, 2, 7, 8
FLAG_DATA, FLAG_INDEX = 0x34, 0x64


def dstring(s):
    """A DeviceSQL string: short ASCII if it fits, else UTF-16LE."""
    if s.isascii() and len(s) < 126:
        return bytes([((len(s) + 1) << 1) | 1]) + s.encode('ascii')
    data = s.encode('utf-16-le')
    return bytes([0x90]) + struct.pack('<H', 4 + len(data)) + b'\0' + data


def artist_row(aid, name):
    head = struct.pack('<HHIBB', 0x60, 0, aid, 0x03, 10)
    return head + dstring(name)


def track_row(tid, artist_id, title, path, duration):
    strings = [''] * 21
    strings[17], strings[20] = title, path
    fixed = bytearray(0x5E + 2 * 21)
    struct.pack_into('<I', fixed, 0x44, artist_id)
    struct.pack_into('<I', fixed, 0x48, tid)
    struct.pack_into('<H', fixed, 0x54, duration)
    heap = b''
    for i, s in enumerate(strings):
        struct.pack_into('<H', fixed, 0x5E + 2 * i, len(fixed) + len(heap))
        heap += dstring(s)
    return bytes(fixed) + heap


def tree_row(node_id, parent, sort, folder, name):
    return struct.pack('<IIIII', parent, 0, sort, node_id, 1 if folder else 0) + dstring(name)


def entry_row(idx, tid, playlist_id):
    return struct.pack('<III', idx, tid, playlist_id)


def page(table, rows, next_page, flags=FLAG_DATA, deleted=()):
    """One page: header, row heap, and the row index at the page end."""
    buf = bytearray(PAGE)
    struct.pack_into('<I', buf, 0x08, table)
    struct.pack_into('<I', buf, 0x0C, next_page)
    buf[0x18] = len(rows) & 0xFF
    buf[0x1B] = flags
    struct.pack_into('<H', buf, 0x22, len(rows) if len(rows) > 255 else 0)
    heap, offsets = 0x28, []
    for row in rows:
        offsets.append(heap - 0x28)
        buf[heap:heap + len(row)] = row
        heap += (len(row) + 3) & ~3
    for g in range((len(rows) + 15) // 16):
        gbase = PAGE - g * 0x24
        present = 0
        for i in range(16):
            n = g * 16 + i
            if n >= len(rows):
                break
            struct.pack_into('<H', buf, gbase - 6 - 2 * i, offsets[n])
            if n not in deleted:
                present |= 1 << i
        struct.pack_into('<H', buf, gbase - 4, present)
    assert heap < PAGE - 0x24 * ((len(rows) + 15) // 16), 'page overflow'
    return bytes(buf)


def build(tables):
    """tables: {table type: [page spec, ...]}, each spec a dict of page() args
    without next_page. Returns the file bytes. Pages chain in order."""
    pages = [None]  # page 0 is the file header
    entries = []
    for t, specs in sorted(tables.items()):
        first = len(pages)
        for i, spec in enumerate(specs):
            idx = len(pages)
            nxt = idx + 1 if i + 1 < len(specs) else 0x3FFFFFF
            pages.append(page(t, next_page=nxt, **spec))
        entries.append((t, 0, first, len(pages) - 1))
    header = bytearray(PAGE)
    struct.pack_into('<IIII', header, 0, 0, PAGE, len(entries), len(pages))
    for i, (t, empty, first, last) in enumerate(entries):
        struct.pack_into('<IIII', header, 28 + 16 * i, t, empty, first, last)
    pages[0] = bytes(header)
    return b''.join(pages)


def sample():
    """A small library:

        Top Hits            playlist: Anthem, Zürich Nights
        System 2023/        folder
          Emotion/          folder
            HAPPY           playlist: 20 tracks, reordered
            SAD             playlist: Anthem
          Mix               playlist (empty)
        Bad: Name?          playlist named with characters FAT can't hold
        Bad/ Name?          collides with the one above once cleaned
    """
    artists = [artist_row(1, 'DJ One'), artist_row(2, 'Ünïcode Artist')]
    tracks = [track_row(1, 1, 'Anthem', '/Contents/DJ One/Anthem.aiff', 245),
              track_row(2, 2, 'Zürich Nights', '/Contents/Unicode/Zurich.flac', 301)]
    tracks += [track_row(100 + i, 1, f'Happy {i:02}', f'/Contents/Happy/{i:02}.mp3', 180 + i)
               for i in range(20)]
    tree = [
        tree_row(10, 0, 0, False, 'Top Hits'),
        tree_row(11, 0, 1, True, 'System 2023'),
        tree_row(12, 11, 0, True, 'Emotion'),
        tree_row(13, 12, 0, False, 'HAPPY'),
        tree_row(14, 12, 1, False, 'SAD'),
        tree_row(15, 11, 1, False, 'Mix'),
        tree_row(16, 0, 2, False, 'Bad: Name?'),
        tree_row(17, 0, 3, False, 'Bad/ Name?'),
        tree_row(99, 0, 9, False, 'Deleted list'),
    ]
    happy = [entry_row(20 - i, 100 + i, 13) for i in range(20)]  # stored reversed
    entries_p1 = [entry_row(1, 1, 10), entry_row(2, 2, 10)] + happy[:10]
    entries_p2 = happy[10:] + [entry_row(1, 1, 14), entry_row(1, 1, 99)]
    return build({
        T_TRACKS: [{'rows': tracks[:12]}, {'rows': tracks[12:]}],
        T_ARTISTS: [{'rows': [], 'flags': FLAG_INDEX}, {'rows': artists}],
        T_TREE: [{'rows': tree, 'deleted': {8}}],
        T_ENTRIES: [{'rows': entries_p1}, {'rows': entries_p2}],
    })

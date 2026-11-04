import sys, zlib, re
b = open(sys.argv[1], 'rb').read()
i = b.find(b'\x1f\x8b\x08')
d = zlib.decompressobj(31).decompress(b[i:])
open(sys.argv[2], 'wb').write(d)
j = d.find(b'IKCFG_ST')
if j >= 0:
    cfg = zlib.decompressobj(31).decompress(d[j+8:])
    open(sys.argv[3], 'wb').write(cfg); print('ikconfig', len(cfg))
else:
    print('no ikconfig')
m = re.search(rb'Linux version [^\n\0]+', d); print(m.group(0).decode() if m else '')

import struct, sys, gzip, io, os, zlib
b = open(sys.argv[1], 'rb').read(); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
assert b[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack('<8I', b[8:40])
print('kernel', ks, 'ramdisk', rs, 'page', ps, 'cmdline', b[64:64+512].split(b'\0')[0])
def pages(n): return (n + ps - 1) // ps * ps
k = b[ps:ps+ks]; r = b[ps+pages(ks):ps+pages(ks)+rs]
for name, blob in (('kernel', k), ('ramdisk', r)):
    if blob[:4] == b'\x88\x16\x88\x58':  # MTK 512-byte header
        print(name, 'mtk header', blob[8:40].split(b'\0')[0]); blob = blob[512:]
    open(os.path.join(out, name), 'wb').write(blob)

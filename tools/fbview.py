#!/usr/bin/env python3
"""Text view of a framebuffer PNG: colour histogram + luminance ASCII map."""
import sys, struct, zlib
from collections import Counter

def load_png(path):
    d = open(path,'rb').read(); pos = 8; idat = b''; w=h=0
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos+4])[0]; typ = d[pos+4:pos+8]
        data = d[pos+8:pos+8+ln]; pos += 12 + ln
        if typ == b'IHDR': w,h = struct.unpack('>II', data[:8])
        elif typ == b'IDAT': idat += data
    raw = zlib.decompress(idat); stride = w*3+1
    return w,h,[raw[y*stride+1:(y+1)*stride] for y in range(h)]

w,h,rows = load_png(sys.argv[1])
hist = Counter()
for y in range(h):
    r = rows[y]
    for x in range(w): hist[(r[x*3],r[x*3+1],r[x*3+2])] += 1
print('size %dx%d  distinct colours %d' % (w,h,len(hist)))
print('top colours:')
for c,n in hist.most_common(6):
    print('  #%02x%02x%02x %6d px' % (c[0],c[1],c[2],n))
sx = int(sys.argv[2]) if len(sys.argv)>2 else 4
sy = int(sys.argv[3]) if len(sys.argv)>3 else 8
print('map (%dx%d cells, 1 cell = %dx%d px):' % (w//sx, h//sy, sx, sy))
for cy in range(h//sy):
    line = ''
    for cx in range(w//sx):
        tot = 0; n = 0
        for y in range(cy*sy, cy*sy+sy):
            r = rows[y]
            for x in range(cx*sx, cx*sx+sx):
                tot += (r[x*3]*299 + r[x*3+1]*587 + r[x*3+2]*114)//1000; n += 1
        v = tot//max(n,1)
        line += ' .:-=+*#%@'[min(9, v*10//256)]
    print('%3d|%s' % (cy*sy, line))

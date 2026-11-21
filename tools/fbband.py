import sys, struct, zlib
def load_png(path):
    d=open(path,'rb').read(); pos=8; idat=b''; w=h=0
    while pos<len(d):
        ln=struct.unpack('>I',d[pos:pos+4])[0]; typ=d[pos+4:pos+8]
        data=d[pos+8:pos+8+ln]; pos+=12+ln
        if typ==b'IHDR': w,h=struct.unpack('>II',data[:8])
        elif typ==b'IDAT': idat+=data
    raw=zlib.decompress(idat); stride=w*3+1
    return w,h,[raw[y*stride+1:(y+1)*stride] for y in range(h)]
w,h,rows=load_png(sys.argv[1])
y0=int(sys.argv[2]); y1=int(sys.argv[3]); x0=int(sys.argv[4]); x1=int(sys.argv[5])
for y in range(y0,y1):
    r=rows[y]; line=''
    for x in range(x0,x1):
        v=(r[x*3]*299+r[x*3+1]*587+r[x*3+2]*114)//1000
        line += '#' if v<140 else ('+' if v<210 else '.')
    print('%3d|%s' % (y,line))

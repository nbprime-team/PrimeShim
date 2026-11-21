import sys, struct, zlib
def load(path):
    d=open(path,'rb').read(); pos=8; idat=b''; w=h=0
    while pos<len(d):
        ln=struct.unpack('>I',d[pos:pos+4])[0]; typ=d[pos+4:pos+8]
        data=d[pos+8:pos+8+ln]; pos+=12+ln
        if typ==b'IHDR': w,h=struct.unpack('>II',data[:8])
        elif typ==b'IDAT': idat+=data
    raw=zlib.decompress(idat); stride=w*3+1
    return w,h,[raw[y*stride+1:(y+1)*stride] for y in range(h)]
w,h,a=load(sys.argv[1]); _,_,b=load(sys.argv[2])
diff=0; ymin=99; ymax=-1
for y in range(h):
    row=0
    for x in range(w):
        if a[y][x*3:x*3+3]!=b[y][x*3:x*3+3]: row+=1
    diff+=row
    if row: ymin=min(ymin,y); ymax=max(ymax,y)
print('changed pixels: %d (%.1f%% of screen), rows %s..%s' % (diff, 100.0*diff/(w*h), ymin, ymax if ymax>=0 else '-'))

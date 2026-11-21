#!/usr/bin/env python3
"""Headless PrimeShim runner: inject HP key codes, dump framebuffer PNG.
usage: run_keys.py out.png "0xB1@8,0x0D@10" [total_seconds]
"""
import os, subprocess, time, zlib, struct, sys, select
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools-local')
W, H = 320, 240; SIZE = W*H*4
out = sys.argv[1]; spec = sys.argv[2] if len(sys.argv) > 2 else ''
total = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0
snaps = [float(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] else []
keys = []
for part in spec.split(','):
    if not part.strip(): continue
    code, at = part.split('@'); keys.append((float(at), int(code, 0)))
fb = os.memfd_create('fb', 0); os.ftruncate(fb, SIZE); r, w = os.pipe()
env = dict(os.environ)
env['PRIMESHIM_FRAMEBUFFER_FD'] = str(fb); env['PRIMESHIM_INPUT_FD'] = str(r)
env['LD_LIBRARY_PATH'] = T + '/root/usr/lib/x86_64-linux-gnu'
here = os.path.dirname(os.path.abspath(__file__))
p = subprocess.Popen([T+'/root/usr/bin/qemu-arm','-B','0x100000000','-L',T+'/root/usr/arm-linux-gnueabi',
                      here+'/build/pc/primeshim.elf','--firmware',here+'/firmware/20250915/armfir.elf'],
                     env=env, pass_fds=(fb,r,w), cwd=here,
                     stdout=open(here+'/run.log','wb'), stderr=subprocess.STDOUT)
t0 = time.time()
while time.time() - t0 < total:
    time.sleep(0.05)
    now = time.time() - t0
    while snaps and snaps[0] <= now:
        t_snap = snaps.pop(0)
        d = os.pread(fb, SIZE, 0)
        base = out.rsplit('.',1)[0] + '_%.1f.png' % t_snap
        open(base[:-4] + '.raw', 'wb').write(d)
        rows = []
        for y in range(H):
            rgb = bytearray()
            for x in range(W):
                v = d[(y*W+x)*4:(y*W+x)*4+4]; c = v[0]|(v[1]<<8)|(v[2]<<16)
                rgb += bytes(((c>>16)&255, (c>>8)&255, c&255))
            rows.append(b'\x00'+bytes(rgb))
        def _ch(t, dd): return struct.pack('>I', len(dd))+t+dd+struct.pack('>I', zlib.crc32(t+dd)&0xFFFFFFFF)
        open(base,'wb').write(b'\x89PNG\r\n\x1a\n'+_ch(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))+_ch(b'IDAT', zlib.compress(b''.join(rows), 6))+_ch(b'IEND', b''))
    while keys and keys[0][0] <= now:
        _, code = keys.pop(0)
        os.write(w, struct.pack('<Iiii', 1, code, 1, 0)); time.sleep(0.08)
        os.write(w, struct.pack('<Iiii', 1, code, 0, 0))
# dump nbCode NBCORING (magic+0, count+8, data+12, size 8192) from guest memory
try:
    RING = 8192
    mem = open('/proc/%d/mem' % p.pid, 'rb', 0)
    best = None
    with open('/proc/%d/maps' % p.pid) as maps:
        for line in maps:
            parts = line.split()
            if 'r' not in parts[1] or 'w' not in parts[1]:
                continue
            a, b = [int(x, 16) for x in parts[0].split('-')]
            if not (1 << 16) <= (b - a) <= (64 << 20):
                continue
            try:
                mem.seek(a); buf = mem.read(b - a)
            except Exception:
                continue
            pos = 0
            while True:
                i = buf.find(b'NBCORING', pos)
                if i < 0:
                    break
                pos = i + 1
                addr = a + i
                try:
                    mem.seek(addr + 8); cnt = int.from_bytes(mem.read(4), 'little')
                except Exception:
                    continue
                if 0 <= cnt <= RING:
                    n = min(cnt, RING); st = (cnt - n) % RING
                    try:
                        mem.seek(addr + 12 + st); raw = mem.read(n)
                    except Exception:
                        continue
                    text = raw.decode('utf-8', 'ignore')
                    printable = sum(1 for ch in text if ch.isprintable() or ch in '\n\r\t')
                    score = printable + (1000 if cnt > 0 else 0)
                    if best is None or score > best[0]:
                        best = (score, text)
    if best and best[1].strip():
        print('=== NBCORING ===')
        print(best[1][-1500:])
    else:
        print('=== NBCORING: nothing captured ===')
    mem.close()
except Exception as e:
    print('ring read failed:', e)
data = os.pread(fb, SIZE, 0)
p.terminate(); time.sleep(0.3); p.kill()
rows = []
for y in range(H):
    rgb = bytearray()
    for x in range(W):
        v = data[(y*W+x)*4:(y*W+x)*4+4]; c = v[0]|(v[1]<<8)|(v[2]<<16)
        rgb += bytes(((c>>16)&255, (c>>8)&255, c&255))
    rows.append(b'\x00'+bytes(rgb))
def chunk(t, d): return struct.pack('>I', len(d))+t+d+struct.pack('>I', zlib.crc32(t+d)&0xFFFFFFFF)
open(out, 'wb').write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(b''.join(rows), 6))+chunk(b'IEND', b''))
print('saved', out)

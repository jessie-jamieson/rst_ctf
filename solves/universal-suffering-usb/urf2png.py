#!/usr/bin/env python3
"""Decode Apple URF (UNIRAST) -> PNG. Correct page-header offsets; decode until data runs out."""
import sys, struct
from PIL import Image

def decode(data, base):
    i = data.find(b'UNIRAST')
    if i < 0: raise SystemExit("no magic")
    off = i + 8
    npages = struct.unpack('>I', data[off:off+4])[0]; off += 4
    sys.stderr.write(f"declared pages={npages}, total {len(data)} bytes\n")
    page = 0
    while off + 32 <= len(data):
        hdr = data[off:off+32]
        bpp = hdr[0]
        cs  = hdr[1]
        width  = struct.unpack('>I', hdr[12:16])[0]
        height = struct.unpack('>I', hdr[16:20])[0]
        dpi    = struct.unpack('>I', hdr[20:24])[0]
        if bpp not in (8,24,32) or not (0 < width < 20000) or not (0 < height < 20000):
            sys.stderr.write(f"  stop: implausible hdr at {off}: bpp={bpp} {width}x{height}\n")
            break
        off += 32
        bpixel = bpp//8
        sys.stderr.write(f"page {page}: {width}x{height} bpp={bpp} cs={cs} dpi={dpi}\n")
        rows = []
        y = 0
        while y < height and off < len(data):
            line_rep = data[off]; off += 1
            row = bytearray()
            target = width * bpixel
            while len(row) < target and off < len(data):
                c = data[off]; off += 1
                if c < 0x80:              # repeat next pixel c+1 times
                    px = data[off:off+bpixel]; off += bpixel
                    row += px * (c+1)
                elif c == 0x80:
                    break
                else:                     # 257-c literal pixels
                    n = 257 - c
                    row += data[off:off+n*bpixel]; off += n*bpixel
            if len(row) < target: row += b'\xff'*(target-len(row))
            row = bytes(row[:target])
            for _ in range(line_rep+1):
                rows.append(row); y += 1
                if y >= height: break
        raw = b''.join(rows)
        mode = {1:'L',3:'RGB',4:'RGBA'}[bpixel]
        need = width*height*bpixel
        raw = raw[:need].ljust(need, b'\xff')
        img = Image.frombytes(mode, (width,height), raw)
        fn = f"{base}_p{page}.png"
        img.save(fn)
        # also a downscaled view
        img.resize((width//4, height//4)).save(f"{base}_p{page}_small.png")
        sys.stderr.write(f"  wrote {fn}\n")
        page += 1
        if npages and page >= npages: break
    return page

if __name__=='__main__':
    data=open(sys.argv[1],'rb').read()
    decode(data, sys.argv[2])

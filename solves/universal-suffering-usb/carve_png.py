#!/usr/bin/env python3
"""Carve the first PNG (\\x89PNG .. IEND) out of a blob. Usage: carve_png.py write_compact.bin [out.png]"""
import sys, struct
d = open(sys.argv[1], "rb").read()
sig = b"\x89PNG\r\n\x1a\n"
start = d.find(sig)
end = d.find(b"IEND", start) + 8
png = d[start:end]
out = sys.argv[2] if len(sys.argv) > 2 else "carved.png"
open(out, "wb").write(png)
w, h = struct.unpack(">II", png[16:24])
print(f"{out}: {len(png)} bytes, {w}x{h}, header_ok={png[:8]==sig}")

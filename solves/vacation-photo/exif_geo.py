#!/usr/bin/env python3
"""Dump EXIF + GPS from an image and convert GPS to decimal degrees.
Usage: python3 -I exif_geo.py <image>
"""
import sys
from PIL import Image, ExifTags

path = sys.argv[1]
img = Image.open(path)
exif = img.getexif()

print(f"== {path}  ({img.format} {img.size}) ==")

# Top-level EXIF tags
print("\n-- EXIF --")
for tag_id, val in exif.items():
    name = ExifTags.TAGS.get(tag_id, tag_id)
    if isinstance(val, bytes) and len(val) > 64:
        val = val[:64] + b"...(%d bytes)" % len(val)
    print(f"  {name}: {val!r}")

# The Exif sub-IFD (DateTimeOriginal, lens, etc.)
try:
    sub = exif.get_ifd(ExifTags.IFD.Exif)
    if sub:
        print("\n-- Exif sub-IFD --")
        for tag_id, val in sub.items():
            name = ExifTags.TAGS.get(tag_id, tag_id)
            if isinstance(val, bytes) and len(val) > 64:
                val = val[:64] + b"...(%d bytes)" % len(val)
            print(f"  {name}: {val!r}")
except Exception as e:
    print("  (sub-IFD err:", e, ")")

# GPS IFD
def to_deg(val, ref):
    d, m, s = [float(x) for x in val]
    dec = d + m / 60.0 + s / 3600.0
    if ref in ("S", "W"):
        dec = -dec
    return dec

print("\n-- GPS --")
try:
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
except Exception:
    gps = {}
if not gps:
    print("  (no GPS IFD found)")
else:
    named = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
    for k, v in named.items():
        print(f"  {k}: {v!r}")
    try:
        lat = to_deg(named["GPSLatitude"], named.get("GPSLatitudeRef", "N"))
        lon = to_deg(named["GPSLongitude"], named.get("GPSLongitudeRef", "E"))
        print(f"\n  DECIMAL: {lat:.6f}, {lon:.6f}")
        print(f"  Google Maps: https://maps.google.com/?q={lat:.6f},{lon:.6f}")
        if "GPSAltitude" in named:
            print(f"  Altitude: {float(named['GPSAltitude']):.1f} m")
    except Exception as e:
        print("  (could not convert to decimal:", e, ")")

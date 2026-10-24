#!/usr/bin/env python3
"""Reassemble printer bulk-OUT pipes (7.10, 7.3) from a USBLL TSV, keeping only ACK'd DATA.
Usage: reassemble_printer.py printer.tsv   ->   clean_7_10.bin, clean_7_3.bin"""
import sys

def clean_stream(rows, ep):
    """Concatenate payloads of host->ep DATA packets whose next frame is ACK (0xd2)."""
    out = bytearray()
    pending = None
    for i, (fn, s, d, pid, data) in enumerate(rows):
        if pending is not None:
            if pid == "0xd2":           # ACK -> the buffered DATA was accepted
                out += pending
            pending = None              # NAK / anything else -> drop (retransmit follows)
        if d == ep and pid in ("0xc3", "0x4b") and data:
            pending = bytes.fromhex(data)
    return bytes(out)

def main(path):
    rows = [l.rstrip("\n").split("\t") for l in open(path)]
    for r in rows:
        while len(r) < 5: r.append("")
    for ep in ("7.10", "7.3"):
        blob = clean_stream(rows, ep)
        name = "clean_" + ep.replace(".", "_") + ".bin"
        open(name, "wb").write(blob)
        print(f"{name}: {len(blob)} bytes, UNIRAST x{blob.count(b'UNIRAST')}")

if __name__ == "__main__":
    main(sys.argv[1])

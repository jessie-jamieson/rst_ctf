#!/usr/bin/env python3
"""Minimal manual port check, post-advisory (102/80/161 disabled by author).
Tests only researched, S7-1200-plausible OT ports. One TCP connect each.
Writes its own output file (no shell pipe). Usage: portcheck2.py [host]
"""
import socket, sys, os, datetime

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.100.56"
# 502  Modbus TCP   (native S7-1200 server) -- recheck
# 4840 OPC-UA       (native S7-1200 FW>=4)  -- top candidate
# 102  S7comm       (should now be CLOSED per author)
# 44818 EtherNet/IP , 20000 DNP3  (not native Siemens; sanity only)
PORTS = [502, 4840, 102, 44818, 20000]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portcheck2_out.txt")
lines = [f"# portcheck2 {datetime.datetime.now()}  host={HOST}"]
for p in PORTS:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(3)
    try:
        s.connect((HOST, p)); line = f"{HOST}:{p}  OPEN"
    except Exception as e:
        line = f"{HOST}:{p}  closed/filtered ({type(e).__name__})"
    finally:
        s.close()
    print(line); lines.append(line)
with open(OUT, "w") as f:
    f.write("\n".join(lines) + "\n")
print("[written]", OUT)

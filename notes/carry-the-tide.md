# Carry The Tide — Writeup

- **Category:** Reverse Engineering
- **Points:** 500
- **Flag:** `rstcon{running_sum_unwinds_in_reverse}`
- **Description:** *A sluice controller will only align if you give it the right control key.*

## TL;DR

The provided `carry` is a **Renesas SH (SuperH)** ELF — a nod to the "sluice
controller" flavor and to the word *carry*. It reads a 38-char "control key" and
checks it with a **chained running-sum (carry) cipher**: each expected byte is
`(previous_char + current_char) mod 256`, seeded with `0x5A`. The transform is
fully invertible, so we unwind it in reverse to regenerate the one accepted key —
which is the flag.

## Recon

```
$ file carry
carry: ELF 32-bit LSB executable, Renesas SH, version 1 (SYSV),
       dynamically linked, interpreter /lib/ld-linux.so.2, ... not stripped
```

SuperH, little-endian, **not stripped**. Strings give us the whole shape of the
program:

```
Carry the tide. Enter control key:
Sluice aligned.
Out of phase.
```

and the symbols `main`, `check`, `target`, `target_len`, from `carry.c`.

No SH disassembler (`objdump`/`llvm-objdump`) was installed and only
`qemu-system-sh4` (full-system, no user-mode) was available, so running it
natively wasn't convenient. Instead we disassembled statically with **Capstone's
SH4 backend** (`CS_ARCH_SH` / `CS_MODE_SH4`), after parsing the ELF symbol and
section tables by hand to locate `check`, `main`, and the `target` bytes.

## The check

`target_len` is `0x26` = **38**, and `check()` first rejects any input whose
length isn't 38. The loop (annotated from the SH disassembly) is:

```c
unsigned char acc = 0x5A;          // 'Z' seed, in a stack byte
for (int i = 0; i < 38; i++) {
    unsigned char t = (acc + s[i]) & 0xff;
    if (t != target[i]) return 0;  // "Out of phase."
    acc = s[i];                    // previous char feeds the next step
}
return 1;                          // "Sluice aligned."
```

Key detail: `acc` is **not** a constant XOR/add key — after each position it
becomes the current input character. So position `i` depends on position `i-1`:
a running chain, i.e. the "carry" that drifts along like a tide.

The 38 expected bytes (`target`, pulled straight from `.rodata`):

```
cc e5 e7 d7 d2 dd e9 ed e7 e3 dc d7 d7 d5 c6 d2 e8 e2 cc d4 e3
e5 e0 d7 d2 d7 d2 c8 d7 cd d1 d7 db db d7 e5 d8 e2
```

## The vulnerability

The chain is **invertible**. Given the seed and all target bytes we can solve for
the input directly — there is exactly one 38-byte string that aligns the sluice:

```
s[0] = (target[0] - 0x5A)  mod 256
s[i] = (target[i] - s[i-1]) mod 256      for i >= 1
```

Each subtraction mod 256 undoes one `(acc + s[i])` step and simultaneously hands
us the `acc` (= `s[i]`) needed for the next one.

## Exploit

```python
TARGET = bytes.fromhex(
    "cce5e7d7d2dde9ede7e3dcd7d7d5c6d2e8e2ccd4e3e5e0d7d2d7d2c8d7cdd1d7dbdbd7e5d8e2"
)
acc, key = 0x5A, bytearray()
for t in TARGET:
    c = (t - acc) & 0xFF
    key.append(c)
    acc = c
print(key.decode())
```

Full script with a forward-direction round-trip assertion lives in
[`solves/carry-the-tide/solve.py`](solves/carry-the-tide/solve.py).

```
$ python3 solves/carry-the-tide/solve.py
rstcon{running_sum_unwinds_in_reverse}
```

The recovered key is 38 printable bytes and, run **forward** through the cipher,
reproduces `target` byte-for-byte — so feeding it to the binary prints
`Sluice aligned.`

## Flag

```
rstcon{running_sum_unwinds_in_reverse}
```

## Takeaway

A keyed check is only as strong as its invertibility. This one is a linear,
position-chained sum over a known seed and known expected output — every byte can
be solved in closed form with a single subtraction, so the "secret" control key
falls out instantly. A real integrity/auth check should compare against a
**one-way** function of the input (a keyed hash / MAC), not a reversible running
sum whose expected result is sitting in `.rodata`.

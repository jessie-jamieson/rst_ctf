# ARC4 Reactor — Writeup

- **Category:** Crypto
- **Points:** 10
- **Flag:** `rstcon{n3utronz_Go_BRRRR}`
- **Description:** *AM IRONMAN AND ALL HIS SECRETS*

## TL;DR

RC4 (a.k.a. **ARC4**) keystream was **reused** to encrypt two files. One of them
was given to us in both plaintext and ciphertext form, so we can recover the
keystream with a single XOR and use it to decrypt the secret archive. Classic
**two-time pad / keystream-reuse** break.

## Files

Unzipping `reactor.zip`:

| File | Size | Notes |
|------|------|-------|
| `arc_reactor.png` | 2,313,994 B | **Known plaintext** (a valid PNG, 1254×1254) |
| `arc_reactor.png.enc` | 2,313,994 B | Same size — ciphertext of the PNG |
| `documents.zip.enc` | 1,343,907 B | The secret we want |

The giveaway: we're handed a file **and** its encrypted twin, *and* the twin is
byte-for-byte the same length as the plaintext. That's a stream cipher with no
IV/nonce change between files.

## The vulnerability

RC4 is a stream cipher. It encrypts by XORing data with a key-derived keystream:

```
ciphertext = plaintext XOR keystream
```

The keystream depends only on the key (and the starting position). If the **same
key** is used to encrypt two files starting from the same position, the keystream
is identical for both. That lets us cancel it out:

```
keystream = plaintext  XOR ciphertext            (recovered from the PNG pair)
secret    = secret.enc XOR keystream             (decrypt the zip)
```

Because the recovered keystream (2.3 MB) is **longer** than `documents.zip.enc`
(1.3 MB), it covers the entire archive.

## Exploit

```python
#!/usr/bin/env python3
pt   = open("arc_reactor.png", "rb").read()      # known plaintext
ct   = open("arc_reactor.png.enc", "rb").read()  # its ciphertext
zenc = open("documents.zip.enc", "rb").read()    # secret ciphertext

# 1. Recover keystream from the known plaintext/ciphertext pair
ks = bytes(a ^ b for a, b in zip(pt, ct))

# 2. Decrypt the secret with the same keystream
out = bytes(a ^ b for a, b in zip(zenc, ks))
open("documents.zip", "wb").write(out)
```

Sanity check — the decrypted output starts with `50 4B 03 04`, the **PK ZIP**
magic bytes:

```
$ xxd documents.zip | head -1
00000000: 504b 0304 1400 0000 ...   PK......
```

## Recovering the flag

The archive contained a single PDF:

```
$ unzip -l documents.zip
  1371919  split funny atoms haha.pdf
```

A 7-page slide deck, *"Nuclear Power and the Energy Grid."* The flag lives on the
final slide. No PDF renderer (poppler/ghostscript/mutool) was installed, and the
deck uses a **custom-subset font** — pulling raw bytes out of the content stream
gives shifted/ligature-mangled gibberish.

The clean fix is to decode the text through the PDF's embedded **ToUnicode CMap**,
which maps each glyph code to its real Unicode character:

```python
import re, zlib
d = open("split funny atoms haha.pdf", "rb").read()

# Build glyph-code -> unicode map from the ToUnicode streams
code2uni = {}
for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", d, re.S):
    try: dec = zlib.decompress(m.group(1))
    except Exception: continue
    for bf in re.finditer(rb"beginbfchar(.*?)endbfchar", dec, re.S):
        for c, u in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", bf.group(1)):
            code2uni[int(c, 16)] = bytes.fromhex(u.decode()).decode("utf-16-be")

# Decode the text strings in the content streams
for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", d, re.S):
    try: dec = zlib.decompress(m.group(1))
    except Exception: continue
    for s in re.findall(rb"\((?:[^()\\]|\\.)*\)", dec):
        out = "".join(code2uni.get(b, chr(b)) for b in s[1:-1])
        if "con{" in out:
            print(out)
```

Output:

```
rstcon{n3utronz_Go_BRRRR}
```

## Flag

```
rstcon{n3utronz_Go_BRRRR}
```

## Takeaway

**Never reuse an RC4 keystream.** RC4 has no built-in nonce, so encrypting two
messages under the same key is a two-time pad. A single known-plaintext pair (or
even enough statistical redundancy across the two streams) collapses the whole
scheme — here it took one XOR. If you must use a stream cipher, derive a fresh,
unique nonce per message (and prefer an authenticated AEAD like AES-GCM or
ChaCha20-Poly1305).

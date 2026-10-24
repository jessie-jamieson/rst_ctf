# Vendor FC 0x41 — Writeup

- **Category:** ICS / Modbus (reversing a vendor extension)
- **Points:** 10
- **Flag:** `rstcon{user_defined_fc_reversed}`
- **Description:** *This field device speaks a vendor extension on top of
  Modbus/TCP, function code `0x41`. The integrator who documented it is long gone
  and the manual went with them.*
- **Target:** `18.215.143.250:1502` (Mirror 2: `18.145.136.91:1502`)
- **Provided:** `server.py`

## TL;DR

We're handed the server source, so the "undocumented" vendor function is fully
specified. Custom function code `0x41` returns the flag iff the 16-bit `guess`
we send equals `transform(seed)` for the `seed` we send — and `transform` is a
plain invertible arithmetic function printed right there. It's a **keygen**, not
a brute force: pick any seed, compute the matching guess, send one request.

## The protocol (from `server.py`)

Modbus/TCP framing (MBAP header + PDU) with two function codes implemented:

**`0x03` (Read Holding Registers)** — a red-herring breadcrumb. Registers 0–3
just spell the function code to use:

```python
BREADCRUMB = [ord('0'), ord('x'), ord('4'), ord('1')]   # "0x41"
```

**`0x41` (the vendor extension)** — the real path:

```python
if fc == CUSTOM_FC:                       # 0x41
    seed, guess = struct.unpack(">HH", pdu[1:5])
    if guess == transform(seed):
        return struct.pack(">BB", CUSTOM_FC, 0x00) + FLAG   # status 0x00 + flag
    return struct.pack(">BB", CUSTOM_FC, 0x01)              # status 0x01, wrong
```

with

```python
def transform(seed: int) -> int:
    return (((seed ^ 0x1F3D) * 0x0101) + 0x2027) & 0xFFFF
```

## The "challenge"

There's no secret to recover — `transform` is given. We just need to send a
`(seed, guess)` pair where `guess == transform(seed)`. (Even without the source
it's weak: `transform` is a bijection on 16 bits, and worst case the whole input
space is only 65536 seeds — trivially brute-forceable. With the source it's one
line.)

PDU layout for FC `0x41`: `BYTE fc=0x41 | WORD seed | WORD guess` (big-endian),
wrapped in a standard MBAP header whose `length = len(pdu) + 1`.

## Exploit

```python
seed  = 0x1234                     # any value
guess = (((seed ^ 0x1F3D) * 0x0101) + 0x2027) & 0xFFFF
pdu   = struct.pack(">BHH", 0x41, seed, guess)
req   = struct.pack(">HHHB", 1, 0, len(pdu) + 1, 0x01) + pdu   # MBAP + PDU
```

Running it (see [`solves/vendor-fc41/solve.py`](../solves/vendor-fc41/solve.py)):

```
[*] seed=0x1234  guess=transform(seed)=0x3630
[*] request:  000100000006014112343630
[*] response: 000100000023014100 72737463 6f6e7b75 7365725f ...
[+] FLAG: rstcon{user_defined_fc_reversed}
```

The response PDU is `0x41 0x00` (status OK) followed by the flag bytes.

## Flag

```
rstcon{user_defined_fc_reversed}
```

## Takeaway

A "custom/undocumented" protocol is not a security control — **security through
obscurity fails the moment the source, firmware, or enough traffic is
available.** The check here is a deterministic, invertible 16-bit transform with
no secret key and no rate limiting, so authenticating with it is equivalent to
having no authentication at all. Real device auth needs a secret the client
proves knowledge of (a keyed MAC / challenge-response with a server-held key),
not a reproducible math function over client-supplied input.

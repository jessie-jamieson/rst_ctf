# Modbus Mastermind — Writeup

- **Category:** ICS / PLC (Modbus/TCP)
- **Points:** 30
- **Flag:** `rstcon{pymodbus_or_it_didnt_happen}`
- **Description:** *This PLC is online and chatty, but it is holding out on you.
  Part of what you want reads straight off the holding registers, but seems like
  you need to arm the device a certain way.*
- **Targets:** Mirror 1 `18.215.143.250:1500` · Mirror 2 `18.145.136.91:1500`

## TL;DR

A raw **Modbus/TCP** PLC exposes its holding registers. The flag is stored one
ASCII character per register, in the **low byte** of each 16-bit register. It
comes in two halves — the first reads straight off the registers, the second
appears after you "arm" the device. Read the whole register map, take the low
byte of each register, strip the `0x00` padding, and the flag falls out:

```
rstcon{pymodbus_or_it_didnt_happen}
```

The twist for us was operational, not technical: for most of the event the
public instance was a **shared, world-writable register store** that competitors
had overwritten into noise. The actual break only worked against a **clean
instance** — which is exactly what the challenge intended, and what an organizer
restart finally gave us.

## Recon — what is this thing?

Port `1500` speaks **Modbus/TCP**. There's no banner; you just send a well-formed
request and see what comes back. A Modbus/TCP frame is a 7-byte **MBAP header**
(Transaction ID, Protocol ID, Length, Unit ID) followed by the **PDU** (function
code + data). No library needed — it's a handful of `struct.pack` calls over a
TCP socket (`solves/modbus-mastermind/modbus.py`).

Probing every function code mapped the device's surface:

| FC | Function | Result |
|----|----------|--------|
| `0x03` | Read Holding Registers | **supported** (addresses 0–65535 all readable) |
| `0x06` | Write Single Register | **supported** |
| `0x10` | Write Multiple Registers | **supported** |
| `0x01/0x02/0x04` | Read Coils / Discrete / Input | `ILLEGAL_FUNCTION` (exc 0x01) |
| everything else | diagnostics / file / device-id | `ILLEGAL_FUNCTION` |

So the entire game lives in the **holding registers**, read with FC03. The
prompt confirms it: *"part of what you want reads straight off the holding
registers."*

## The detour — a griefed shared board

The first (long) pass at this looked like a dead end, and it's worth recording
why, because it's a realistic ICS-security lesson.

Reading the register map didn't show a flag — it showed **graffiti**: `ARMED`,
`MASTERMIND`, `GOOD`/`0x600D`, and leet junk (`0xCAFE`, `0xDEAD`, `0xBEEF`, …)
scattered around, with values flipping mid-scan. A few empirical tests explained
it:

- **Writes persist globally across connections** (I wrote a unique nonce from one
  socket and read it back from another) — a single shared backend per mirror.
- **There's no logic behind the registers.** Overwriting `reg1337` (`0x600D`)
  with `0xBEEF` made it *stay* `0xBEEF`; nothing recomputed it. FC06/FC16 writes
  just store. It's a bare key/value store, not a simulated PLC.
- Because read **and write** are open to everyone and nothing resets, ~48 prior
  solvers' writes had accumulated on top of each other and buried the flag.

One genuinely useful positive finding came out of this: **author-placed data is
identical on both mirrors** (same seed/init), while graffiti differs per mirror.
Intersecting the two maps isolated real landmarks — `reg1000 = "MASTERMIND"`,
`reg1337 = 0x600D` — proving the mechanic was register-based and that the flag
*had* been staged in registers, just clobbered since. Conclusion at the time:
**not solvable until a clean instance exists.** (The full lab log of this phase —
function-code probing, the cross-mirror intersection, the reset watch — is in
`solves/modbus-mastermind/process-notes.md`.)

That turned out to be correct. An organizer restart wiped the board, and the
staged flag was immediately readable on **both** mirrors.

## The break — low-byte register encoding

On the clean instance, dumping all 65,536 holding registers and scanning the
bytes for `rstcon{` under every obvious encoding (big-endian, little-endian,
low-byte stream, high-byte stream) hit on the **low-byte stream**: the flag is
stored **one ASCII char per register, in the low byte** (the high byte is zero).

It arrives in two runs, with zero padding between them:

| Registers | Low bytes spell | Role |
|-----------|-----------------|------|
| `reg100…` | `rstcon{pymodbus_or` | *"reads straight off the holding registers"* |
| `reg200…` | `_it_didnt_happen}`  | *"you need to arm the device"* |

Both runs were present on the reset instance (identical on m1 and m2), so
reassembling the low-byte stream and dropping the `0x00` gaps gives the complete,
contiguous flag.

## Exploit

Using the dependency-free client in `solves/modbus-mastermind/modbus.py`:

```python
#!/usr/bin/env python3
from modbus import ModbusTCP, HOSTS   # raw Modbus/TCP over a plain socket

host, port = HOSTS["m1"]              # 18.215.143.250:1500
with ModbusTCP(host, port, timeout=10) as m:
    regs = []
    base = 0
    while base < 65536:               # FC03 caps at 125 regs/request
        cnt = min(125, 65536 - base)
        regs.extend(m.read_holding(base, cnt))
        base += cnt

# Flag is the LOW byte of each register; strip the 0x00 padding
lo   = bytes(r & 0xFF for r in regs)
frag = lo[lo.find(b"rstcon{"):]
frag = frag[:frag.find(b"}") + 1]
print(bytes(b for b in frag if b != 0).decode())
```

Output (identical on both mirrors):

```
rstcon{pymodbus_or_it_didnt_happen}
```

`solves/modbus-mastermind/solve.py` wraps this up — it reads the full map, prints
the landmarks, tries all four byte encodings, and arms the device (writes to
`reg0`) if the second half isn't present yet. Run it with `python3 solve.py m1`.

## Flag

```
rstcon{pymodbus_or_it_didnt_happen}
```

## Takeaways

- **Modbus has no auth and no encryption.** An internet-reachable PLC on `:1500`
  will answer FC03 reads to anyone, and here FC06/FC16 writes too. That's the
  whole premise — and it mirrors real exposed ICS gear.
- **Watch the byte lanes.** Modbus registers are 16-bit; packing ASCII into only
  the low byte of each register is a common ICS idiom. If one encoding looks like
  junk, try BE/LE/low-byte/high-byte before concluding there's nothing there.
- **A shared, writable CTF service is fragile.** With open writes and no reset or
  per-team isolation, competitors overwrite each other (and the staged flag).
  The clean fix the organizers want here is read-only flag registers or a
  per-connection instance — exactly the same control you'd want on a real PLC.
- The flag is a wink at that: **`pymodbus_or_it_didnt_happen`** — prove it with a
  real Modbus client, not by hand.

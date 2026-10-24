# Modbus Mastermind (30 pts)

## Prompt
> This PLC is online and chatty, but it is holding out on you. Part of what you
> want reads straight off the holding registers, but seems like you need to arm
> the device a certain way.

- Mirror 1: `18.215.143.250:1500`
- Mirror 2: `18.145.136.91:1500`
- Flag format: `rstcon{...}`

## Service characterization (Modbus/TCP, port 1500)
Raw Modbus/TCP. Probed every function code:

| FC | Function | Result |
|----|----------|--------|
| 0x03 | Read Holding Registers | **supported** (addr 0–65535 all readable) |
| 0x06 | Write Single Register | **supported** |
| 0x10 | Write Multiple Registers | **supported** |
| 0x01/0x02/0x04 | Read Coils / Discrete / Input | ILLEGAL_FUNCTION (exc 01) |
| 0x05 | Write Single Coil | ILLEGAL_FUNCTION |
| 0x07,0x08,0x0B,0x0C,0x11,0x14,0x16,0x17,0x18,0x2B | diagnostics / file / device-id / etc. | all ILLEGAL_FUNCTION |

Unit/slave ID is ignored (0–255 all identical).

## Key finding: it is a bare, shared, writable register store with NO logic
Verified empirically:
- Writes **persist globally** across connections (unique nonce test) — single
  shared backend per mirror (25/25 connections identical), no load balancing.
- **No on-read logic**: overwrote reg1337 (`0x600D`="GOOD") with `0xBEEF`; it
  stayed `0xBEEF`, never recomputed. No register's read value depends on reg0.
- **No on-write logic**: FC06/FC16 writes just store; no feedback register
  reacts to a "guess" (tested Mastermind-style). No flag ever gets injected.
- **No read-only/protected region** (write+readback across sampled 0–65535).
- **No TTL** (writes don't expire) and **no server-driven mutation** on reads.
- Default fill is a uniform `7, 1965, 42` 3-cycle by address, everywhere.

## State is competitor graffiti, not the challenge
Because reads/writes are unrestricted and shared, all ~48 prior solvers' writes
accumulate. Observed live: `ARMED` (`41 52 4D 45 44`) scattered at reg0-4 and
reg10-14, `MASTERMIND`, `GOOD`/`0x600D`@1337, `0xCAFE`/`0xDEAD`/`0x9876`/`0xBAD`
littered around. reg0 flips under me (concurrent players). **No `rstcon{` /
`flag{` anywhere in 0–65535 on either mirror, in any byte encoding.**

## Author landmarks survive (cross-mirror agreement)
Author-placed data is identical on both mirrors (same init); graffiti is
independent per mirror. Taking the intersection (same address, same non-noise
value on BOTH m1 and m2) isolates author content:
- **reg1000-1004 = `MASTERMIND`** (`0x4D41 53 54 45 52 4D 49 4E 44`) — the device label.
- **reg1337 = `0x600D` ("GOOD")** — leet status landmark.

So the author *did* stage data in holding registers (register-based mechanic
confirmed). The flag bytes would sit adjacent to these landmarks — but that
region is now overwritten. On m2, reg1005-1019 (right after `MASTERMIND`) is
all zeros; on m1 the reg1337+ region is competitor graffiti (`RSTCD`, `2026`,
`MASTERMIND` fragments). No intact `rstcon{...}` survives on either mirror.

Latest moment-in-time retest: additional angles all negative —
- All 256 unit/slave IDs return identical data (no hidden bank).
- Spelling `ARMED` in reg0-4 unlocks nothing across reg0-16384 (no on-read logic).
- MBAP Protocol-ID / Transaction-ID are echoed and ignored (standard Modbus).
- No other active writer on m2 during a 12 s window (board is shared but quiet).

## Conclusion / blocker
The live shared instance is vandalized past the point of reading the flag. The
intended path ("read part of the flag off holding registers; arm the device to
reveal the rest") only works against a **clean instance** — the flag bytes were
author-placed in holding registers and have been overwritten. No automatic
reset observed in a 5-min monitor; m2 only accumulated more graffiti (34 → 4031
anomalies), arguing against frequent auto-resets.

**Need:** a fresh/reset instance (per-team spin-up or server reset), then
`read holding registers → arm (write the documented register) → read`.

## Tooling (in `solves/modbus-mastermind/`)
- `modbus.py` — dependency-free raw Modbus/TCP client (read/write holding).
- `recon.py`, `probe.py` — register map + function-code probing.
- `arm_brute.py` — brute candidate (arm-register, arm-value) pairs.
- `monitor.py`, `catch_reset.py` — poll mirrors for a reset/clean flag state.

## SOLVED (after organizer restart, 2026-10-24)
Once the organizers reset the instance, the staged flag was readable on BOTH
mirrors. The flag is stored one ASCII char per register in the **low byte** of
each holding register, in two pieces:
- **reg100** low bytes = `rstcon{pymodbus_or` (reads straight off the registers)
- **reg200** low bytes = `_it_didnt_happen}` (the "arm the device" half)

Join the low-byte stream (drop the `0x00` padding between the two runs):

```
rstcon{pymodbus_or_it_didnt_happen}
```

`solve.py` auto-extracts it (LO encoding). The earlier blocker was correct: the
mechanic was register-based all along; it just needed a clean board.

## Flag
`rstcon{pymodbus_or_it_didnt_happen}`

# Carbon Noneoxide — Writeup

- **Category:** Firmware / Pwn (embedded, FreeRTOS on Cortex-M)
- **Points:** 10
- **Flag:** `rstcon{y0ur_Q_my_Q}`
- **Description:** *"There's a weird port open on my smart carbon monoxide detector.
  Here's the firmware from their website."* + a `ChudMaxxing_AirSensor` product-sheet PDF.
- **Target:** `nc 18.215.143.250 1337` (Mirror 2: `nc 18.145.136.91 1337`)
- **Files:** `challenges/carbon-noneoxide/extracted/firmware.bin.chal` (9028 bytes, raw
  Cortex-M image), `ChudMaxxing_AirSensor_v1.23.0_ProductSheet.pdf`.

## TL;DR

The "weird port" is a FreeRTOS debug UART shell emulated in QEMU (`lm3s6965evb`).
Log in with the password `charlotte` (plainly visible in the firmware strings). The
shell's `i` (inject) command appends a reading to a **128-entry log array** at
`0x20006140` using a **1-byte counter with no bounds check**, while the sensor task
(which *does* clamp the counter) can be shut off with the `s` command. Suspend the
sensor, then inject 128 readings: entry #128 lands exactly on the **FreeRTOS queue
handle** at `0x20006340`. Point that handle at a **fake `Queue_t`** we built in the
log array, with `pcReadFrom` aimed at the flag in flash (`0x22d8`) and
`uxItemSize = 4`. The Monitor task then `xQueueReceive`s straight out of flash and
prints the flag four bytes at a time as "CO readings". Reassemble the little-endian
`uint32`s → the flag.

> The PDF is a **decoy**: it's stuffed with white-on-white prompt-injection text and a
> fake `FLAG{pr0mpt_1nj3ct10n_...}`. Ignore it entirely; the real flag only lives in the
> firmware's RAM/flash on the server.

## Recon

`file` calls the blob `data`, but the first vector-table word is `0x20010000` (initial
SP) followed by Thumb reset/exception vectors — a textbook raw **ARM Cortex-M** image.
Strings nail the platform and hand us the password:

```
--- Debug Shell ---
Device : LM3S6965 (Cortex-M3)
[Admin] Task started
charlotte                      <-- admin password
[Sensor] Reading = / [Monitor] OK ( / [ALERT] Threshold exceeded!
rstcon{???????????}            <-- flag placeholder (11 chars), filled in on the server
Starting FreeRTOS scheduler...
```

`LM3S6965` is the canonical QEMU `-M lm3s6965evb` target; the service is QEMU piping
the board UART over TCP. Connecting shows three FreeRTOS tasks running: **Sensor**
(emits random readings), **Monitor** (compares each reading to threshold 75), and
**Admin** (the shell). Disassembly was done with Capstone (Thumb/M-class); the ELF
toolchain wasn't needed.

## The shell

The Admin task `readline`s a line and `strcmp`s it against `charlotte`, looping until it
matches, then drops into a command dispatcher (`tbb` jump table on `firstbyte - 0x68`):

| cmd | action |
|-----|--------|
| `h` | help (prints nothing useful) |
| `i` | inject a CO reading (prompts for a number) |
| `s` | **suspend** the sensor task |
| `r` | resume the sensor task |
| `x` | log out (back to password) |

Nothing here prints the flag — `0x22d8` is **never referenced by any code path**. So
this is a memory-corruption problem.

## The vulnerability

Two tasks write readings into the same global ring buffer, but only one of them is safe.

**Sensor task** (safe — clamps the index):

```c
int8_t *ctr = (int8_t*)0x2000613c;           // 1-byte counter
if (*ctr < 0) *ctr = 0;                       // reset when it passes 128
log[*ctr] = reading;                          // log @ 0x20006140, 128 entries
(*ctr)++;
```

**Inject command `i`** (vulnerable — no clamp, unsigned index):

```c
uint8_t idx = *(uint8_t*)0x2000613c;          // unsigned, NO bounds check
*(uint32_t*)(0x20006140 + idx*4) = value;     // OOB once idx >= 128
*(uint8_t*)0x2000613c = idx + 1;
```

The log array is exactly 128 words (`0x20006140`–`0x2000633c`). The very next words are:

| addr | idx | what |
|------|-----|------|
| `0x20006340` | 128 | **sensor queue handle** (used by Monitor's `xQueueReceive`) |
| `0x20006344` | 129 | sensor task handle |
| `0x20006348` | 130+ | start of the FreeRTOS heap (TCBs / stacks) |

So inject can walk the counter past the array and overwrite the **queue handle**. The
only catch is the Sensor task keeps resetting the counter — so **`s` (suspend) it first**.
With the sensor suspended, the counter is frozen and deterministic: it sits at **C = 1**
(the sensor emits exactly one reading before our first command — verified stable across
many fresh connections). Inject #k then writes array index `k`, and inject **#128 writes
index 128 = the queue handle**.

## Turning it into a flash read (fake queue)

Background: in FreeRTOS a queue is just a `Queue_t` struct in RAM, and a "queue handle"
is a pointer to it. `xQueueReceive(handle, dst, ...)` normally `memcpy`s one item's worth
of bytes **from inside that struct's ring buffer** (`pcReadFrom`) into `dst`. So if we can
make the handle point at a `Queue_t` *we* control, we choose where the copy reads from —
including flash. We only need to forge the handful of fields the receive path actually
touches; everything else can stay zero.

Reversing `xQueueReceive` / `prvCopyDataFromQueue` gives the `Queue_t` layout for this
build:

| off | field | used in the hot path? |
|-----|-------|-----------------------|
| 0x00 | `pcHead` | only on wrap |
| 0x08 | `pcTail` | wrap boundary |
| 0x0C | `pcReadFrom` | **copy source** |
| 0x10 | `xTasksWaitingToSend.uxNumberOfItems` | must be 0 → clean return |
| 0x38 | `uxMessagesWaiting` | must be > 0 → immediate (non-blocking) receive |
| 0x40 | `uxItemSize` | memcpy length |

The receive hot path is:

```c
pcReadFrom += uxItemSize;
if (pcReadFrom >= pcTail) pcReadFrom = pcHead;
memcpy(buf, pcReadFrom, uxItemSize);          // <-- copies from an attacker pointer
uxMessagesWaiting--;
if (xTasksWaitingToSend.uxNumberOfItems) { /* unblock senders */ }  // skipped if 0
```

If `uxMessagesWaiting > 0` and the send-wait count is `0`, `xQueueReceive` returns a copy
of `*pcReadFrom` **without ever touching the list structures** — so we only need to fake a
handful of fields. The Monitor then prints the received word as an (unsigned) decimal
"reading". Point `pcReadFrom` at `flag - 4`, set `uxItemSize = 4`, and each receive leaks
the next 4 bytes of flash. The flag is 20 bytes → ~5 reads.

**Fake `Queue_t`** (built in the log array; base = index 1 = `0x20006144`, since C = 1):

```
idx  1 (pcHead)              = 0x000022d4
idx  3 (pcTail)              = 0x00030000   # large -> no wrap
idx  4 (pcReadFrom)          = 0x000022d4   # +4 on first read -> 0x22d8 (flag)
idx  5 (WaitingToSend count) = 0            # clean, listless return
idx 15 (uxMessagesWaiting)   = 16
idx 17 (uxItemSize)          = 4
idx 128 (queue handle)       = 0x20006144   # <-- swap Monitor's queue to our fake
```

The Monitor re-reads the handle from `0x20006340` on every loop iteration, so the swap
takes effect on its next receive. Note the inject's array write runs even on a
"Queue full" result, so pacing against the real queue doesn't matter — every inject
advances the counter by exactly one.

## Exploit

`solves/carbon-noneoxide/solve.py` — login, suspend, 128 paced injects, then read the
Monitor's "readings" and reassemble them little-endian:

```
$ python3 solve.py 18.215.143.250 1337
FLAG = rstcon{y0ur_Q_my_Q}
```

The leaked words decode straight to flash contents:

```
0x63747372 0x6e6f6373 ...  ->  'r','s','t','c','o','n', ...  ->  rstcon{y0ur_Q_my_Q}
```

## Flag

```
rstcon{y0ur_Q_my_Q}
```

(The pun — "your queue, my queue" — is the whole exploit: we hand the Monitor *our*
queue in place of the real one.)

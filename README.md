# RSTCON 2026 CTF — solutions & writeups

A personal solve log for the **[RSTCON](https://rstcon.org/) 2026** Capture-the-Flag
(Oct 23–25, 2026). One folder per challenge, a readable writeup for each, and the
scripts/exploits used to get the flag.

## About the conference & CTF

**RSTCON** is a security conference focused on research, exploitation, and tradecraft
for the systems that run **logistics, energy, and manufacturing** — the PLCs, field
buses, sensors, and embedded gear behind critical infrastructure. Its CTF reflects that
slant: alongside the usual web/pwn/crypto/forensics fare, this edition leaned heavily on
**ICS/OT** — raw Modbus/TCP, a custom Modbus function code, OPC-UA on a live Siemens
S7-1200 dosing skid, and FreeRTOS firmware on a Cortex-M "CO detector."

The CTF was Jeopardy-format. Flags take the form **`rstcon{...}`** (a couple of
challenges — OSINT geolocation and a Wi-Fi fox-hunt — are answered with a coordinate or
BSSID instead of a flag string).

## Challenges

Scored total of the solved, flag-bearing challenges: **2,090 pts**, plus three
non-pointed/physical solves (S7 dosing skid, Vacation Photo, Plutonium Stash).

### 🏭 ICS / OT

| Challenge | Pts | Technique | Flag |
|-----------|----:|-----------|------|
| [Modbus Mastermind](notes/modbus-mastermind.md) | 30 | World-writable Modbus/TCP holding registers; flag packed one ASCII char per register **low byte** (recoverable only on a clean instance after competitors griefed the shared board). | `rstcon{pymodbus_or_it_didnt_happen}` |
| [Vendor FC41](notes/vendor-fc41.md) | 10 | Reverse a vendor's **user-defined Modbus function code**; compute its bijective transform and send one matching `(seed, guess)` request. | `rstcon{user_defined_fc_reversed}` |
| [S7-1200 Dosing Skid](notes/s7-dosing-skid.md) | hw | Anonymous **OPC-UA** read/write on a Siemens S7-1200 lets you flip a writable Boolean that actuates a **real dosing pump**; the flag word is revealed physically on the rig. | `rstcon{ALUM_<redacted>_4840}` |

### 💥 Pwn

| Challenge | Pts | Technique | Flag |
|-----------|----:|-----------|------|
| [Leaky Logger](notes/leaky-logger.md) | 10 | Textbook **format string** — `printf(user_line)`; `%N$p` positional leaks pull the stack-resident flag out directly. | `rstcon{f0rmat_str1ngs_l3ak_the_stack}` |
| [Carbon Noneoxide](notes/carbon-noneoxide.md) | 10 | **FreeRTOS** firmware (Cortex-M): an unbounded index write overruns a log buffer into a **queue handle**, pointed at a forged `Queue_t` that leaks flash via `xQueueReceive`. | `rstcon{y0ur_Q_my_Q}` |
| [Thought Slop](notes/thought-slop.md) | 500 | A llama.cpp chatbot feeds the **LLM's own output** into `printf`; prime GPT-2 to emit `%p` and leak the stack flag (format string via model output). | `rstcon{nuclear_0pti0n_trash_EVERYTHING}` |

### 🌐 Web

| Challenge | Pts | Technique | Flag |
|-----------|----:|-----------|------|
| [Template Tide](notes/template-tide.md) | 10 | **Jinja2 SSTI** — user input rendered as template source; escalate to RCE via the `cycler` `__globals__` gadget. | `rstcon{ssti_rolls_in_with_the_t1de}` |
| [Dow is Up 50k](notes/dow-is-up-50k.md) | 10 | **"React2Shell"** (CVE-2025-55182) — pre-auth prototype pollution in the Next.js/React **Flight** deserializer reaches the `Function` constructor for RCE. | `rstcon{pr0t0typ3_p0llut10n_m3ets_r34ct_fl1ght}` |
| [MEDVAULT](notes/medvault.md) | — | **UNION-based SQLi** in a med-search box dumps the whole PHI + credentials DB. | ⚠️ unsolved / WIP (flag not captured) |

### 🔐 Crypto · 🧩 Reversing

| Challenge | Pts | Technique | Flag |
|-----------|----:|-----------|------|
| [ARC4 Reactor](notes/arc4-reactor.md) | 10 | **RC4 keystream reuse** between two files (one known-plaintext); XOR recovers the keystream, decrypts a hidden zip/PDF, flag from the PDF's ToUnicode CMap. | `rstcon{n3utronz_Go_BRRRR}` |
| [Carry the Tide](notes/carry-the-tide.md) | 500 | **SuperH** key-check binary using a chained **running-sum cipher** that's trivially invertible — solved in closed form by walking the target bytes backward. | `rstcon{running_sum_unwinds_in_reverse}` |

### 🔎 Forensics

| Challenge | Pts | Technique | Flag |
|-----------|----:|-----------|------|
| [Universal Suffering Begins (USB)](notes/universal-suffering-usb.md) | 500 | 104M-packet **USB 2.0 link-layer** capture; reassemble bulk transfers (keep ACK/NYET, drop NAK retransmits), flag is a PNG on **USB mass storage** behind a keyboard + printer decoy. | `rstcon{yu_es_be_m0n}` |
| [Do Not Service](notes/do-not-service.md) | 500 | **DNS exfiltration** over `www.<base64>.<rotating-TLD>` A-queries (TLD rotation dodges single-domain tunnel detection); decode the length-prefixed blobs. | `rstcon{d0main_n@m3_EXPansi0n}` |

### 🧭 OSINT · Misc

| Challenge | Technique | Answer |
|-----------|-----------|--------|
| [Vacation Photo](notes/vacation-photo.md) | **EXIF GPS** geolocation of a JPEG. | `41.265556, -95.922222` — Bob Kerrey Pedestrian Bridge |
| [Secret Plutonium Stash](notes/plutonium-stash.md) | Beat the macOS Location-Services gate by wrapping a CoreWLAN scanner in a **signed `.app`**, then fox-hunt the AP by RSSI. | BSSID `b8:fb:b3:98:91:de` |

## Repo layout

| Dir | What's in it |
|-----|--------------|
| `notes/`      | One writeup per challenge, `notes/<name>.md` — prompt, recon, the vulnerability/mechanism, exploitation, and the flag. **Start here.** |
| `solves/`     | Our scripts and exploits, one subdir per challenge (`solves/<name>/`). |
| `challenges/` | Provided challenge files, one subdir per challenge. Large binaries (pcaps, firmware, disk images) are not committed — see each challenge's note. |
| `tools/`      | Reusable helpers that aren't challenge-specific. |

Each writeup is self-contained and written to be followed by someone who **didn't** solve
the challenge: acronyms and techniques are introduced before they're used, dead ends are
recorded where they're instructive, and the exploit is shown, not just described.

## Conventions

- New challenge → create `challenges/<name>/` (given files), `solves/<name>/` (our work),
  and `notes/<name>.md` (the writeup). Record the flag in the writeup header as soon as
  it's found.
- `.gitignore` keeps `secrets.txt`, keys, and large binaries (pcaps, images, dumps) out of
  git by default — the writeup says where to re-download anything too big to commit.

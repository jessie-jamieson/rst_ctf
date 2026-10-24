# Do Not Service — Writeup

- **Category:** Network Forensics
- **Points:** 500
- **Flag:** `rstcon{d0main_n@m3_EXPansi0n}`
- **Author:** Veryyes
- **Description:** *The new IT guy said not to use this computer, I used it anyways.*
- **Artifact:** `odd_transmission.pcapng.gz` → `odd_transmission.pcapng` (~50 MB, 62,887 packets)

## TL;DR

**"Do Not Service" = DNS.** The capture is a conference-network session that
reads as ordinary web browsing — that's the misdirection. Hidden in the outbound
DNS from host `10.200.11.146` is a **DNS-exfiltration channel**: A-record queries
shaped `www.<base64>.<TLD>`, rotating the TLD across `.com/.net/.org/.club/.xyz`.
Each base64 label decodes to a length-prefixed record from a stolen contact list;
one planted record is the flag.

```
www.AB1yc3Rjb257ZDBtYWluX25AbTNfRVhQYW5zaTBufQ==.com
    └─ base64 → \x00\x1d rstcon{d0main_n@m3_EXPansi0n}
```

## Recon

`capinfos` / protocol hierarchy — a Pop!_OS laptop (`wlp2s0`, Linux 6.2.6
System76 kernel, `*.pop-os.org` captive checks) on a `10.200.0.0/16` conference
net. Mostly QUIC + TLS to Google/ad-tech/StackOverflow/thehackernews — normal
browsing. Only unicast TCP belongs to `10.200.11.146`, so that host is the suspect
("the computer the IT guy said not to use").

The title is the whole hint: **D**o **N**ot **S**ervice → **DNS**.

## The dead ends (and why the channel hid)

- Port-53 DNS is a single flow `10.200.11.146 → 10.200.0.1`, and grouping queries
  by *registered domain* shows nothing tunnel-like (max 50 queries to one domain,
  `mozgcp.net`). No TXT/NULL/long-label tunneling, no DoH/DoT, no external resolver.
- mDNS/NBNS/LLMNR/SNMP (Canon `canon_admin` printer discovery) all look benign.

The exfil queries defeat naive tunnel detection precisely **because each one is a
different registered domain** (`www.<blob>.com`, `www.<blob>.net`, …). They never
cluster under a single second-level domain, so "one domain, many subdomains"
heuristics miss them. They also blend into the dozens of real `www.*` lookups.

## Finding it

Sweep *all* name-service query labels for base64/hex-shaped tokens that aren't
standard service-discovery strings:

```bash
tshark -r odd_transmission.pcapng -Y "dns.flags.response==0" -T fields -e dns.qry.name \
 | tr ',' '\n' | grep -oE '[A-Za-z0-9+/_=-]{12,}' \
 | grep -vE 'companion|airplay|spotify|googlecast|MacBook|_tcp|_udp|local' \
 | sort -u
```

This surfaces a cluster of `AAxx…`/`ABxx…` base64 labels. Decoding shows a
length-prefixed string table:

```
AAlKYW1lcyBMZWU=              -> \x00\x09 James Lee
ABNDaHJpc3RvcGhlciBNaXJhbmRh -> \x00\x13 Christopher Miranda
AB1yc3Rjb257ZDBtYWluX25AbTNfRVhQYW5zaTBufQ== -> \x00\x1d rstcon{d0main_n@m3_EXPansi0n}
```

The `\x00\xNN` prefix is the record length — a wink at DNS label-length framing,
matching the flag text **domain name expansion**. The flag query is frame **31567**,
t≈473 s, from `10.200.11.146` (`2c:3b:70:5d:2b:65`).

## Solve

`solves/do-not-service/solve.py` — pulls every outbound A query shaped
`www.<b64>.<tld>`, strips the 2-byte length prefix, decodes, and prints the
reconstructed contact table plus the flag. One-liner equivalent:

```bash
tshark -r odd_transmission.pcapng -Y 'dns.qry.name contains "www." && dns.qry.type==1' \
  -T fields -e dns.qry.name \
 | grep -oE 'www\.[A-Za-z0-9+/=]+\.' | sed -E 's/^www\.//;s/\.$//' \
 | while read b; do echo "$b" | base64 -d 2>/dev/null | tr -d '\0'; echo; done \
 | grep rstcon
```

## Flag

```
rstcon{d0main_n@m3_EXPansi0n}
```

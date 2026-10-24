# Universal Suffering Begins (USB) — Writeup

- **Category:** Forensics / Hardware
- **Points:** 500
- **Flag:** `rstcon{yu_es_be_m0n}`
- **Description:** *"IN DATA1 ACK IN DATA1 ACK IN NACK IN NACK"* — plus a `data.pcap.gz`
  download (437 MB gz → 1.9 GB `data.pcap`, **104 million packets**).

## TL;DR

The pcap is a **USBLL (USB 2.0 link-layer)** capture taken with a hardware analyzer,
so every frame is a raw USB packet ID — `SOF`, `SPLIT`, `IN`/`OUT`, `DATA0`/`DATA1`,
`ACK`/`NAK`/`NYET`, `PING` — with no URB framing. Three devices are live on the bus,
and **two are elaborate decoys** built to waste your time (the "universal suffering"):

1. **Device 5 — HID keyboard.** Keystrokes decode to a fake medical note ending with
   *"Playing too many CTFs and not finding any flags LOL."*
2. **Device 7 — IPP-over-USB printer.** Four print jobs, each an Apple-Raster (URF)
   page image of a fake "MedVault" medical record. One Diagnosis field literally reads
   *"Lack of a rstcon{} flag lmao"* — which conveniently leaks the **flag format**.
3. **Device 6 — USB mass storage (NTFS).** The real payload. A `chainsaw_guy.png` was
   copied to the drive; its Chainsaw Man speech bubbles spell the flag.

`rstcon{yu_es_be_m0n}` reads aloud as "**U-S-B demon**".

## Recon

```
$ file data.pcap
data.pcap: pcap capture file, nanosecond ts ... (USB 2.0, capture length 65535)
$ capinfos -c data.pcap
Number of packets:   104 M        Capture duration: 159.8 s
```

First packets show the shape immediately — host polling, a hub doing SPLIT
transaction translation, and interrupt endpoints NAK-ing until they have data:

```
host → broadcast   USBLL SOF
host → 4:1         USBLL SPLIT Start          # high-speed hub @ addr 4
host → 5.1         USBLL IN
 5.1 → host        USBLL NAK                   # keyboard, nothing to report yet
```

Data-bearing endpoints across the whole capture (DATA0/DATA1 frames only):

| src→dst | pkts | what |
|---------|------|------|
| `host→7.3`, `host→7.10` | 6420 / 6174 | printer bulk-OUT (IPP print jobs) |
| `6.1→host` / `host→6.2` | 2427 / 750 | mass storage bulk-IN / -OUT (SCSI) |
| `5.1→host` | 888 | keyboard interrupt-IN (8-byte boot reports) |
| `7.6→host`, `7.11→host` | 884 / 653 | printer bulk-IN (IPP responses) |

## The one trick the whole challenge hinges on

Because this is a *link-layer* trace, you see **every retransmission**. High-speed bulk
transfers use the PING/NYET flow-control protocol: the host sends `DATA`, the device
answers `ACK` (accepted), `NYET` (accepted, but PING before next) or `NAK` (rejected —
host will resend the *same* bytes later). For the printer OUT pipe, almost exactly half
the DATA packets are NAK'd and retransmitted:

```
DATA → 7.10 followed by:   ACK (0xd2)  3131      <- real data
                           NAK (0x5a)  3043      <- retransmit, must be dropped
```

Naïvely concatenating every `usbll.data` payload therefore **doubles** packets and
corrupts the stream — you get two `UNIRAST` headers 512 bytes apart, broken ZIP/PNG,
garbage rasters. The fix is to reassemble at the transaction layer:

> **Keep a DATA packet only if the handshake in the very next frame is `ACK` (`0xd2`)
> — or, for high-speed bulk-OUT, `NYET` (`0x96`), which also means "accepted". Drop
> anything followed by `NAK`.**

With that rule every pipe reassembles cleanly (and the SCSI data phases all come back
exactly their declared `dCBWDataTransferLength`).

Extraction is one `tshark` pass per device, emitting frame / src / dst / pid / data:

```sh
tshark -r data.pcap -Y 'usbll.src=="6.1"||usbll.dst=="6.1"||usbll.src=="6.2"||usbll.dst=="6.2"' \
  -T fields -e frame.number -e usbll.src -e usbll.dst -e usbll.pid -e usbll.data > dev6.tsv
```

## Decoy 1 — the keyboard (device 5)

888 interrupt-IN reports, standard 8-byte USB HID boot-keyboard format
`[modifiers, reserved, key1..key6]`. Decoding key-down transitions with the US usage
table (and honoring Shift + Backspace) yields a chatty fake clinic note that ends:

```
... likely related to prolonged sedentary posture
Playing too many CTFs and not finding any flags LOL
```

→ `solves/.../hid_decode.py`. No flag.

## Decoy 2 — the printer (device 7, IPP-over-USB)

The `host→7.10` / `host→7.3` streams are **HTTP** (`POST /ipp/print HTTP/1.1`,
`Content-Type: application/ipp`) — this is IPP-over-USB. The bodies are **chunked**
transfer-encoded; after the IPP attribute block the document begins, and
`document-format = image/urf` with the magic `UNIRAST`: it's **Apple Raster**.

Steps: keep ACK'd DATA → de-chunk the HTTP → carve from `UNIRAST` → decode URF. The URF
page header (after the 8-byte magic + 4-byte page count) is 32 bytes with `bpp` at
offset 0 and big-endian `width`/`height`/`dpi` at offsets 12/16/20 → **5100×6600 @
600 dpi, 24-bpp RGB**. The raster lines are URF PackBits (`<line-repeat>` then control
bytes: `c<0x80` → repeat next pixel `c+1` times; `c>0x80` → `257-c` literal pixels).

All four pages render as pristine "MedVault" medical records (prescription, lab report,
intake form, EOB) — see `solves/.../pages/`. The prescription's Diagnosis field trolls
*"Lack of a rstcon{} flag lmao"*, which is the only useful thing here: **the flag format
is `rstcon{...}`.**

→ `reassemble_printer.py`, `dechunk_ipp.py`, `urf2png.py`. No flag.

## The real vector — mass storage (device 6, NTFS)

The `host→6.2` stream opens with `55534243` = **"USBC"**, the signature of a SCSI
**Command Block Wrapper** — this is USB Mass Storage / Bulk-Only Transport. Parsing the
CBWs (CDB opcodes) shows the OS mounting an NTFS volume and, notably, **14 WRITE10
commands** — files being *written* to the drive:

```
WRITE10 LBA=2064..2168      # NTFS $MFT / metadata (file creation)
WRITE10 LBA=30445584 ...    # file data region
READ10  LBA=0, 2048, 60625920...  # MBR, $MFT, backup $MFT at end of volume
```

Reassembling each CBW→data→CSW transaction (ACK/NYET rule) and placing the blocks at
their LBAs gives the touched sectors. The NTFS `$MFT` yields the filenames:

```
Alzheimer_Disease_A_Report.docx
chainsaw_guy.png   (8.3: CHAINS~1.PNG)
y.png
```

Two things were written. The **.docx** carves out of the WRITE data as a valid
10-entry ZIP — an innocuous "Alzheimer's Disease: A Report" (copied from WSL, per the
`$LXUID/$LXGID/$LXMOD` NTFS metadata streams). Another decoy.

The **PNG** also carves cleanly (`\x89PNG` … `IEND`, 387×516 RGB). Opening it:

> a Chainsaw Man panel edit whose speech bubbles read
> **`rstcon{yu_es_be_m0n}`** — twice — followed by *"… this is a ctf."*

→ `bot_carve.py`, `carve_png.py`.

## Flag

```
rstcon{yu_es_be_m0n}
```

## Takeaways

- A `LINKTYPE_USB_2_0` pcap is a *link-layer* trace: no URBs, so Wireshark won't reassemble
  transfers for you, and you must handle retransmissions yourself. The ACK/NYET-vs-NAK rule
  is the whole game.
- `tshark`'s `usbll` dissector tracks address/endpoint across token→data→handshake, so you
  can filter DATA and handshakes per endpoint even though handshake PIDs carry no address.
- Once reassembled, the upper layers are ordinary: HTTP+IPP+URF for the printer, SCSI BOT +
  NTFS for the drive. Identify the signature (`USBC`, `UNIRAST`, `%PNG`) and carve.
- Budget time for decoys. Three full, self-consistent payloads; only one is the flag.

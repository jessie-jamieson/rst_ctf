# Universal Suffering Begins (USB) — solve scripts

Raw capture: `data.pcap.gz` (437 MB gz → 1.9 GB `data.pcap`, 104 M packets).
It's a hardware **USBLL (USB 2.0 link-layer)** capture, so the pcap link type is
`LINKTYPE_USB_2_0` and every frame is a raw PID (SOF / SPLIT / IN / OUT / DATA0/1 /
ACK / NAK / NYET / PING). Not committed here due to size — see
`../../challenges/universal-suffering-usb/README.md`.

Requires `tshark` (Wireshark) and Python 3 with Pillow.

## Pipeline

```sh
# 0. decompress
gunzip -k data.pcap.gz

# 1. one extraction pass: every link-layer frame touching an endpoint we care about
#    (DATA packets + their handshakes), as TSV: frame, src, dst, pid, data
tshark -r data.pcap -Y 'usbll.src=="5.1" || usbll.dst=="5.1"' \
  -T fields -e frame.number -e usbll.src -e usbll.dst -e usbll.pid -e usbll.data > dev5.tsv
tshark -r data.pcap -Y 'usbll.src=="7.3"||usbll.dst=="7.3"||usbll.src=="7.10"||usbll.dst=="7.10"' \
  -T fields -e frame.number -e usbll.src -e usbll.dst -e usbll.pid -e usbll.data > printer.tsv
tshark -r data.pcap -Y 'usbll.src=="6.1"||usbll.dst=="6.1"||usbll.src=="6.2"||usbll.dst=="6.2"' \
  -T fields -e frame.number -e usbll.src -e usbll.dst -e usbll.pid -e usbll.data > dev6.tsv

# 2. keyboard (device 5) -> decoy text
python3 hid_decode.py dev5.tsv

# 3. printer (device 7, IPP-over-USB) -> 4 decoy page images
python3 reassemble_printer.py printer.tsv   # -> clean_7_10.bin, clean_7_3.bin
python3 dechunk_ipp.py clean_7_10.bin p710  # -> *.urf
python3 urf2png.py p710_doc2.urf p710_doc2  # -> PNG per page

# 4. mass storage (device 6, NTFS) -> the flag
python3 bot_carve.py dev6.tsv               # -> read_compact.bin, write_compact.bin
python3 carve_png.py write_compact.bin      # -> carved.png  == the flag
```

## The trick that matters

The capture is a *link-layer* trace, so for every bulk transfer about half the DATA
packets were **NAK'd / NYET-flow-controlled and retransmitted**. Reassembling by just
concatenating every `usbll.data` gives a corrupt stream (doubled URF headers, broken
ZIP/PNG). The fix: **keep a DATA packet only if the handshake immediately following it
is ACK (`0xd2`) — or, for high-speed bulk-OUT, NYET (`0x96`), which also means
"accepted".** NAK (`0x5a`) → drop, it's a retransmit.

## Three vectors, two decoys

| Device | Protocol | Payload | Verdict |
|--------|----------|---------|---------|
| 5 (HID keyboard) | interrupt IN, 8-byte boot reports | typed "Patient Visit Summary… LOL" | decoy |
| 7 (printer) | IPP-over-USB → URF/Apple-Raster | 4 "MedVault" medical records | decoy |
| 6 (mass storage) | SCSI Bulk-Only Transport, NTFS | `chainsaw_guy.png` | **flag** |

Flag: `rstcon{yu_es_be_m0n}`  ("U-S-B demon" — a Chainsaw Man panel).

# Universal Suffering Begins (USB) — challenge files

- **Provided:** `data.pcap.gz` (437 MB gzip → **1.9 GB** `data.pcap`, 104 M packets).
- **Capture type:** USBLL (USB 2.0 link-layer, `LINKTYPE_USB_2_0`).

The raw capture is **not committed** here — it is far too large for git. Grab it from
the challenge's download button / Google Drive mirror, then:

```sh
gunzip -k data.pcap.gz
```

Solve scripts and recovered artifacts: `../../solves/universal-suffering-usb/`.
Full writeup: `../../notes/universal-suffering-usb.md`.

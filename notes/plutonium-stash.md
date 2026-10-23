# Where's Waldo — "Secret Plutonium Stash" (misc)

**Prompt:** Who is "Secret Plutonium Stash" on the 2.4GHz band?
**Category:** misc · **Title hint:** "Where's Waldo"

## Answer

| Field | Value |
| --- | --- |
| SSID | `Secret Plutonium Stash` |
| **BSSID (the "who")** | **`b8:fb:b3:98:91:de`** |
| Vendor (OUI `b8:fb:b3`) | TP-Link Systems Inc. (block registered 2025-09-16) |
| Radio | channel 9, 2.4GHz |
| Signal at first contact | ~ -62 to -74 dBm |

The "who" is the access point's BSSID — the MAC address of the radio broadcasting
that SSID. The "2.4GHz band" qualifier matters: several neighbors (Gigawatt,
EPRIGuest) run dual-band twins with a **different MAC per radio**, so the band pins
which radio's MAC to report. "Secret Plutonium Stash" appeared only once, on 2.4GHz
channel 9, so there was no 5GHz twin to confuse it.

## Interpreting the title

"Where's Waldo" = find one target hidden in a crowd. The air held ~39 BSSIDs. The
SSID plus the band narrowed it to exactly one radio. A secondary reading ("where" =
physical location) led to the fox-hunt below.

## Environment and obstacles

Target was **live over the air**, not a capture file. macOS made this harder than it
should be:

1. **No `airport` CLI.** Apple removed `/System/.../Apple80211.framework/.../airport`
   in recent macOS. `tshark` / `kismet` were not installed either.
2. **`system_profiler SPAirPortDataType` redacts.** It listed neighbors but printed
   every SSID as `<redacted>` and no BSSIDs at all.
3. **Location Services gate.** Since macOS Sonoma, the OS only reveals Wi-Fi
   SSID/BSSID to a process whose controlling app holds Location Services permission.
   iTerm did not have it.
4. **A CLI tool cannot prompt for location.** A bare `swift` script has no bundle
   `Info.plist` with a location-usage string, so `CLLocationManager` returned
   `kCLErrorDomain error 1` and never prompted. iTerm never appeared in the Location
   Services list.

## Solution

Build a minimal **signed `.app` bundle** that carries `NSLocationUsageDescription`.
Launched with `open`, it runs as its own app (not as iTerm), so macOS shows a real
"allow location" prompt and registers it. Once authorized, CoreWLAN's
`scanForNetworks` returns real BSSIDs.

Steps:
1. `swiftc` the scanner into `WifiScan.app/Contents/MacOS/WifiScan`.
2. `Info.plist` with `CFBundleIdentifier` + `NSLocationUsageDescription`.
3. Ad-hoc codesign: `codesign --force --deep -s - WifiScan.app`.
4. `open WifiScan.app`, click **Allow** on the prompt.
5. App scans, writes SSID / BSSID / channel / band / RSSI to a file.

Result line:
```
Secret Plutonium Stash bssid=b8:fb:b3:98:91:de ch=9 2.4GHz rssi=-74  <<< MATCH
```

Vendor confirmed against two OUI sources (api.macvendors.com and maclookup.app):
`b8:fb:b3` → TP-Link Systems Inc.

## Fox-hunt ("Where's Waldo", literally)

To physically locate the AP, re-used the same signed app as a **live RSSI meter**
(`live.swift`): one reading every ~1.5s, a WARMER/colder trend vs the last reading,
and a **peak-hold** of the strongest RSSI seen so far.

Walking technique:
- RSSI in dBm, negative; closer to 0 = closer to the AP.
- Hold the laptop level in front of you; the body blocks 2.4GHz, so turning a full
  circle and noting the strongest heading points the way.
- Rising number / WARMER = right direction; falling / colder = turn around.
- Walls and metal cause reflections and false peaks; trust the overall trend.
- Below ~ -45 dBm the AP is within a few feet. It was a small TP-Link box.

Homed in from ~ -74 dBm down to the device. Found it. ✅

## Files

| File | Role |
| --- | --- |
| `solves/plutonium-stash/scan.swift` | First CoreWLAN CLI scanner (showed SSIDs, BSSIDs nil — proved the location gate). |
| `solves/plutonium-stash/main.swift` | The `.app`-bundle scanner that requests location and dumps all BSSIDs. |
| `solves/plutonium-stash/live.swift` | Live RSSI fox-hunt meter with trend + peak-hold. |
| `solves/plutonium-stash/scan-output.txt` | Raw 39-BSS scan evidence, target line marked. |

A separate `locauth.swift` probe (bare CLI `CLLocationManager`) was a dead end — it
confirmed obstacle #4 and is not included.

## Takeaways

- On modern macOS, `airport` is gone; use CoreWLAN, and remember SSID/BSSID need
  Location Services.
- To grant a terminal tool location, wrap it in a signed `.app` with a usage string
  and launch with `open`.
- RSSI + peak-hold is enough for a short-range fox-hunt indoors.

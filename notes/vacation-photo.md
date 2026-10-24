# Vacation Photo — Writeup

- **Category:** OSINT / Forensics (EXIF geolocation)
- **Tolerance:** 500 m
- **Answer:** `41.265556, -95.922222` — **Bob Kerrey Pedestrian Bridge**, over the
  Missouri River between **Omaha, NE** and **Council Bluffs, IA**.
- **Description:** *A contact sent us this "vacation photo." The picture itself
  is nothing, but the photographer was not careful about what their camera wrote
  into it. Figure out exactly where this was taken.*

## TL;DR

The photo (`solves/vacation-photo/vacation.jpg`, a plain 640×480 JPEG) carries a
full **EXIF GPS tag**. The camera recorded the exact coordinates, and a chatty
`UserComment` confirms the spot. Read the GPS IFD, convert DMS → decimal, done:

```
41°15'56"N, 95°55'20"W  ->  41.265556, -95.922222
```

That point lands on the **Bob Kerrey Pedestrian Bridge**, which crosses the
Missouri River — the **Nebraska/Iowa state line**.

## Pulling the metadata

No stego, no tricks — it's straight EXIF. Reading it with Pillow
(`solves/vacation-photo/exif_geo.py`, run as `python3 -I exif_geo.py <image>`):

```
Make:              Canon
Model:             Canon EOS R7
Software:          field-capture 2.1
DateTimeOriginal:  2026:05:14 18:42:11
UserComment:       caught the sunset with one foot in each state

GPSLatitudeRef:    N
GPSLatitude:       (41, 15, 56)
GPSLongitudeRef:   W
GPSLongitude:      (95, 55, 20)
GPSAltitude:       335.0 m
```

Convert degrees/minutes/seconds to decimal (negate for S/W):

```
lat = 41 + 15/60 + 56/3600            = 41.265556
lon = -(95 + 55/60 + 20/3600)         = -95.922222
```

## Why this is the spot

Every field agrees:

- **GPS** places the camera on a pedestrian bridge over the Missouri River.
- **`UserComment`: "one foot in each state."** The Missouri River there is the
  **NE/IA border**; the Bob Kerrey Pedestrian Bridge has a marked state line at
  mid-span where you stand with a foot in each state.
- **"caught the sunset"** → facing west, out over the river.
- **DateTimeOriginal 18:42 on May 14** fits a spring sunset.

No flag string is embedded in the file — the deliverable is the location itself.
Submitting `41.265556, -95.922222` is the exact camera-recorded point, well
inside the 500 m tolerance.

## Lesson

Cameras and "field capture" apps happily stamp precise GPS (and free-text
comments) into EXIF. If you don't want to broadcast where a photo was taken,
strip metadata before sharing — the picture being "nothing" doesn't matter when
the header gives you away.

## Tooling

- `solves/vacation-photo/exif_geo.py` — dumps EXIF + the GPS IFD and converts to
  decimal degrees with a Maps link.
- `solves/vacation-photo/vacation.jpg` — the challenge image.

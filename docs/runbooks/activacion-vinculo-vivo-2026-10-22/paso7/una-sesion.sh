#!/bin/bash
# uso: una-sesion.sh <cuerpo.sh> [fichero ...] — UNA conexión SSH al .166 (rechaza ráfagas). Credencial por stdin, nunca en argv.
set -euo pipefail
source ~/.secrets/midpoint-upeu.env
L=/Users/alberto/proyectos/productos/iga/canonico/.worktrees/fusion-hulda/docs/runbooks/fusion-hulda-2026-10-28/lib
esc() { local s=${1//\\/\\\\}; s=${s//\"/\\\"}; printf '%s' "${s//\'/\'\\\'\'}"; }
CUERPO=$1; shift
{
  echo 'set -eu'
  printf "A='%s'\n" "$(esc "$MIDPOINT_ADMIN_USER:$MIDPOINT_ADMIN_PASS")"
  cat <<'P'
cred() { printf 'user = "%s"\n' "$A"; }
F=$(mktemp -d); trap 'rm -rf "$F"' EXIT
pg() { docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' midpoint-midpoint_data-1 \
    psql -U midpoint -d midpoint -q -At -F '|' -P pager=off; }
mp() { local d=(); [ -n "${4:-}" ] && d=(--data-binary @"$4")
  curl -sS -m 900 -K <(cred) -X "$1" -H "Content-Type: ${3:-application/xml}" -H 'Accept: application/xml' "${d[@]}" \
    -w '\nHTTP %{http_code}\n' "http://localhost:8080/midpoint/ws/rest/$2"; }
P
  for f in "$@"; do printf "base64 -d > \"\$F/%s\" <<'B64'\n%s\nB64\n" "$(basename "$f")" "$(base64 < "$f" | tr -d '\n')"; done
  cat "$CUERPO"
} | "$L/mp.sh" "bash -s"

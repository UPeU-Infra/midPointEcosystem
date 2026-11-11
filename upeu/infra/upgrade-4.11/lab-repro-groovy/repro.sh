#!/usr/bin/env bash
#
# repro.sh — reproduce en el lab el fallo de F3 sin Oracle (ver README.md)
#
#   ./repro.sh preparar              baja el bundle ScriptedSQL 2.2.10 de Maven Central,
#                                    comprueba que es el MISMO jar que PROD (sha256) y
#                                    genera .env (600) con contraseñas aleatorias
#   ./repro.sh probar <ver> <puerto> levanta midPoint <ver> vacío, crea el recurso de
#                                    prueba, lanza el test de conexión e imprime el
#                                    resultado y la traza del log si sale Whitelist
#   ./repro.sh bajar <ver>           para y BORRA ese proyecto (contenedores y volúmenes)
#
# Solo toca contenedores/volúmenes del proyecto mprepro<ver sin puntos>. Nada sale del lab.
set -euo pipefail
cd "$(dirname "$0")"
JAR=net.tirasa.connid.bundles.db.scriptedsql-2.2.10-bundle.jar
URL=https://repo1.maven.org/maven2/net/tirasa/connid/bundles/db/net.tirasa.connid.bundles.db.scriptedsql/2.2.10/$JAR
SHA_PROD=c4d1f0bd3549e92c3f8aaf481fb1a74a270b611d3ed50b01ad4840f33d5c27f9   # /opt/midpoint/connectors en PROD, 11-nov
RES_OID=5c1f3a2e-0b7d-4e6a-9f11-4110a5c0f3e1
proyecto() { echo "mprepro${1//./}"; }
dc() { local v=$1 p=${2:-0}; shift 2; MP_VER=$v PORT=$p docker compose -p "$(proyecto "$v")" --env-file .env "$@"; }

case "${1:-}" in
preparar)
    mkdir -p connectors
    [[ -f connectors/$JAR ]] || curl -fsS -o "connectors/$JAR" "$URL"
    echo "$SHA_PROD  connectors/$JAR" | sha256sum -c -
    if [[ ! -f .env ]]; then
        umask 077
        printf 'MP_DB_PASSWORD=%s\nMP_ADMIN_PASSWORD=Lab-%s-9a\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 12)" > .env
    fi
    ls -l .env connectors/
    ;;
probar)
    V="${2:?falta version}"; P="${3:?falta puerto}"
    dc "$V" "$P" up -d
    echo "esperando a midPoint $V en :$P ..."
    t0=$(date +%s)
    until curl -fsS "http://localhost:$P/midpoint/actuator/health" 2>/dev/null | grep -q UP; do
        (( $(date +%s) - t0 > 900 )) && { echo "ABORTO: no arranca en 15 min"; dc "$V" "$P" logs --tail 40 midpoint_server; exit 1; }
        sleep 10
    done
    echo "UP en $(( $(date +%s) - t0 )) s"
    DB=$(dc "$V" "$P" ps -q midpoint_data)
    psql() { docker exec -i "$DB" psql -U midpoint -d midpoint -tA "$@" </dev/null; }
    psql -c "SELECT 'nodo', version FROM m_node" || true
    COID=""
    for _ in $(seq 1 30); do
        COID=$(psql -c "SELECT oid FROM m_connector WHERE connectortype LIKE '%ScriptedSQLConnector' LIMIT 1")
        [[ -n "$COID" ]] && break; sleep 5
    done
    [[ -n "$COID" ]] || { echo "ABORTO: midPoint no descubrió el bundle ScriptedSQL"; exit 1; }
    psql -c "SELECT 'conector', oid, connectorversion, framework, available FROM m_connector WHERE oid='$COID'" 2>/dev/null \
      || psql -c "SELECT 'conector', oid FROM m_connector WHERE oid='$COID'"
    set -a; . ./.env; set +a
    T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
    printf 'user = "administrator:%s"\n' "$MP_ADMIN_PASSWORD" > "$T/curl.cfg"
    sed -e "s/@CONNECTOR_OID@/$COID/" -e "s/@DB_PASS@/$MP_DB_PASSWORD/" recurso-scriptedsql-postgres.xml.tmpl > "$T/res.xml"
    REST="http://localhost:$P/midpoint/ws/rest"
    code=$(curl -sS -K "$T/curl.cfg" -o "$T/post.out" -w '%{http_code}' -X POST -H 'Content-Type: application/xml' --data-binary @"$T/res.xml" "$REST/resources?options=overwrite")
    echo "POST recurso: HTTP $code"; [[ "$code" =~ ^20 ]] || { cat "$T/post.out"; exit 1; }
    code=$(curl -sS -K "$T/curl.cfg" -o "$T/test.out" -w '%{http_code}' -X POST -H 'Accept: application/xml' "$REST/resources/$RES_OID/test")
    echo "TEST conexión: HTTP $code"
    echo "--- estados del OperationResult (operación | estado | mensaje):"
    python3 - "$T/test.out" <<'PY'
import sys, xml.etree.ElementTree as ET
r = ET.parse(sys.argv[1]).getroot()
def loc(e): return e.tag.split('}')[-1]
def walk(e, d=0):
    op = st = msg = ''
    for c in e:
        if loc(c) == 'operation': op = (c.text or '').split('.')[-1]
        elif loc(c) == 'status': st = c.text or ''
        elif loc(c) == 'message': msg = (c.text or '')[:220]
    if op or st: print(f"{'  '*d}{op} | {st} | {msg}")
    for c in e:
        if loc(c) == 'partialResults': walk(c, d + 1)
walk(r)
PY
    echo "--- log del servidor: primera aparición de Whitelist y su traza"
    dc "$V" "$P" logs --no-log-prefix midpoint_server 2>/dev/null \
      | grep -n -m1 -A60 'scriptsecurity/sandbox/Whitelist' \
      | grep -E 'Whitelist|Caused by|NoClassDefFound|ClassNotFound|at org\.identityconnectors|at net\.tirasa|at groovy|at org\.codehaus' | head -25 \
      || echo "(no aparece Whitelist en el log)"
    ;;
bajar)
    V="${2:?falta version}"
    dc "$V" 0 down -v
    ;;
*) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

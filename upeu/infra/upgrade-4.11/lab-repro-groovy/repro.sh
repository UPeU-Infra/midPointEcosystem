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
#   ./repro.sh preparar-parche       baja a lib-parche/ las 2 librerías del parche en prueba
#                                    (sha1 de Maven Central fijados aquí)
#   PARCHE=1|b|c ./repro.sh probar|bajar ...   lo mismo con lib-parche[-b|-c]/ montado en var/lib
#                                    (proyecto aparte: mprepro<ver>p[b|c])
#   TMPL=<plantilla> ./repro.sh probar ...      usa otra plantilla de recurso
#
# Solo toca contenedores/volúmenes del proyecto mprepro<ver sin puntos>. Nada sale del lab.
set -euo pipefail
cd "$(dirname "$0")"
JAR=net.tirasa.connid.bundles.db.scriptedsql-2.2.10-bundle.jar
URL=https://repo1.maven.org/maven2/net/tirasa/connid/bundles/db/net.tirasa.connid.bundles.db.scriptedsql/2.2.10/$JAR
SHA_PROD=c4d1f0bd3549e92c3f8aaf481fb1a74a270b611d3ed50b01ad4840f33d5c27f9   # /opt/midpoint/connectors en PROD, 11-nov
RES_OID=5c1f3a2e-0b7d-4e6a-9f11-4110a5c0f3e1
PARCHE="${PARCHE:-0}"
# PARCHE=1 -> lib-parche/ (las 2 librerias); PARCHE=b -> lib-parche-b/ (solo groovy-security-sandbox)
LIB_PARCHE=./lib-parche; [[ $PARCHE != 0 && $PARCHE != 1 ]] && LIB_PARCHE=./lib-parche-$PARCHE; export LIB_PARCHE
proyecto() { local s=""; [[ $PARCHE == 1 ]] && s=p; [[ $PARCHE != 0 && $PARCHE != 1 ]] && s=p$PARCHE; echo "mprepro${1//./}$s"; }
dc() {
    local v=$1 p=${2:-0}; shift 2
    local f=(-f docker-compose.yml); [[ $PARCHE != 0 ]] && f+=(-f docker-compose.parche.yml)
    MP_VER=$v PORT=$p docker compose -p "$(proyecto "$v")" "${f[@]}" --env-file .env "$@"
}

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
preparar-parche)
    mkdir -p lib-parche
    MC=https://repo1.maven.org/maven2
    while read -r sha rel; do
        f=lib-parche/${rel##*/}
        [[ -f $f ]] || curl -fsS -o "$f" "$MC/$rel"
        echo "$sha  $f" | sha1sum -c -
    done <<'LIST'
eb606473a9e19afe2806ddf6fd92a59354fabc05 net/tirasa/groovy-security-sandbox/1.1.0/groovy-security-sandbox-1.1.0.jar
1640cfc18ff8281476a32f5c2af91da65d927225 org/craftercms/groovy-sandbox/4.3.2/groovy-sandbox-4.3.2.jar
LIST
    chmod 644 lib-parche/*.jar; ls -l lib-parche
    # variante b: solo la que contiene Whitelist/Blacklist; sin org.kohsuke SandboxTransformer,
    # el constructor del ejecutor de ConnId captura NoClassDefFoundError y DESACTIVA el sandbox
    mkdir -p lib-parche-b; cp -p lib-parche/groovy-security-sandbox-1.1.0.jar lib-parche-b/; ls -l lib-parche-b
    # variante c (la elegida para F3): las 2 librerias + una lista negra VACIA que se carga antes que la
    # de ConnId (verificado: var/lib va primero en el classpath). El sandbox queda activo pero no prohibe
    # nada, como en 4.10.5. OJO: no arregla eachRow (ese fallo no es de la lista negra): hace falta toRowResult().
    mkdir -p lib-parche-c; cp -p lib-parche/*.jar lib-parche-c/
    python3 -I -c "
import zipfile
with zipfile.ZipFile('lib-parche-c/zz-groovy-blacklist-vacia.jar', 'w') as z:
    z.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n\n')
    z.writestr('META-INF/groovy.blacklist', '# vacia: neutraliza la lista negra del sandbox Groovy de ConnId 1.7.0.0-M0\n')
"
    chmod 644 lib-parche-c/*.jar; ls -l lib-parche-c
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
    sed -e "s/@CONNECTOR_OID@/$COID/" -e "s/@DB_PASS@/$MP_DB_PASSWORD/" recurso-scriptedsql-postgres.xml.tmpl > "$T/res.xml"; [[ -n "${TMPL:-}" ]] && sed -e "s/@CONNECTOR_OID@/$COID/" -e "s/@DB_PASS@/$MP_DB_PASSWORD/" "$TMPL" > "$T/res.xml"
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
    for filtro in '' 'administrator'; do
        if [[ -z $filtro ]]; then
            cond=''; etiqueta='BÚSQUEDA todos'
        else
            cond="<q:equal><q:path>attributes/icfs:name</q:path><q:value>$filtro</q:value></q:equal>"; etiqueta="BÚSQUEDA __NAME__=$filtro"
        fi
        cat > "$T/q.xml" <<XML
<q:query xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3" xmlns:ri="http://midpoint.evolveum.com/xml/ns/public/resource/instance-3" xmlns:icfs="http://midpoint.evolveum.com/xml/ns/public/connector/icf-1/resource-schema-3">
  <q:filter><q:and>
    <q:ref><q:path>resourceRef</q:path><q:value oid="$RES_OID"/></q:ref>
    <q:equal><q:path>objectClass</q:path><q:value>ri:AccountObjectClass</q:value></q:equal>
    $cond
  </q:and></q:filter>
</q:query>
XML
        code=$(curl -sS -K "$T/curl.cfg" -o "$T/s.out" -w '%{http_code}' -X POST -H 'Content-Type: application/xml' -H 'Accept: application/xml' --data-binary @"$T/q.xml" "$REST/shadows/search")
        n=$(grep -o '<name>[^<]*</name>' "$T/s.out" | sort -u | tr '\n' ' ' || true)
        echo "$etiqueta: HTTP $code; nombres: ${n:-(ninguno)}"; [[ -n $n ]] || { echo "  respuesta:"; head -c 1500 "$T/s.out"; echo; }
        [[ "$code" =~ ^20 ]] || { grep -o '<message>[^<]*' "$T/s.out" | head -3 || true; }
    done
    echo "--- log del servidor: primera aparición de Whitelist y su traza"
    dc "$V" "$P" logs --no-log-prefix midpoint_server 2>/dev/null \
      | grep -n -m1 -A60 -E 'scriptsecurity/sandbox/Whitelist|SecurityException|[Ss]andbox' \
      | grep -E 'Whitelist|Caused by|NoClassDefFound|ClassNotFound|at org\.identityconnectors|at net\.tirasa|at groovy|at org\.codehaus' | head -25 \
      || echo "(no aparece Whitelist en el log)"
    ;;
bajar)
    V="${2:?falta version}"
    dc "$V" 0 down -v
    ;;
*) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

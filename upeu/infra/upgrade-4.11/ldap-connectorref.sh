#!/usr/bin/env bash
#
# ldap-connectorref.sh
# ------------------------------------------------------------------------------
# Cambia el connectorRef del recurso LDAP-IdentityCache-UPeU al conector LDAP
# BUNDLED de la version de midPoint recien arrancada. Es el unico recurso de UPeU
# con conector bundled (inventario §2), y cada midPoint trae el suyo:
#
#     midPoint 4.10.2 -> connector-ldap 3.9.2   (hoy, OID 31072286-...)
#     midPoint 4.10.5 -> connector-ldap 3.9.4   (pom.xml del tag v4.10.5)  -> ventana F2
#     midPoint 4.11.0 -> connector-ldap 3.10    (pom.xml del tag v4.11.0)  -> ventana F3
#
# Al arrancar una version nueva, midPoint registra el conector nuevo como un
# objeto ConnectorType NUEVO (OID nuevo) y marca el anterior available=false
# (medido en PROD: los LdapConnector/AdLdapConnector 3.9.1 quedaron available=f
# tras la subida 4.9.5 -> 4.10.2). Hasta cambiar el connectorRef, el recurso
# LDAP (58.883 cuentas) no funciona.
#
# El OID del conector nuevo NO se conoce de antemano: lo genera midPoint al
# descubrirlo. Este script lo busca en m_connector (solo lectura) y exige que
# haya exactamente uno, available=true.
#
# SIEMPRE PATCH del item connectorRef, NUNCA PUT (docs/runbooks/NUNCA-PUT-resources-schema-cache.md).
#
# ORDENES
#   show                 solo lectura: connectorRef actual, version del objeto,
#                        tamano del <schema> cacheado y conectores LDAP registrados
#   find  <version>      solo lectura: OID del LdapConnector <version> disponible
#   apply <version>      PATCH connectorRef -> OID de <version>; verifica version
#                        del objeto (+1), connectorRef (GET raw) y que el <schema>
#                        sigue presente. Pide confirmacion (o --yes).
#   test                 test connection del recurso (POST .../test), imprime estados
#
# VUELTA ATRAS del PATCH: `apply <version anterior>`. Solo tiene sentido si ese
# conector sigue available=true (p. ej. se dejo su JAR en icf-connectors). En una
# vuelta atras COMPLETA (restaurar el dump previo) el connectorRef vuelve con la BD
# y no hace falta nada.
#
# Corre en el HOST de midPoint (REST en localhost, psql por docker exec). La
# contrasena REST se pide por teclado si MP_REST_PASS no esta definida.
#
# ENTORNO
#   MP_BASE        (http://localhost:8080/midpoint)   -> en el lab, su puerto
#   MP_REST_USER   (administrator)
#   PG_CONTAINER   (midpoint-midpoint_data-1)
#   RESOURCE_OID   (7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f)
# ------------------------------------------------------------------------------
set -euo pipefail

MP_BASE="${MP_BASE:-http://localhost:8080/midpoint}"
MP_REST_USER="${MP_REST_USER:-administrator}"
PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"
RESOURCE_OID="${RESOURCE_OID:-7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f}"
CONNECTOR_TYPE="${CONNECTOR_TYPE:-com.evolveum.polygon.connector.ldap.LdapConnector}"
HERE="$(cd "$(dirname "$0")" && pwd)"

sql() {
    docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$PG_CONTAINER" \
        psql -U midpoint -d midpoint -tA -F'|' -v ON_ERROR_STOP=1
}

need_pass() {
    if [[ -z "${MP_REST_PASS:-}" ]]; then
        read -r -s -p "Contrasena REST de $MP_REST_USER: " MP_REST_PASS; echo
    fi
}

rest() {  # rest METHOD PATH [curl args...]
    local m="$1" p="$2"; shift 2
    curl -sS -o "$TMPD/body" -w '%{http_code}' -u "$MP_REST_USER:$MP_REST_PASS" -X "$m" "$MP_BASE/ws/rest/$p" "$@"
}

state() {
    printf "SELECT r.version, r.connectorreftargetoid, c.connectorversion, c.available,
                   length((convert_from(r.fullobject,'UTF8')::jsonb->'resource'->'schema')::text)
            FROM m_resource r LEFT JOIN m_connector c ON c.oid = r.connectorreftargetoid
            WHERE r.oid = '%s';" "$RESOURCE_OID" | sql
}

find_oid() {
    local v="$1" rows n
    rows=$(printf "SELECT oid, available FROM m_connector WHERE connectortype = '%s' AND connectorversion = '%s';" \
        "$CONNECTOR_TYPE" "$v" | sql)
    n=$(grep -c . <<< "$rows" || true)
    if [[ "$n" != "1" ]]; then
        echo "ERROR: se esperaba 1 conector $CONNECTOR_TYPE $v y hay $n:" >&2; echo "$rows" >&2; return 1
    fi
    if [[ "${rows#*|}" != "t" ]]; then
        echo "ERROR: el conector $v existe pero available=${rows#*|}" >&2; return 1
    fi
    echo "${rows%%|*}"
}

TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT

case "${1:-}" in
show)
    echo "Recurso $RESOURCE_OID: version|connectorRef|version conector|available|tamano <schema>"
    state
    echo "Conectores LDAP registrados (oid|tipo|version|available):"
    echo "SELECT oid, connectortype, connectorversion, available FROM m_connector WHERE connectorbundle = 'com.evolveum.polygon.connector-ldap' ORDER BY connectorversion, connectortype;" | sql
    ;;
find)
    find_oid "${2:?falta la version, p. ej. 3.9.4}"
    ;;
apply)
    V="${2:?falta la version, p. ej. 3.9.4}"
    NEW=$(find_oid "$V")
    IFS='|' read -r VER0 REF0 CV0 AV0 SL0 <<< "$(state)"
    echo "Antes: version=$VER0 connectorRef=$REF0 ($CV0, available=$AV0) schema=$SL0 caracteres"
    [[ "$REF0" == "$NEW" ]] && { echo "Ya apunta a $NEW ($V). Nada que hacer."; exit 0; }
    [[ "$SL0" =~ ^[0-9]+$ && "$SL0" -gt 1000 ]] || { echo "ABORTO: el recurso no tiene <schema> cacheado razonable ($SL0)." >&2; exit 3; }
    echo "Despues: connectorRef=$NEW ($V)"
    if [[ "${3:-}" != "--yes" ]]; then
        read -r -p "¿Aplicar el PATCH? escribe SI: " ok; [[ "$ok" == "SI" ]] || { echo "Cancelado."; exit 1; }
    fi
    need_pass
    sed "s/__NEW_CONNECTOR_OID__/$NEW/" "$HERE/ldap-connectorref-patch.xml.tmpl" > "$TMPD/patch.xml"
    code=$(rest PATCH "resources/$RESOURCE_OID" -H 'Content-Type: application/xml' --data-binary @"$TMPD/patch.xml")
    echo "PATCH -> HTTP $code (un 204 NO prueba nada: se verifica a continuacion)"
    [[ "$code" =~ ^2 ]] || { cat "$TMPD/body" >&2; exit 4; }
    IFS='|' read -r VER1 REF1 CV1 AV1 SL1 <<< "$(state)"
    echo "Ahora: version=$VER1 connectorRef=$REF1 ($CV1, available=$AV1) schema=$SL1 caracteres"
    code=$(rest GET "resources/$RESOURCE_OID?options=raw" -H 'Accept: application/xml')
    RAWREF=$(python3 -c "import re,sys; m=re.search(r'<connectorRef[^>]*oid=\"([0-9a-f-]{36})\"', open(sys.argv[1]).read()); print(m.group(1) if m else '')" "$TMPD/body")
    fail=0
    [[ "$VER1" -gt "$VER0" ]] || { echo "FALLO: la version del objeto no subio ($VER0 -> $VER1)"; fail=1; }
    [[ "$REF1" == "$NEW" && "$RAWREF" == "$NEW" ]] || { echo "FALLO: connectorRef BD=$REF1 GET raw=$RAWREF (esperado $NEW)"; fail=1; }
    [[ "$SL1" =~ ^[0-9]+$ && "$SL1" -gt 1000 ]] || { echo "FALLO: el <schema> cacheado desaparecio ($SL1)"; fail=1; }
    [[ $fail -eq 0 ]] && echo "OK: connectorRef -> $V verificado. Siguiente: $0 test" || exit 5
    ;;
test)
    need_pass
    code=$(rest POST "resources/$RESOURCE_OID/test" -H 'Accept: application/xml')
    echo "POST test -> HTTP $code"
    python3 - "$TMPD/body" <<'PY'
import re, sys
x = open(sys.argv[1], encoding='utf-8', errors='replace').read()
ops = re.findall(r'<(?:\w+:)?operation>([^<]+)</(?:\w+:)?operation>\s*<(?:\w+:)?status>([^<]+)</', x)
for op, st in ops: print(f'  {st:15s} {op}')
top = re.search(r'<(?:\w+:)?status>([^<]+)</', x)
print('ESTADO GLOBAL:', top.group(1) if top else 'desconocido')
PY
    ;;
*)
    sed -n '2,50p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

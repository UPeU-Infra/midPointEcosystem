#!/usr/bin/env bash
#
# aislar-midpoint.sh — SEGUNDA capa del aislamiento del clon F1 (dentro de midPoint)
# ------------------------------------------------------------------------------
# Se ejecuta con el clon arrancado CON EL PLANIFICADOR PARADO (override de ventana)
# y con aislamiento-red.sh ya aplicado y comprobado. Cambia SOLO la BD del clon:
#
#   1. LDAP, Koha, Zammad y Entra -> administrativeOperationalState/
#      administrativeAvailabilityStatus = maintenance: midPoint no los contacta y deja
#      las operaciones como pendientes en el shadow (docs Evolveum "Resource
#      Maintenance State", experimental desde 4.2; por eso es la 2.a capa, no la 1.a).
#      Los 8 Oracle LAMB siguen operativos: solo lectura (create/update/delete
#      deshabilitados en las capabilities, medido en PROD el 28-oct).
#   2. SystemConfiguration -> sin messageTransportConfiguration (el transporte de
#      Telegram): el clon no puede avisar al grupo real aunque la red lo dejara.
#   3. Suspende las 8 tareas de negocio (../tareas-ventana.sh suspender).
#
# ORDENES: aplicar | comprobar
# ENTORNO: MP_BASE (http://localhost:8085/midpoint), MP_REST_USER, MP_REST_PASS,
#          PG_CONTAINER (mp411_data)
# ------------------------------------------------------------------------------
set -euo pipefail
export MP_BASE="${MP_BASE:-http://localhost:8085/midpoint}"
export MP_REST_USER="${MP_REST_USER:-administrator}"
export PG_CONTAINER="${PG_CONTAINER:-mp411_data}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ESCRITORES=(
  7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f   # LDAP-IdentityCache-UPeU
  e10a539a-cb7f-4c72-a19f-60f7f62e4b96   # Koha ILS UPeU (consolidado)
  7a11d0d0-0000-4000-a000-7a11d0d00001   # Zammad UPeU
  2f11c057-7b15-4641-a0eb-00c98a6fa4cb   # UPEU-EntraID-Graph
)
SYSCONFIG=00000000-0000-0000-0000-000000000001
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
NS='xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3" xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3"'

patch() {  # patch <tipo> <oid> <fichero>
    local code
    code=$(curl -sS -o "$T/body" -w '%{http_code}' -u "$MP_REST_USER:$MP_REST_PASS" -X PATCH \
        -H 'Content-Type: application/xml' --data-binary @"$3" "$MP_BASE/ws/rest/$1/$2")
    echo "  PATCH $1/$2 -> HTTP $code"; [[ "$code" =~ ^2 ]] || { cat "$T/body" >&2; return 1; }
}
sql() { docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$PG_CONTAINER" psql -U midpoint -d midpoint -tA -F'|'; }

comprobar() {
    echo "Recursos (nombre|administrativeAvailabilityStatus):"
    echo "SELECT nameorig, coalesce(convert_from(fullobject,'UTF8')::jsonb->'resource'->'administrativeOperationalState'->>'administrativeAvailabilityStatus','operational (sin valor)') FROM m_resource ORDER BY 1;" | sql
    echo "SystemConfiguration: messageTransportConfiguration presente = $(echo "SELECT (convert_from(fullobject,'UTF8')::jsonb->'systemConfiguration') ? 'messageTransportConfiguration' FROM m_object WHERE oid = '$SYSCONFIG';" | sql)"
    "$HERE/../tareas-ventana.sh" estado
}

case "${1:-}" in
aplicar)
    [[ -n "${MP_REST_PASS:-}" ]] || { read -r -s -p "Contrasena REST de $MP_REST_USER (CLON): " MP_REST_PASS; echo; export MP_REST_PASS; }
    case "$MP_BASE" in *192.168.15.166*|*identity.upeu.edu.pe*|*localhost:8080*) echo "ABORTO: MP_BASE=$MP_BASE parece PROD" >&2; exit 3 ;; esac
    cat > "$T/maint.xml" <<EOF
<objectModification $NS><itemDelta><t:modificationType>replace</t:modificationType>
<t:path>c:administrativeOperationalState/c:administrativeAvailabilityStatus</t:path><t:value>maintenance</t:value></itemDelta></objectModification>
EOF
    cat > "$T/notransport.xml" <<EOF
<objectModification $NS><itemDelta><t:modificationType>replace</t:modificationType>
<t:path>c:messageTransportConfiguration</t:path></itemDelta></objectModification>
EOF
    for o in "${ESCRITORES[@]}"; do patch resources "$o" "$T/maint.xml"; done
    patch systemConfigurations "$SYSCONFIG" "$T/notransport.xml"
    "$HERE/../tareas-ventana.sh" suspender
    comprobar
    ;;
comprobar) comprobar ;;
*) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# driver-masivo-cris.sh — Fase 5 CRIS — PROVISIONING CONTROLADO MASIVO
# (PREPARADO, NO EJECUTAR sin visto bueno y verificar precondiciones de la tarea
#  recompute-dgi-investigadores.xml)
#
# Provisiona al DSpace-CRIS (cris.upeu.edu.pe) la poblacion de investigadores y/o
# OrgUnits de investigacion, de forma SERIALIZADA, idempotente y con gate de heap.
# Espejo del driver acotado usado el 2026-06-18 para los 185 OrgUnit DGI.
#
# USO:
#   driver-masivo-cris.sh ORGUNIT  <admin_user> <admin_pass> <oids_file>
#     -> asigna AR-CRIS-OrgUnit (bdfe5f18-…) a cada OrgType del archivo (1 OID/linea),
#        en ORDEN JERARQUICO (centros antes que lineas) para que parentOrganization
#        resuelva. Proyecta orgUnit con metadata PeruCRIS (legalName/parent/tiposubunidad).
#   driver-masivo-cris.sh PERSON   <admin_user> <admin_pass> <oids_file>
#     -> recompute (PATCH ?options=reconcile no-op en description) de cada foco User.
#        AR-CRIS-Person (c4e8f1a2-…) gobierna quien se proyecta (gate RENACYT/research-center).
#
# IDEMPOTENTE: upsert en CRIS por organization.legalName (OrgUnit) / perucris.person.dni
# (Person). Reejecutable; mantiene /tmp/cris_masivo_done.txt (resume).
#
# CODIGOS HTTP:
#   204 / 240 (handled_error) / 250 (partial_error) = EXITO (dato en CRIS; shadow dead = ruido).
#   400 'sin attributes' = dato sucio del foco (givenName/dni faltantes) -> se reporta, no se reintenta.
#   Verificar exito REAL contra el CRIS (matches por DNI/legalName = 1), no por HTTP code.
#
# GATE HEAP: pausa si MemPerc>=85, aborta si >=95.
# ─────────────────────────────────────────────────────────────────────────────
set -u
MODE="${1:?MODE=ORGUNIT|PERSON}"
A_USER="${2:?admin_user}"; A_PASS="${3:?admin_pass}"; OIDS="${4:?oids_file}"
AR_ORGUNIT="bdfe5f18-99f1-437b-80e6-ccffb52215ad"
BASE="http://localhost:8080/midpoint/ws/rest"
DONE="/tmp/cris_masivo_done.txt"; touch "$DONE"
ok=0; skip=0; partial=0; dirty=0; fail=0; n=0
total=$(grep -c . "$OIDS")

heap_pct () { docker stats --no-stream --format '{{.MemPerc}}' midpoint_server | tr -d '%' | cut -d. -f1; }

while read OID; do
  [ -z "$OID" ] && continue
  n=$((n+1))
  grep -qx "$OID" "$DONE" && { skip=$((skip+1)); continue; }
  H=$(heap_pct)
  if [ "${H:-0}" -ge 95 ]; then echo "HEAP ${H}% >=95 -> ABORT en $n/$total"; exit 2; fi
  while [ "${H:-0}" -ge 85 ]; do echo "heap ${H}% >=85, pausa 30s..."; sleep 30; H=$(heap_pct); done

  if [ "$MODE" = "ORGUNIT" ]; then
    CODE=$(curl -s -u "$A_USER:$A_PASS" -X PATCH "$BASE/orgs/$OID" -H 'Content-Type: application/json' \
      -d "{\"objectModification\":{\"itemDelta\":[{\"modificationType\":\"add\",\"path\":\"assignment\",\"value\":{\"targetRef\":{\"oid\":\"$AR_ORGUNIT\",\"type\":\"RoleType\"}}}]}}" \
      -o /tmp/cris_resp.txt -w '%{http_code}')
  else
    CODE=$(curl -s -u "$A_USER:$A_PASS" -X PATCH "$BASE/users/$OID?options=reconcile" -H 'Content-Type: application/json' \
      -d "{\"objectModification\":{\"itemDelta\":[{\"modificationType\":\"replace\",\"path\":\"description\",\"value\":\"cris-masivo\"}]}}" \
      -o /tmp/cris_resp.txt -w '%{http_code}')
  fi

  case "$CODE" in
    204|240) echo "$OID" >> "$DONE"; ok=$((ok+1)) ;;
    250)     echo "$OID" >> "$DONE"; partial=$((partial+1)) ;;  # creado en CRIS, shadow dead
    400)
      if grep -q "without any attributes" /tmp/cris_resp.txt 2>/dev/null; then
        echo "  DIRTY $OID (foco sin atributos proyectables)"; dirty=$((dirty+1))
      else
        echo "  FAIL $OID -> 400"; fail=$((fail+1))
      fi ;;
    *) echo "  FAIL $OID -> $CODE"; fail=$((fail+1)) ;;
  esac
  [ $((n % 25)) -eq 0 ] && echo "  $n/$total ok=$ok partial=$partial dirty=$dirty fail=$fail skip=$skip heap=${H}%"
done < "$OIDS"
echo "DONE [$MODE]: ok=$ok partial=$partial dirty=$dirty fail=$fail skip=$skip / $total"
echo "VERIFICAR exito REAL en CRIS (matches por DNI/legalName = 1), no por HTTP code."

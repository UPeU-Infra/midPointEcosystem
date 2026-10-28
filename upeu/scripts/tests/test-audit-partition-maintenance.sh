#!/usr/bin/env bash
#
# test-audit-partition-maintenance.sh
# ------------------------------------------------------------------------------
# Prueba reproducible de upeu/scripts/audit-partition-maintenance.sh contra un
# PostgreSQL DESECHABLE (contenedor local), con el esquema de auditoria REAL de
# MidPoint descargado del tag correspondiente:
#
#   Escenario A (4.10.2): event/delta/ref; 4 meses viejos -> deben irse los 4
#                         (no solo el primero: regresion del fallo del 1-oct).
#   Escenario B (4.11.0): tras aplicar postgres-audit-upgrade.sql de 4.11.0
#                         (crea ma_audit_payload_* con FK a event). Con payload
#                         con datos, los meses viejos deben irse enteros.
#   Escenario C (guarda): una tabla ajena con FK a un event viejo -> ese mes NO
#                         se toca y el bucle se corta (fail-closed).
#   Escenario D (dry-run): no cambia nada y la sesion es de solo lectura.
#
# Opcional: --con-version-anterior ejecuta tambien la version de main
# (git show main:...) para DEMOSTRAR los dos fallos que corrige esta version:
#   - A: solo procesa el primer mes (el export se come el stdin del bucle);
#   - B: el DROP de event falla por la FK de payload.
#
# NO toca PROD ni el laboratorio: solo un contenedor local que se borra al final.
# El export a S3 se sustituye por un doble que LEE stdin a proposito (como hace
# el real con `docker run -i`) y deja constancia del mes en un fichero.
#
# Requisitos: docker, bash >= 4 (mapfile), curl. En macOS: brew install bash y
# ejecutar con /opt/homebrew/bin/bash.
#
# USO
#   bash upeu/scripts/tests/test-audit-partition-maintenance.sh [--con-version-anterior]
# ------------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../audit-partition-maintenance.sh"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
CT="mp-audit-test-$$"
PG_IMAGE="${PG_IMAGE:-postgres:16}"
WORK="$(mktemp -d)"
WITH_OLD=0
[[ "${1:-}" == "--con-version-anterior" ]] && WITH_OLD=1

cleanup() { docker rm -f "$CT" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

PASS=0; FAIL=0
ok()   { echo "  OK   $*"; PASS=$((PASS+1)); }
ko()   { echo "  FAIL $*"; FAIL=$((FAIL+1)); }
sql()  { docker exec -i "$CT" psql -U midpoint -d midpoint -tA -v ON_ERROR_STOP=1 "$@"; }
exists() { [[ "$(sql -c "select count(*) from pg_class where relname='$1' and relkind='r'")" == "1" ]]; }
ym()   { sql -c "select to_char(date_trunc('month', now()) - interval '$1 months','YYYYMM')"; }

for t in v4.10.2 v4.11.0; do
    for f in postgres-audit.sql postgres-audit-upgrade.sql; do
        curl -fsSL "https://raw.githubusercontent.com/Evolveum/midpoint/$t/config/sql/native/$f" -o "$WORK/$t-$f"
    done
done

# Doble del export: consume stdin (como `docker run -i` del real) y registra el mes.
cat > "$WORK/fake-export.sh" <<'EOF'
#!/usr/bin/env bash
cat > /dev/null
echo "$2" >> "$(dirname "$0")/exported.txt"
exit 0
EOF
chmod +x "$WORK/fake-export.sh"

start_db() {
    docker rm -f "$CT" >/dev/null 2>&1 || true
    docker run -d --name "$CT" -e POSTGRES_USER=midpoint -e POSTGRES_PASSWORD=x -e POSTGRES_DB=midpoint "$PG_IMAGE" >/dev/null
    until docker exec "$CT" pg_isready -U midpoint -d midpoint >/dev/null 2>&1; do sleep 1; done
    sleep 2
    sql -q < "$WORK/v4.10.2-postgres-audit.sql" >/dev/null
    # Meses: actual y 5 hacia atras (-6) + 3 futuros.
    sql -q -c "CALL audit_create_monthly_partitions(-6)" 2>/dev/null
    sql -q -c "CALL audit_create_monthly_partitions(3)" 2>/dev/null
    # Una fila por mes (event + delta + ref) en los 6 meses.
    for i in 0 1 2 3 4 5; do
        sql -q -c "with e as (insert into ma_audit_event(timestamp) values (date_trunc('month', now()) - interval '$i months' + interval '1 day') returning id, timestamp)
                   , d as (insert into ma_audit_delta(recordId, timestamp, checksum) select id, timestamp, 'c$i' from e returning 1)
                   insert into ma_audit_ref(recordId, timestamp, name) select id, timestamp, 'r' from e" >/dev/null
    done
}

upgrade_to_411() {
    sql -q < "$WORK/v4.11.0-postgres-audit-upgrade.sql" >/dev/null 2>&1
    for i in 0 1 2 3 4 5; do
        sql -q -c "insert into ma_audit_payload(recordId, timestamp, ordinal, name, content)
                   select id, timestamp, 0, 'p', 'x'::bytea from ma_audit_event
                   where timestamp = date_trunc('month', now()) - interval '$i months' + interval '1 day'" >/dev/null
    done
}

run() {  # run <script> [args]
    local s="$1"; shift
    rm -f "$WORK/exported.txt"
    PG_CONTAINER="$CT" EXPORT_SCRIPT="$WORK/fake-export.sh" LOG_FILE=/dev/null RETENTION_MONTHS=2 \
        "${BASH:-bash}" "$s" "$@" > "$WORK/out.txt" 2>&1 && echo 0 || echo $?
}

# Meses: M0 actual, M1, M2 (se conservan con retencion 2); M3, M4, M5 (se van).
OLDM=(); KEEPM=()

echo "== Escenario A: esquema 4.10.2 (sin payload)"
start_db
for i in 3 4 5; do OLDM+=("$(ym $i)"); done
for i in 0 1 2; do KEEPM+=("$(ym $i)"); done
rc=$(run "$SCRIPT")
[[ "$rc" == "0" ]] && ok "exit 0" || { ko "exit $rc"; cat "$WORK/out.txt"; }
[[ "$(sort "$WORK/exported.txt" 2>/dev/null | tr '\n' ' ')" == "$(printf '%s\n' "${OLDM[@]}" | sort | tr '\n' ' ')" ]] \
    && ok "exporto los ${#OLDM[@]} meses viejos (${OLDM[*]})" || ko "exportados: $(tr '\n' ' ' < "$WORK/exported.txt" 2>/dev/null)"
for m in "${OLDM[@]}"; do for c in event delta ref; do exists "ma_audit_${c}_$m" && ko "sigue ma_audit_${c}_$m" || ok "dropeada ma_audit_${c}_$m"; done; done
for m in "${KEEPM[@]}"; do exists "ma_audit_event_$m" && ok "conserva ma_audit_event_$m" || ko "borro ma_audit_event_$m"; done
grep -q "Reposicion OK" "$WORK/out.txt" && ok "reposicion del colchon" || ko "sin reposicion"

if [[ "$WITH_OLD" -eq 1 ]]; then
    echo "== Escenario A con la version de main (esperado: FALLA, solo el primer mes)"
    git -C "$REPO_ROOT" show main:upeu/scripts/audit-partition-maintenance.sh > "$WORK/old.sh"
    start_db
    run "$WORK/old.sh" >/dev/null
    n=$(wc -l < "$WORK/exported.txt" | tr -d ' ')
    echo "  (version anterior) meses exportados: $n de ${#OLDM[@]} -> $(tr '\n' ' ' < "$WORK/exported.txt")"
fi

echo "== Escenario D: --dry-run (sin cambios, sesion de solo lectura)"
start_db
before=$(sql -c "select count(*) from pg_class where relname ~ '^ma_audit_'")
rc=$(run "$SCRIPT" --dry-run)
after=$(sql -c "select count(*) from pg_class where relname ~ '^ma_audit_'")
[[ "$rc" == "0" ]] && ok "exit 0" || { ko "exit $rc"; cat "$WORK/out.txt"; }
[[ "$before" == "$after" ]] && ok "mismas tablas ($before)" || ko "cambio el numero de tablas: $before -> $after"
[[ ! -e "$WORK/exported.txt" ]] && ok "no llamo al export" || ko "llamo al export en dry-run"
grep -q "\[DRY-RUN\] mes" "$WORK/out.txt" && ok "lista los meses en dry-run" || ko "no lista meses"
ro=$(docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$CT" psql -U midpoint -d midpoint -tA -c "create table zz(x int)" 2>&1 || true)
grep -q "read-only" <<< "$ro" && ok "la sesion del dry-run rechaza escrituras" || ko "PGOPTIONS no fuerza solo lectura: $ro"

echo "== Escenario B: esquema 4.11.0 (con payload y FK a event)"
start_db
upgrade_to_411
exists "ma_audit_payload_${OLDM[0]}" && ok "existe ma_audit_payload_${OLDM[0]} tras el upgrade de 4.11" || ko "el upgrade no creo payload"
if [[ "$WITH_OLD" -eq 1 ]]; then
    git -C "$REPO_ROOT" show main:upeu/scripts/audit-partition-maintenance.sh > "$WORK/old.sh"
    rc=$(run "$WORK/old.sh")
    echo "  (version anterior) exit=$rc; error: $(grep -m1 -i 'error' "$WORK/out.txt" || echo ninguno)"
    start_db; upgrade_to_411
fi
rc=$(run "$SCRIPT")
[[ "$rc" == "0" ]] && ok "exit 0" || { ko "exit $rc"; cat "$WORK/out.txt"; }
for m in "${OLDM[@]}"; do for c in payload delta ref event; do exists "ma_audit_${c}_$m" && ko "sigue ma_audit_${c}_$m" || ok "dropeada ma_audit_${c}_$m"; done; done
for m in "${KEEPM[@]}"; do exists "ma_audit_payload_$m" && ok "conserva ma_audit_payload_$m" || ko "borro ma_audit_payload_$m"; done
fut=$(sql -c "select count(*) from pg_class where relname ~ '^ma_audit_payload_[0-9]{6}$'")
[[ "$fut" -ge 4 ]] && ok "payload futuras presentes tras la reposicion ($fut)" || ko "faltan payload futuras ($fut)"

echo "== Escenario C: guarda FK (tabla ajena referencia un event viejo)"
start_db
sql -q -c "create table zz_ajena(recordid bigint, ts timestamptz, foreign key (recordid, ts) references ma_audit_event_${OLDM[2]}(id, timestamp))"
rc=$(run "$SCRIPT")
grep -q "GUARD FK" "$WORK/out.txt" && ok "detecta la FK ajena" || ko "no la detecta"
exists "ma_audit_event_${OLDM[2]}" && ok "no toca el mes protegido ${OLDM[2]}" || ko "dropeo el mes protegido"

echo
echo "RESULTADO: $PASS OK, $FAIL FAIL"
[[ "$FAIL" -eq 0 ]]

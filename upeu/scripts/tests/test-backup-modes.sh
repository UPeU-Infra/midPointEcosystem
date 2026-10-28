#!/usr/bin/env bash
#
# test-backup-modes.sh
# ------------------------------------------------------------------------------
# Prueba de backup-midpoint-s3.sh SIN AWS y SIN PROD:
#   - --export-audit YYYYMM con el esquema de auditoria de 4.11.0 (incluye
#     ma_audit_payload_YYYYMM en el dump y en la verificacion del TOC) y con el de
#     4.10.2 (sin payload);
#   - --pre-upgrade ETIQUETA (MidPoint "parado"): BD sin datos de auditoria y
#     home leido de un volumen;
#   - que --pre-upgrade se NIEGA si hay un contenedor midpoint_server en marcha.
#
# Como: Postgres desechable con tablas m_* de juguete + esquema de auditoria real
# (descargado del tag); un doble de la CLI de AWS (imagen local "fake-aws") que
# guarda en $STAGE/.fakes3 lo que el real subiria a S3; y el script corriendo en
# un contenedor Linux (docker:cli + bash/coreutils/python3) con el socket de
# Docker, porque usa stat -c, numfmt y df -BG de GNU.
#
# USO: bash upeu/scripts/tests/test-backup-modes.sh
# ------------------------------------------------------------------------------
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$(cd "$HERE/.." && pwd)/backup-midpoint-s3.sh"
W="$(mktemp -d "${TMPDIR:-/tmp}/mp-bk-test.XXXXXX")"; W="$(cd "$W" && pwd -P)"
PGC="mp-bk-test-pg-$$"; VOL="mp-bk-test-home-$$"; FAKE_MP="mp-bk-test-mpserver-$$"
cleanup() { docker rm -f "$PGC" "$FAKE_MP" >/dev/null 2>&1 || true; docker volume rm -f "$VOL" >/dev/null 2>&1 || true; rm -rf "$W"; }
trap cleanup EXIT
PASS=0; FAIL=0
ok() { echo "  OK   $*"; PASS=$((PASS+1)); }
ko() { echo "  FAIL $*"; FAIL=$((FAIL+1)); }

# --- doble de la CLI de AWS ---------------------------------------------------
mkdir -p "$W/fakeaws"
cat > "$W/fakeaws/aws" <<'EOF'
#!/bin/sh
# Emula: s3 cp <file|-> s3://B/K ... ; s3api head-object --bucket B --key K ... ;
#        s3api get-object --bucket B --key K --range bytes=0-N OUT
ROOT=/stage/.fakes3
arg() { n="$1"; shift; while [ $# -gt 0 ]; do [ "$1" = "$n" ] && { echo "$2"; return; }; shift; done; }
case "$1 $2" in
  "s3 cp")
    src="$3"; dst="${4#s3://}"; mkdir -p "$ROOT/$(dirname "$dst")"
    if [ "$src" = "-" ]; then cat > "$ROOT/$dst"; else cp "$src" "$ROOT/$dst"; fi ;;
  "s3api head-object")
    b=$(arg --bucket "$@"); k=$(arg --key "$@"); wc -c < "$ROOT/$b/$k" | tr -d ' ' ;;
  "s3api get-object")
    b=$(arg --bucket "$@"); k=$(arg --key "$@"); r=$(arg --range "$@"); out=$(eval echo \${$#})
    n=${r#bytes=0-}; head -c $((n+1)) "$ROOT/$b/$k" > "$out"; echo '{}' ;;
  *) echo "fake-aws: no emulado: $*" >&2; exit 9 ;;
esac
EOF
chmod +x "$W/fakeaws/aws"
printf 'FROM alpine:3.20\nCOPY aws /usr/local/bin/aws\nENTRYPOINT ["/usr/local/bin/aws"]\n' > "$W/fakeaws/Dockerfile"
docker build -q -t mp-bk-test-fake-aws "$W/fakeaws" >/dev/null

# --- Postgres desechable --------------------------------------------------------
docker run -d --name "$PGC" -e POSTGRES_USER=midpoint -e POSTGRES_PASSWORD=x -e POSTGRES_DB=midpoint postgres:16 >/dev/null
until docker exec "$PGC" pg_isready -U midpoint -d midpoint >/dev/null 2>&1; do sleep 1; done; sleep 2
psqlc() { docker exec -i "$PGC" psql -U midpoint -d midpoint -q -v ON_ERROR_STOP=1 "$@"; }
for t in v4.10.2 v4.11.0; do
    curl -fsSL "https://raw.githubusercontent.com/Evolveum/midpoint/$t/config/sql/native/postgres-audit.sql" -o "$W/$t-audit.sql"
    curl -fsSL "https://raw.githubusercontent.com/Evolveum/midpoint/$t/config/sql/native/postgres-audit-upgrade.sql" -o "$W/$t-audit-up.sql"
done
psqlc < "$W/v4.10.2-audit.sql" >/dev/null 2>&1
psqlc -c "CALL audit_create_monthly_partitions(-6)" >/dev/null 2>&1
for tb in m_user m_shadow_abc m_resource m_role m_org m_system_configuration m_assignment m_simulation_result_processed_object; do
    psqlc -c "create table $tb(x int); insert into $tb values (1);"
done
M=$(docker exec "$PGC" psql -U midpoint -d midpoint -tA -c "select to_char(date_trunc('month', now()) - interval '4 months','YYYYMM')")
psqlc -c "insert into ma_audit_event(timestamp) values (date_trunc('month', now()) - interval '4 months' + interval '1 day')"

# --- home (volumen) y directorio del host -----------------------------------------
docker volume create "$VOL" >/dev/null
docker run --rm -v "$VOL:/v" --entrypoint sh postgres:16 -c 'echo k > /v/keystore.jceks; echo "<configuration/>" > /v/config.xml; mkdir /v/log; echo x > /v/log/a.log'
mkdir -p "$W/hostdir" "$W/stage" "$W/home"
echo "services: {}" > "$W/hostdir/docker-compose.yml"; echo "MP_VER=x" > "$W/hostdir/.env"
cat > "$W/backup.env" <<EOF
AWS_ACCESS_KEY_ID=fake
AWS_SECRET_ACCESS_KEY=fake
AWS_DEFAULT_REGION=us-east-2
IGA_BACKUP_BUCKET=fakebucket
EOF

run() {  # corre el script real en un contenedor Linux con el socket de Docker
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$W:$W" -v "$SCRIPT:/s/backup.sh:ro" \
        -e HOME="$W/home" -e CONF="$W/backup.env" -e PG_CONTAINER="$PGC" -e MP_CONTAINER="$FAKE_MP" \
        -e MP_HOST_DIR="$W/hostdir" -e AWS_IMAGE=mp-bk-test-fake-aws -e STAGE="$W/stage" -e LOG_FILE="$W/log.txt" \
        -e MP_HOME_VOLUME="$VOL" -e MP_IMAGE_FOR_TAR=postgres:16 \
        docker:cli sh -c 'apk add -q bash coreutils python3 >/dev/null 2>&1 && bash /s/backup.sh "$@"' _ "$@" \
        > "$W/out.txt" 2>&1 && echo 0 || echo $?
}
S3="$W/stage/.fakes3/fakebucket/midpoint"
# Siempre a variable: `toc | grep -q` con pipefail da falso negativo (SIGPIPE).
toc() { docker exec -i "$PGC" pg_restore -l < "$1"; }

echo "== --export-audit $M con esquema 4.10.2 (sin payload)"
rc=$(run --export-audit "$M"); [[ "$rc" == 0 ]] && ok "exit 0" || { ko "exit $rc"; tail -20 "$W/out.txt"; }
[[ -s "$S3/audit/ma_audit_$M.dump.sha256" ]] && ok ".sha256 escrito" || ko "sin .sha256"
T=$(toc "$S3/audit/ma_audit_$M.dump"); n=$(grep -c "TABLE DATA .* ma_audit_\(event\|delta\|ref\)_$M " <<< "$T" || true)
[[ "$n" == 3 ]] && ok "TOC con event, delta y ref" || ko "TOC: $n tablas"

echo "== --export-audit $M con esquema 4.11.0 (con payload)"
psqlc < "$W/v4.11.0-audit-up.sql" >/dev/null 2>&1
rm -rf "$S3/audit"
rc=$(run --export-audit "$M"); [[ "$rc" == 0 ]] && ok "exit 0" || { ko "exit $rc"; tail -20 "$W/out.txt"; }
T=$(toc "$S3/audit/ma_audit_$M.dump"); grep -q "TABLE DATA .* ma_audit_payload_$M " <<< "$T" && ok "TOC incluye ma_audit_payload_$M" || ko "payload no esta en el dump"
grep -q "Tablas a exportar: .*ma_audit_payload_$M" "$W/out.txt" && ok "log lista payload" || ko "log sin payload"

echo "== --pre-upgrade con MidPoint 'parado'"
rc=$(run --pre-upgrade test-f0); [[ "$rc" == 0 ]] && ok "exit 0" || { ko "exit $rc"; tail -20 "$W/out.txt"; }
db=$(ls "$S3/upgrade/test-f0/"midpoint-db-sin-auditoria-*.dump 2>/dev/null | head -1)
[[ -n "$db" && -s "$db.sha256" ]] && ok "dump BD + .sha256" || ko "falta dump o .sha256"
T=$(toc "$db"); grep -q "TABLE DATA .* m_user " <<< "$T" && ok "TOC con m_user" || ko "TOC sin m_user"
grep -q "TABLE DATA .* ma_audit_event_$M " <<< "$T" && ko "trae datos de auditoria (no deberia)" || ok "sin datos de auditoria"
hm=$(ls "$S3/upgrade/test-f0/"midpoint-home-*.tar.gz 2>/dev/null | head -1)
[[ -n "$hm" && -s "$hm.sha256" ]] && ok "tar del home + .sha256" || ko "falta tar del home"
inner=$(tar -tzf "$hm" | grep '^home-var\.'); lst=$(tar -xzOf "$hm" "$inner" | tar -t)
grep -qx './keystore.jceks' <<< "$lst" && ok "home con keystore.jceks" || ko "home sin keystore"
grep -q '^./log/' <<< "$lst" && ko "home incluye log/" || ok "home sin log/"

echo "== --pre-upgrade se niega con midpoint_server en marcha"
docker run -d --name "$FAKE_MP" postgres:16 sleep 300 >/dev/null 2>&1 || docker run -d --name "$FAKE_MP" --entrypoint sleep postgres:16 300 >/dev/null
rc=$(run --pre-upgrade test-f0b); [[ "$rc" != 0 ]] && ok "exit $rc (se niega)" || ko "no se nego"
grep -q "sigue en marcha" "$W/out.txt" && ok "mensaje claro" || ko "sin mensaje"

echo; echo "RESULTADO: $PASS OK, $FAIL FAIL"
[[ "$FAIL" -eq 0 ]]

#!/usr/bin/env bash
#
#  Correo institucional que FALTA en Oracle (MOISES.PERSONA_NATURAL.CORREO_INST)
#  para los matriculados de PREGRADO del semestre vigente, verificado contra Entra ID.
#
#    ./generar.sh                 semestre 283 (2026-2)
#    SEMESTRE=290 ./generar.sh    otro semestre
#
#  SOLO LECTURA en Oracle, MidPoint y Entra. Produce en ~/Downloads el Excel,
#  el UPDATE (sin COMMIT) y el ROLLBACK. El UPDATE lo ejecuta el equipo LAMB, nunca el IGA.
#  Requiere VPN corporativa y ~/.secrets/{upeu-infra,midpoint-upeu,oracle-lamb}.env
#
set -euo pipefail
cd "$(dirname "$0")"
SEMESTRE="${SEMESTRE:-283}"
W="${M365_WORK:-$HOME/.cache/upeu-correos-oracle}"; OUT="${OUT:-$HOME/Downloads}"
mkdir -p "$W"; chmod 700 "$W"
source ~/.secrets/midpoint-upeu.env; source ~/.secrets/oracle-lamb.env; source ~/.secrets/upeu-infra.env
export SSHPASS="$MIDPOINT_PROD_PASS"
JAR=/opt/midpoint/var/lib/ojdbc11-23.6.0.24.10.jar; DSN='jdbc:oracle:thin:@192.168.13.9:1521/UPEU'
ssh_mp() { sshpass -e ssh -o StrictHostKeyChecking=no -o ConnectTimeout=90 -o NumberOfPasswordPrompts=1 midpoint-prod "$@"; }
ora()   { ssh_mp "docker exec midpoint_server java -cp /tmp:$JAR OraQ '$DSN' '$ORACLE_USER' '$ORACLE_PASS' \"$1\""; }
# OraQ.class lo compila ../m365-clasificacion-cuentas-2026-08-17/lib/03-extraer-oracle.sh si falta
ssh_mp 'docker exec midpoint_server test -f /tmp/OraQ.class' || bash ../m365-clasificacion-cuentas-2026-08-17/lib/03-extraer-oracle.sh >/dev/null

echo "→ 1/5 tenant M365 (~7 min)"
python3 ../m365-clasificacion-cuentas-2026-08-17/lib/01-pull-entra.py \
  "$MIDPOINT_AZ_TENANT_ID" "$MIDPOINT_AZ_CLIENT_ID" "$MIDPOINT_AZ_CLIENT_SECRET" "$W/entra_hoy.json" | tail -1

echo "→ 2/5 matriculados del semestre $SEMESTRE (Oracle)"
# TODOS los niveles de cada persona: quien lleva Pregrado + Idiomas ES de pregrado (error del 13-oct: 922 mal clasificados)
ora "SELECT DISTINCT aac.ID_PERSONA, pna.CODIGO, pn.ID_TIPODOCUMENTO, pn.NUM_DOCUMENTO, p.NOMBRE, p.PATERNO, p.MATERNO, pn.CORREO_INST AS CORREO_INST_RAW, os.NOMBRE AS SEDE, ape.NOMBRE AS PROGRAMA, tne.NOMBRE AS NIVEL FROM DAVID.ACAD_ALUMNO_CONTRATO aac JOIN DAVID.ACAD_SEMESTRE_PROGRAMA asp ON asp.ID_SEMESTRE_PROGRAMA=aac.ID_SEMESTRE_PROGRAMA JOIN DAVID.ACAD_ALUMNO_CONTRATO_CURSO aacc ON aacc.ID_ALUMNO_CONTRATO=aac.ID_ALUMNO_CONTRATO JOIN DAVID.ACAD_PROGRAMA_ESTUDIO ape ON ape.ID_PROGRAMA_ESTUDIO=asp.ID_PROGRAMA_ESTUDIO LEFT JOIN DAVID.TIPO_NIVEL_ENSENANZA tne ON tne.ID_NIVEL_ENSENANZA=ape.ID_NIVEL_ENSENANZA LEFT JOIN ELISEO.ORG_SEDE_AREA osa ON osa.ID_SEDEAREA=ape.ID_SEDEAREA LEFT JOIN ELISEO.ORG_SEDE os ON os.ID_SEDE=osa.ID_SEDE JOIN MOISES.PERSONA p ON p.ID_PERSONA=aac.ID_PERSONA JOIN MOISES.PERSONA_NATURAL pn ON pn.ID_PERSONA=p.ID_PERSONA JOIN MOISES.PERSONA_NATURAL_ALUMNO pna ON pna.ID_PERSONA=p.ID_PERSONA WHERE asp.ID_SEMESTRE=$SEMESTRE" > "$W/ora_2026_2_v2.tsv"

echo "→ 3/5 CORREO_INST de todo Oracle y fichas con documento duplicado"
ora "SELECT ID_PERSONA, lower(trim(CORREO_INST)) CORREO_INST FROM MOISES.PERSONA_NATURAL WHERE CORREO_INST IS NOT NULL" > "$W/ora_correo_inst_all.tsv"
ora "SELECT pn.ID_PERSONA, pn.ID_TIPODOCUMENTO, pn.NUM_DOCUMENTO, lower(pn.CORREO_INST) CORREO_INST FROM MOISES.PERSONA_NATURAL pn WHERE (pn.ID_TIPODOCUMENTO, pn.NUM_DOCUMENTO) IN (SELECT ID_TIPODOCUMENTO, NUM_DOCUMENTO FROM MOISES.PERSONA_NATURAL WHERE NUM_DOCUMENTO IS NOT NULL GROUP BY ID_TIPODOCUMENTO, NUM_DOCUMENTO HAVING COUNT(*)>1)" > "$W/ora_doc_dup.tsv"

ora "SELECT UPPER(TRIM(NOMBRE)) N, UPPER(TRIM(PATERNO)) P, UPPER(TRIM(MATERNO)) M, COUNT(*) C FROM MOISES.PERSONA WHERE NOMBRE IS NOT NULL GROUP BY UPPER(TRIM(NOMBRE)), UPPER(TRIM(PATERNO)), UPPER(TRIM(MATERNO)) HAVING COUNT(*)>1" > "$W/ora_nombres_dup.tsv"

echo "→ 4/5 focos de MidPoint"
ssh_mp "docker exec midpoint-midpoint_data-1 psql -U midpoint midpoint -c \"COPY (SELECT u.nameorig, coalesce(u.ext->>'74','') AS codigo, regexp_replace(coalesce(u.ext->>'72',''),'^.*:','') AS dni, lower(coalesce(u.emailaddress,'')) AS email, coalesce(u.ext->>'219',u.ext->>'220','') AS campus, coalesce(u.ext->>'78','') AS aff, u.lifecyclestate FROM m_user u) TO STDOUT WITH CSV HEADER\"" > "$W/mp_hoy.csv"

for f in entra_hoy.json ora_2026_2_v2.tsv ora_correo_inst_all.tsv mp_hoy.csv; do
  [ "$(wc -c < "$W/$f")" -gt 100000 ] || { echo "✗ $f sospechosamente corto"; exit 1; }
done
echo "→ 5/5 Excel (lote 1, lote 2, revisión, pendientes) + UPDATE + ROLLBACK"
python3 lib/build_oracle_update.py "$W" "$OUT"

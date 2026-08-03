#!/usr/bin/env bash
# =============================================================================
# diff-repo-prod.sh — detecta drift entre el repo GitOps y MidPoint PROD
# M5.8 del plan docs/specs/gobierno-iga-fase14/01-plan.md
#
# POR QUÉ EXISTE
# El drift repo↔PROD es crónico en este proyecto: se detectó el 19-jul (roles
# Koha), el 20-jul (5 roles, no 2) y el 03-ago (6 roles RIMS/svc que vivían
# SOLO en PROD, uno de ellos definiendo control de acceso del gateway de IA).
# Siempre se descubrió por casualidad, investigando otra cosa. Esto lo convierte
# en una comprobación rutinaria.
#
# QUÉ COMPARA
# Por OID, no por nombre (CLAUDE.md: "OIDs estables. Filename puede cambiar;
# OID nunca"). Cubre los tipos que se versionan: role, resource, archetype,
# objectTemplate, org, service, task, functionLibrary, lookupTable, policy.
#
# QUÉ NO ES DRIFT (excluido a propósito)
#   - objetos built-in de MidPoint (OID 00000000-…)
#   - archive/ y datasets/ (material histórico y demo, no se despliega)
#   - tasks one-shot ya cerradas en PROD: son ejecuciones, no configuración
#     (se listan aparte como informativo, no cuentan para el exit code)
#
# USO
#   ./diff-repo-prod.sh              # informe humano; exit 1 si hay drift
#   ./diff-repo-prod.sh --quiet      # solo el resumen (para cron)
#
# Corre EN PROD (necesita el repo y el contenedor de Postgres).
# =============================================================================
set -uo pipefail

REPO="${REPO:-/home/juansanchez/midPointEcosystem}"
PGC="${PGC:-midpoint-midpoint_data-1}"
QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

say() { [[ $QUIET -eq 0 ]] && echo -e "$@"; return 0; }

# --- 1. OIDs presentes en el repo -------------------------------------------
# El oid del elemento RAÍZ puede estar varias líneas por debajo del tag (los XML
# de este repo abren con bloques largos de xmlns). Se resuelve leyendo el archivo
# entero y tomando el primer oid= que aparece TRAS el tag raíz — nunca los oid de
# targetRef/resourceRef, que son referencias a otros objetos.
python3 - "$REPO" <<'PY' > "$TMP/repo.txt"
import re,sys,glob,os
root=sys.argv[1]
TAGS=r'(role|resource|archetype|objectTemplate|org|service|task|functionLibrary|lookupTable|policy|genericObject)'
out=set()
for base in ('upeu','canonical'):
    for f in glob.glob(os.path.join(root,base,'**','*.xml'),recursive=True):
        try: x=open(f,encoding='utf-8',errors='replace').read()
        except Exception: continue
        m=re.search(r'<'+TAGS+r'[\s>]',x)
        if not m: continue
        o=re.search(r'oid="([0-9a-f-]{36})"',x[m.start():])
        if o and not o.group(1).startswith('00000000-'):
            out.add(o.group(1))
for o in sorted(out): print(o)
PY
sort -u "$TMP/repo.txt" -o "$TMP/repo.txt"

# --- 2. OIDs desplegados en PROD --------------------------------------------
# Se excluyen los ServiceType con archetype "Position": son las ~738 posiciones
# sincronizadas desde LAMB-Oracle-Posiciones — DATOS, no configuración. Solo 13
# están versionadas a propósito (upeu/services/positions/). Incluirlas ahogaría
# el informe en ruido y volvería inútil la comprobación.
docker exec "$PGC" psql -U midpoint -d midpoint -At -F'|' -c "
  SELECT o.oid, o.objecttype::text, o.nameorig
  FROM m_object o
  WHERE o.objecttype IN ('ROLE','RESOURCE','ARCHETYPE','OBJECT_TEMPLATE','SERVICE',
                         'FUNCTION_LIBRARY','LOOKUP_TABLE','POLICY')
    AND o.oid::text NOT LIKE '00000000-%'
    AND NOT EXISTS (
      SELECT 1 FROM m_ref_archetype ra JOIN m_archetype a ON a.oid=ra.targetoid
      WHERE ra.ownerOid=o.oid AND a.nameorig IN ('Position'))
  ORDER BY 2,3;" > "$TMP/prod_full.txt" 2>/dev/null

cut -d'|' -f1 "$TMP/prod_full.txt" | sort -u > "$TMP/prod.txt"

# --- 2b. Nombres presentes en el repo (respaldo del cotejo) ------------------
# No todos los XML versionados declaran <oid> en el elemento raíz: p. ej. los 6
# R-Affiliation-* se desplegaron sin OID y MidPoint les asignó uno. Comparar solo
# por OID los marcaría como "solo en PROD" siendo falso. Se cotejan por nombre.
grep -rhoE '<name>[^<]+</name>' "$REPO/upeu" "$REPO/canonical" 2>/dev/null \
  | sed -E 's#</?name>##g' | LC_ALL=C sort -u > "$TMP/repo_names.txt"

# --- 3. Diferencias ----------------------------------------------------------
comm -23 "$TMP/prod.txt" "$TMP/repo.txt" > "$TMP/solo_prod_oid.txt"
comm -13 "$TMP/prod.txt" "$TMP/repo.txt" > "$TMP/solo_repo.txt"

# Del lado PROD, descartar los que sí están en el repo por nombre (sin OID
# declarado) y los sample objects que trae MidPoint de fábrica con OID propio.
: > "$TMP/solo_prod.txt"
: > "$TMP/sin_oid.txt"
DEMO='^(Project|Team|Location|Organization|Organizational unit|Organization unit|Top-level organization)$'
while read -r oid; do
  nm=$(grep "^$oid|" "$TMP/prod_full.txt" | cut -d'|' -f3)
  [[ "$nm" =~ $DEMO ]] && continue                       # sample object de MidPoint
  if LC_ALL=C grep -qxF "$nm" "$TMP/repo_names.txt"; then
    echo "$oid|$nm" >> "$TMP/sin_oid.txt"                # está versionado, sin OID
  else
    echo "$oid" >> "$TMP/solo_prod.txt"                  # drift real
  fi
done < "$TMP/solo_prod_oid.txt"

N_PROD=$(wc -l < "$TMP/solo_prod.txt" | tr -d ' ')
N_REPO=$(wc -l < "$TMP/solo_repo.txt" | tr -d ' ')

say "=============================================================="
say " DIFF repo ↔ PROD — $(date '+%Y-%m-%d %H:%M')"
say " repo: $(wc -l < "$TMP/repo.txt" | tr -d ' ') OIDs · PROD: $(wc -l < "$TMP/prod.txt" | tr -d ' ') OIDs"
say "=============================================================="

if [[ "$N_PROD" -gt 0 ]]; then
  say "\n🔴 EN PROD Y NO EN EL REPO ($N_PROD) — desplegado sin versionar:"
  while read -r oid; do
    say "   $(grep "^$oid|" "$TMP/prod_full.txt" | awk -F'|' '{printf "%-18s %s", $2, $3}')  [$oid]"
  done < "$TMP/solo_prod.txt"
fi

if [[ "$N_REPO" -gt 0 ]]; then
  # Se listan solo los que NO son tasks/orgs/positions: esos son ejecuciones y
  # datos sincronizados, cuyo OID legítimamente no coincide o ya no existe.
  : > "$TMP/solo_repo_rel.txt"
  while read -r oid; do
    f=$(grep -rl "$oid" "$REPO/upeu" "$REPO/canonical" --include='*.xml' 2>/dev/null | head -1)
    case "${f#$REPO/}" in
      upeu/tasks/*|upeu/orgs/*|upeu/services/positions/*) continue ;;
    esac
    echo "${f#$REPO/}|$oid" >> "$TMP/solo_repo_rel.txt"
  done < "$TMP/solo_repo.txt"
  N_REPO=$(wc -l < "$TMP/solo_repo_rel.txt" | tr -d ' ')
  if [[ "$N_REPO" -gt 0 ]]; then
    say "\n🟡 EN EL REPO Y NO EN PROD ($N_REPO) — versionado sin desplegar, o borrado en PROD:"
    while IFS='|' read -r f oid; do say "   $f  [$oid]"; done < "$TMP/solo_repo_rel.txt"
  fi
fi

N_SINOID=$(wc -l < "$TMP/sin_oid.txt" | tr -d ' ')
if [[ "$N_SINOID" -gt 0 ]]; then
  say "\nℹ️  VERSIONADOS PERO SIN <oid> EN EL REPO ($N_SINOID) — no es drift, pero"
  say "    rompe la trazabilidad OID↔archivo (CLAUDE.md: «OIDs estables»):"
  while IFS='|' read -r oid nm; do say "   $nm  [$oid]"; done < "$TMP/sin_oid.txt"
fi

if [[ "$N_PROD" -eq 0 && "$N_REPO" -eq 0 ]]; then
  say "\n✅ Sin drift."
  echo "DIFF-REPO-PROD OK: 0 drift ($(date '+%Y-%m-%d %H:%M'))"
  exit 0
fi

echo "DIFF-REPO-PROD DRIFT: $N_PROD solo-PROD, $N_REPO solo-repo ($(date '+%Y-%m-%d %H:%M'))"
exit 1

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
# Toma el oid="..." del elemento raíz de cada XML versionado.
grep -rhoE '^\s*<(role|resource|archetype|objectTemplate|org|service|task|functionLibrary|lookupTable|policy)[^>]*oid="[0-9a-f-]{36}"' \
  "$REPO/upeu" "$REPO/canonical" 2>/dev/null \
  | grep -oE 'oid="[0-9a-f-]{36}"' | cut -d'"' -f2 \
  | grep -v '^00000000-' | sort -u > "$TMP/repo.txt"

# Algunos XML declaran el oid en una línea posterior al tag raíz: segunda pasada
# por archivo, tomando el primer oid que aparezca.
find "$REPO/upeu" "$REPO/canonical" -name '*.xml' 2>/dev/null | while read -r f; do
  head -25 "$f" | grep -oE 'oid="[0-9a-f-]{36}"' | head -1 | cut -d'"' -f2
done | grep -v '^00000000-' | sort -u >> "$TMP/repo.txt"
sort -u "$TMP/repo.txt" -o "$TMP/repo.txt"

# --- 2. OIDs desplegados en PROD --------------------------------------------
docker exec "$PGC" psql -U midpoint -d midpoint -At -F'|' -c "
  SELECT o.oid, o.objecttype::text, o.nameorig
  FROM m_object o
  WHERE o.objecttype IN ('ROLE','RESOURCE','ARCHETYPE','OBJECT_TEMPLATE','SERVICE',
                         'FUNCTION_LIBRARY','LOOKUP_TABLE','POLICY')
    AND o.oid::text NOT LIKE '00000000-%'
  ORDER BY 2,3;" > "$TMP/prod_full.txt" 2>/dev/null

cut -d'|' -f1 "$TMP/prod_full.txt" | sort -u > "$TMP/prod.txt"

# --- 3. Diferencias ----------------------------------------------------------
comm -23 "$TMP/prod.txt" "$TMP/repo.txt" > "$TMP/solo_prod.txt"
comm -13 "$TMP/prod.txt" "$TMP/repo.txt" > "$TMP/solo_repo.txt"

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
  say "\n🟡 EN EL REPO Y NO EN PROD ($N_REPO) — versionado sin desplegar, o borrado en PROD:"
  while read -r oid; do
    f=$(grep -rl "$oid" "$REPO/upeu" "$REPO/canonical" --include='*.xml' 2>/dev/null | head -1)
    say "   ${f#$REPO/}  [$oid]"
  done < "$TMP/solo_repo.txt"
fi

if [[ "$N_PROD" -eq 0 && "$N_REPO" -eq 0 ]]; then
  say "\n✅ Sin drift."
  echo "DIFF-REPO-PROD OK: 0 drift ($(date '+%Y-%m-%d %H:%M'))"
  exit 0
fi

echo "DIFF-REPO-PROD DRIFT: $N_PROD solo-PROD, $N_REPO solo-repo ($(date '+%Y-%m-%d %H:%M'))"
exit 1

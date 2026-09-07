#!/usr/bin/env bash
#
#  Snapshot del directorio Entra ID de UPeU + comparación con el anterior.
#
#      ./snapshot-entra.sh
#
#  Solo lectura. Guarda ~43 MB en ~/backups/entra-snapshots/ y, si ya había un
#  snapshot previo, muestra automáticamente qué cambió desde entonces.
#  Tarda ~7 min (75.900 cuentas vía Microsoft Graph, paginado).
#
set -euo pipefail
DIR="${ENTRA_SNAP_DIR:-$HOME/backups/entra-snapshots}"
HOY=$(date +%Y-%m-%d)
DEST="$DIR/entra-snapshot-$HOY.json"
AQUI="$(cd "$(dirname "$0")" && pwd)"
PULL="$AQUI/../m365-clasificacion-cuentas-2026-08-17/lib/01-pull-entra.py"

[ -f ~/.secrets/upeu-infra.env ] || { echo "✗ falta ~/.secrets/upeu-infra.env"; exit 1; }
[ -f "$PULL" ] || { echo "✗ no encuentro el extractor: $PULL"; exit 1; }
mkdir -p "$DIR"; chmod 700 "$DIR"

# el snapshot anterior, para comparar al final
PREV=$(ls -1 "$DIR"/entra-snapshot-*.json 2>/dev/null | grep -v "$HOY" | tail -1 || true)

if [ -f "$DEST" ]; then
  echo "Ya existe el snapshot de hoy: $DEST"
  echo "Bórralo si quieres rehacerlo."
else
  echo "→ leyendo el directorio (~7 min)…"
  source ~/.secrets/upeu-infra.env
  python3 "$PULL" "$MIDPOINT_AZ_TENANT_ID" "$MIDPOINT_AZ_CLIENT_ID" \
      "$MIDPOINT_AZ_CLIENT_SECRET" "$DEST"
  chmod 600 "$DEST"
fi

# verificación de integridad: un snapshot truncado no sirve de nada
python3 - "$DEST" <<'EOF'
import json,sys
u=json.load(open(sys.argv[1],encoding='utf-8'))
ids={x.get("id") for x in u if x.get("id")}
assert len(u)>50000, f"solo {len(u)} registros: el volcado parece truncado"
assert len(ids)==len(u), "hay identificadores duplicados o vacíos"
print(f"✓ integridad correcta: {len(u):,} cuentas, {len(ids):,} ids únicos".replace(",","."))
EOF

if [ -n "$PREV" ]; then
  echo
  echo "════ cambios desde $(basename "$PREV") ════"
  python3 "$AQUI/comparar-snapshots.py" "$PREV" "$DEST" --csv "$DIR/cambios-$HOY.csv"
else
  echo "(no hay snapshot anterior con el que comparar)"
fi
echo
echo "Snapshots guardados en $DIR"
ls -1t "$DIR"/entra-snapshot-*.json | head -5 | sed 's|.*/|   |'

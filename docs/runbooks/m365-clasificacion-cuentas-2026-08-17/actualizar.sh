#!/usr/bin/env bash
#
#  Estudio de cuentas M365 de UPeU — regeneración completa con datos frescos.
#
#    ./actualizar.sh              todo (~40 min: 8 de descarga + 30 de Excel)
#    ./actualizar.sh --rapido     reutiliza las descargas previas si existen
#    ./actualizar.sh --solo-informe   rehace solo los entregables (~30 min, sin red)
#
#  Requiere: VPN corporativa levantada (192.168.15.166 debe responder) y los
#  secretos en ~/.secrets/{upeu-infra,midpoint-upeu,oracle-lamb}.env
#
#  TODO es de solo lectura: no escribe en M365, MidPoint, Entra ni Oracle.
#
set -euo pipefail
cd "$(dirname "$0")"

export M365_WORK="${M365_WORK:-$HOME/.cache/upeu-m365}"
export M365_OUT="${M365_OUT:-$HOME/Downloads}"
mkdir -p "$M365_WORK" "$M365_OUT"

MODO="${1:-}"
t0=$(date +%s)
paso() { echo; echo "═══ $* ═══"; }
fresco() { [ -s "$M365_WORK/$1" ] && [ "$MODO" = "--rapido" ]; }

if [ "$MODO" != "--solo-informe" ]; then
  paso "0/6 · comprobaciones previas"
  ping -c1 -W 3000 192.168.15.166 >/dev/null 2>&1 \
    || { echo "✗ No se alcanza MidPoint PROD (192.168.15.166). ¿VPN levantada?"; exit 1; }
  for s in upeu-infra midpoint-upeu oracle-lamb; do
    [ -f "$HOME/.secrets/$s.env" ] || { echo "✗ Falta ~/.secrets/$s.env"; exit 1; }
  done
  python3 -c "import openpyxl" 2>/dev/null || { echo "✗ Falta openpyxl: pip3 install openpyxl"; exit 1; }
  echo "✓ VPN, secretos y dependencias correctos"
  echo "  trabajo: $M365_WORK"
  echo "  salida:  $M365_OUT"

  paso "1/6 · tenant M365 completo (Microsoft Graph, ~8 min)"
  if fresco entra_users2.json; then echo "  (reutilizando descarga previa)"; else
    source ~/.secrets/upeu-infra.env
    python3 lib/01-pull-entra.py "$MIDPOINT_AZ_TENANT_ID" "$MIDPOINT_AZ_CLIENT_ID" \
        "$MIDPOINT_AZ_CLIENT_SECRET" "$M365_WORK/entra_users2.json"
  fi

  paso "2/6 · focos de identidad y catálogo de unidades (MidPoint PROD)"
  if fresco mp_full.csv; then echo "  (reutilizando extracción previa)"; else bash lib/02-extraer-midpoint.sh; fi

  paso "3/6 · MDM de personas (Oracle LAMB)"
  if fresco ora_nombres.tsv; then echo "  (reutilizando extracción previa)"; else bash lib/03-extraer-oracle.sh; fi
fi

paso "4/6 · clasificación por cascada de procedencia"
python3 lib/04-clasificar.py

paso "5/6 · entregables 1 y 2 (Excel — ~25 min, son 75.000 filas cada uno)"
python3 lib/05-entregables.py

paso "6/6 · entregable 3 (informe HTML)"
python3 lib/06-informe.py

echo
echo "═══ listo en $(( ($(date +%s)-t0)/60 )) min ═══"
ls -lh "$M365_OUT"/Analisis_*.xlsx "$M365_OUT"/Informe_Analisis_*.html 2>/dev/null | tail -3
echo
echo "Los datos intermedios quedan en $M365_WORK (borrables; se regeneran solos)."

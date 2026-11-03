#!/bin/bash
# ESCRITURA REAL en PROD (template 855caaca). Paso 7: borra 9 mappings archived desde el 28-oct
# (5772 leaver, v1 5831/5833/5835/5836, canario v2 5840..5843). Están archived ⇒ no hacen nada: el borrado
# no cambia el cálculo de nadie. Solo PATCH. Lee, comprueba, aplica, vuelve a leer y comprueba.
# Vuelta atrás: ./paso7.sh --rollback  (re-añade los 9 tal cual estaban, archived).
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p out
x() { awk '/=== B64/{getline; print}' "$1" | base64 -d > "$2"; }
if [ "${1:-}" = --rollback ]; then
  VESP=$(( $(grep -o 'version="[0-9]*"' out/tpl-despues.xml | head -1 | tr -dc 0-9) - 1 ))
  cat > out/rb.body <<'B'
mp PATCH 'objectTemplates/855caaca-68c4-4f7f-8ff8-b4e35dd7d390' application/xml "$F/rollback-71-template-restaurar.xml" | tail -c 400
mp GET 'objectTemplates/855caaca-68c4-4f7f-8ff8-b4e35dd7d390?options=raw' > $F/t.xml; tail -1 $F/t.xml
echo '=== B64'; head -n -2 $F/t.xml | base64 -w0; echo
B
  ./una-sesion.sh out/rb.body rollback-71-template-restaurar.xml > out/rb.out 2>&1; grep -v '^[A-Za-z0-9+/=]\{200,\}$' out/rb.out | tail -5
  x out/rb.out out/tpl-rollback.xml; ./comprobar.py out/tpl-rollback.xml antes $((VESP+2)); exit
fi
h=$((10#$(date -u +%H)*100 + 10#$(date -u +%M)))
[ -n "${FUERA_VENTANA:-}" ] || [ $h -ge 1610 ] || [ $h -lt 700 ] || { echo "PARO: fuera de la ventana 16:10–07:00 UTC (ahora $(date -u +%H:%M))"; exit 1; }
echo "== 1/3 lectura"
./una-sesion.sh leer.body > out/leer.out 2>&1; grep -E '^(recons|HTTP|[A-Z][a-z]{2} )' out/leer.out
grep -q '^recons-corriendo|0$' out/leer.out || { echo "PARO: hay una recon corriendo"; exit 1; }
x out/leer.out out/tpl-antes.xml
VESP=$(grep -o 'version="[0-9]*"' out/tpl-antes.xml | head -1 | tr -dc 0-9); echo "template v$VESP"
./comprobar.py out/tpl-antes.xml antes $VESP || { echo "PARO: el template no está como se esperaba"; exit 1; }
(cd out && python3 ../gen_paso7.py tpl-antes.xml) || { echo "PARO: no se pudo regenerar"; exit 1; }
cmp -s out/patch-71-template-limpieza.json patch-71-template-limpieza.json || { echo "PARO: el parche regenerado difiere"; exit 1; }
cp out/rollback-71-template-restaurar.xml rollback-71-template-restaurar.xml   # reversión = estado real de hoy
echo "== 2/3 aplicar (Enter para seguir, Ctrl-C para abortar)"; read -r
sed "1i\\
VESP=$VESP" aplicar.body > out/aplicar.body
./una-sesion.sh out/aplicar.body patch-71-template-limpieza.json > out/aplicar.out 2>&1
grep -v '^[A-Za-z0-9+/=]\{200,\}$' out/aplicar.out | tail -6
grep -q PARO out/aplicar.out && exit 1
echo "== 3/3 comprobar"
x out/aplicar.out out/tpl-despues.xml
./comprobar.py out/tpl-despues.xml despues $((VESP+1)) && echo "OK: paso 7 aplicado. $(date -u)"

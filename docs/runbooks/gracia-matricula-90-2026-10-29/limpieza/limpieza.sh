#!/bin/bash
# ESCRITURA REAL en PROD. Limpieza de la gracia de matrícula: borra lo que el despliegue global del 30-oct dejó
# archived — template 5844 (R1v2), 5852 (R1v3 canario), 5853 (T1 canario); e22 inbound 3327 (217 sin gracia).
# Están archived ⇒ no calculan nada. Solo PATCH. Lee, comprueba, aplica, vuelve a leer y comprueba.
# ⚠️ Tras esto rollback-20/21 ya no sirven solos: antes hay que correr `limpieza.sh --rollback` (re-añade los 4 archived).
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p out
x() { awk -v k="=== $2" '$0==k{getline; print}' "$1" | base64 -d > "$3"; }
quieto() { grep -v '^[A-Za-z0-9+/=]\{200,\}$' "$1" | tail -"$2"; }
if [ "${1:-}" = --rollback ]; then
  v() { grep -o 'version="[0-9]*"' "$1" | head -1 | tr -dc 0-9; }
  VT=$(v out/tpl-despues.xml); VR=$(v out/e22-despues.xml)
  cat > out/rb.body <<'B'
T='objectTemplates/855caaca-68c4-4f7f-8ff8-b4e35dd7d390'; R='resources/6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22'
mp PATCH "$T" application/xml "$F/rollback-L1-template-restaurar.xml" | tail -c 400
mp PATCH "$R" application/xml "$F/rollback-L2-e22-restaurar.xml" | tail -c 400
mp GET "$T?options=raw" > $F/t.xml; mp GET "$R?options=raw" > $F/r.xml
echo '=== TPL'; head -n -2 $F/t.xml | base64 -w0; echo
echo '=== E22'; head -n -2 $F/r.xml | base64 -w0; echo
B
  ./una-sesion.sh out/rb.body rollback-L1-template-restaurar.xml rollback-L2-e22-restaurar.xml > out/rb.out 2>&1; quieto out/rb.out 6
  x out/rb.out TPL out/tpl-rb.xml; x out/rb.out E22 out/e22-rb.xml
  ./comprobar.py out/tpl-rb.xml out/e22-rb.xml antes $((VT+1)) $((VR+1)); exit
fi
h=$((10#$(date -u +%H)*100 + 10#$(date -u +%M)))
[ -n "${FUERA_VENTANA:-}" ] || [ $h -ge 1610 ] || [ $h -lt 700 ] || { echo "PARO: fuera de la ventana 16:10–07:00 UTC (ahora $(date -u +%H:%M))"; exit 1; }
echo "== 1/3 lectura"
./una-sesion.sh leer.body > out/leer.out 2>&1; grep -E '^(recons|HTTP)' out/leer.out
grep -q '^recons-corriendo|0$' out/leer.out || { echo "PARO: hay una recon corriendo"; exit 1; }
x out/leer.out TPL out/tpl-antes.xml; x out/leer.out E22 out/e22-antes.xml
v() { grep -o 'version="[0-9]*"' "$1" | head -1 | tr -dc 0-9; }
VT=$(v out/tpl-antes.xml); VR=$(v out/e22-antes.xml); echo "template v$VT (v142 si ya se hizo el paso 7 de activacion-vinculo-vivo), e22 v$VR"
./comprobar.py out/tpl-antes.xml out/e22-antes.xml antes $VT $VR || { echo "PARO: no está como se esperaba"; exit 1; }
(cd out && python3 ../gen_limpieza.py tpl-antes.xml e22-antes.xml) || { echo "PARO: no se pudo regenerar"; exit 1; }
for f in patch-L1-template-limpieza.json patch-L2-e22-limpieza.json; do
  cmp -s out/$f $f || { echo "PARO: $f regenerado difiere"; exit 1; }; done
cp out/rollback-L1-template-restaurar.xml out/rollback-L2-e22-restaurar.xml .   # reversión = estado real de hoy
echo "== 2/3 aplicar (Enter para seguir, Ctrl-C para abortar)"; read -r
sed "1i\\
VT=$VT; VR=$VR" aplicar.body > out/aplicar.body
./una-sesion.sh out/aplicar.body patch-L1-template-limpieza.json patch-L2-e22-limpieza.json > out/aplicar.out 2>&1
quieto out/aplicar.out 10
grep -q PARO out/aplicar.out && exit 1
echo "== 3/3 comprobar"
x out/aplicar.out TPL out/tpl-despues.xml; x out/aplicar.out E22 out/e22-despues.xml
./comprobar.py out/tpl-despues.xml out/e22-despues.xml despues $((VT+1)) $((VR+1)) && echo "OK: limpieza de la gracia aplicada. $(date -u)"

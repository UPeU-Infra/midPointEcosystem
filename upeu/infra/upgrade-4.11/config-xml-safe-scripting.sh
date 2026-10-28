#!/usr/bin/env bash
#
# config-xml-safe-scripting.sh
# ------------------------------------------------------------------------------
# Deja escrito en el config.xml del volumen de MidPoint:
#
#     <expressions>
#         <safeScriptingLanguagesOnly>false</safeScriptingLanguagesOnly>
#     </expressions>
#
# POR QUE: en 4.11.0 la clave vale false si falta (ExpressionsConfigurationSectionImpl,
# configuration.getBoolean(..., false)), y el config.xml del volumen se conserva
# (init-native solo lo copia si NO existe). Pero si alguien recrea el volumen, el
# config.xml nuevo de 4.11 trae `true` y apaga Groovy: las 433 expresiones de UPeU
# dejan de evaluarse. Escribirlo explicitamente blinda ese caso (riesgo R8).
# NOTA: en 4.10.x la clave no existe; aplicar en la ventana F3 (no en F2) salvo
# que el ensayo F1 demuestre que 4.10.5 la ignora sin quejarse.
#
# QUE HACE
#   --check   (por defecto) solo lectura: dice si la clave esta y con que valor.
#   --apply   si falta, la inserta antes de </midpoint>; deja copia
#             config.xml.bak-pre-4.11-<ts> en el volumen; valida el XML resultante
#             (python3 del host) ANTES de escribirlo. Idempotente: si ya esta a
#             false no toca nada; si esta a true, ABORTA (decision humana).
#
# Corre en el HOST, con MidPoint PARADO para --apply. El config.xml contiene
# contrasenas: la copia temporal va a un mktemp 0600 y se borra al salir.
#
# USO
#   MP_HOME_VOLUME=midpoint_midpoint_home ./config-xml-safe-scripting.sh --check
#   MP_HOME_VOLUME=midpoint_midpoint_home ./config-xml-safe-scripting.sh --apply
# ------------------------------------------------------------------------------
set -euo pipefail

VOL="${MP_HOME_VOLUME:-midpoint_midpoint_home}"
IMG="${HELPER_IMAGE:-postgres:16-bullseye}"     # imagen ya presente en el host
MP_CONTAINER="${MP_CONTAINER:-midpoint_server}"
MODE="${1:---check}"

umask 077
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

vol_cat()   { docker run --rm -v "$VOL:/v:ro" --entrypoint cat "$IMG" /v/config.xml; }

vol_cat > "$TMP/config.xml"
[[ -s "$TMP/config.xml" ]] || { echo "ERROR: config.xml vacio o inexistente en el volumen $VOL" >&2; exit 1; }

STATE=$(python3 - "$TMP/config.xml" <<'PY'
import sys, xml.etree.ElementTree as ET
r = ET.parse(sys.argv[1]).getroot()
e = r.find('./midpoint/expressions/safeScriptingLanguagesOnly')
print('ausente' if e is None else (e.text or '').strip())
PY
)
echo "safeScriptingLanguagesOnly en $VOL/config.xml: $STATE"

case "$MODE" in
    --check) exit 0 ;;
    --apply) ;;
    *) echo "Uso: $0 [--check|--apply]" >&2; exit 2 ;;
esac

if [[ "$STATE" == "false" ]]; then
    echo "Ya esta a false. Nada que hacer."; exit 0
elif [[ "$STATE" != "ausente" ]]; then
    echo "ABORTO: la clave existe con valor '$STATE'. Revisar a mano (no se sobrescribe)." >&2; exit 3
fi

if [[ -n "$(docker ps --filter "name=^/${MP_CONTAINER}$" --format '{{.Names}}')" ]]; then
    echo "ABORTO: $MP_CONTAINER esta en marcha. Pararlo antes de --apply." >&2; exit 4
fi

python3 - "$TMP/config.xml" "$TMP/config.new.xml" <<'PY'
import sys, xml.etree.ElementTree as ET
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
block = ("        <expressions>\n"
         "            <!-- UPeU 2026: Groovy sigue habilitado hasta migrar a MEL (proyecto F5). -->\n"
         "            <safeScriptingLanguagesOnly>false</safeScriptingLanguagesOnly>\n"
         "        </expressions>\n"
         "    </midpoint>")
assert s.count('</midpoint>') == 1, 'se esperaba exactamente un </midpoint>'
s = s.replace('    </midpoint>', block, 1) if '    </midpoint>' in s else s.replace('</midpoint>', block.strip(), 1)
open(dst, 'w', encoding='utf-8').write(s)
r = ET.parse(dst).getroot()   # valida el XML
assert (r.find('./midpoint/expressions/safeScriptingLanguagesOnly').text or '').strip() == 'false'
print('XML nuevo valido')
PY

TS=$(date +%Y%m%d-%H%M%S)
# Copia de seguridad y escritura atomica dentro del volumen (como root; el chown
# de F3 la deja luego en 1000:1000).
docker run --rm -i -v "$VOL:/v" --user 0 --entrypoint sh "$IMG" -c \
    "cp -p /v/config.xml /v/config.xml.bak-pre-4.11-$TS && cat > /v/config.xml.new && chmod --reference=/v/config.xml /v/config.xml.new && chown --reference=/v/config.xml /v/config.xml.new && mv /v/config.xml.new /v/config.xml" \
    < "$TMP/config.new.xml"

vol_cat > "$TMP/check.xml"
cmp -s "$TMP/check.xml" "$TMP/config.new.xml" && echo "OK: config.xml actualizado (copia: config.xml.bak-pre-4.11-$TS)" \
    || { echo "ERROR: el contenido escrito no coincide" >&2; exit 5; }

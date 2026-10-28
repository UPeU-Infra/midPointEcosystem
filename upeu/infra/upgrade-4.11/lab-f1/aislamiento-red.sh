#!/usr/bin/env bash
#
# aislamiento-red.sh — PRIMERA capa del aislamiento del clon F1 (laboratorio .150)
# ------------------------------------------------------------------------------
# El clon de PROD tiene las credenciales REALES de LDAP, Koha, Zammad, Entra y el
# bot de Telegram (descifrables con el keystore del home). Si sale a la red, puede
# escribir en ellos. Esta capa lo hace IMPOSIBLE por red, sin depender de midPoint:
#
#   cadena DOCKER-USER (la que Docker consulta antes que sus propias reglas):
#     subred del clon 172.31.41.0/24 ->
#       ACCEPT  dentro de la propia subred (midPoint <-> su Postgres)
#       ACCEPT  respuestas de conexiones ya establecidas
#       ACCEPT  Oracle LAMB 192.168.13.9:1521 (solo lectura: los 8 recursos tienen
#               create/update/delete deshabilitados y ningun script de escritura,
#               medido en PROD el 28-oct)
#       ACCEPT  EXTRA_ALLOW (opcional, "ip:puerto ip:puerto"): destinos DEL LAB
#               (p. ej. el OpenLDAP o el Zammad del laboratorio), nunca de PROD
#       DROP    todo lo demas (LDAP .168/.169, Koha .136, Graph/Entra, Zammad,
#               Telegram, DNS publico...)
#
# Las reglas llevan el comentario "mp411-f1" y se quitan todas con `quitar`.
# No persisten tras un reinicio del host (no se guardan con iptables-save):
# despues de reiniciar el lab hay que `aplicar` otra vez ANTES de arrancar el clon.
#
# ORDENES (con sudo):  aplicar | quitar | comprobar
#   comprobar: desde un contenedor efimero EN LA SUBRED del clon, intenta conectar a
#   Oracle (debe poder) y a LDAP PROD, Koha PROD, Graph y Telegram (NO debe poder).
# ------------------------------------------------------------------------------
set -euo pipefail
SUBNET="${SUBNET:-172.31.41.0/24}"
NET="${NET:-mp411_net}"
ORACLE="${ORACLE:-192.168.13.9:1521}"
EXTRA_ALLOW="${EXTRA_ALLOW:-}"
TAG="mp411-f1"
IPT="iptables"

del_all() {
    while read -r n; do $IPT -D DOCKER-USER "$n"; done < <($IPT -L DOCKER-USER --line-numbers -n | awk -v t="$TAG" '$0 ~ t {print $1}' | sort -rn)
}

case "${1:-}" in
aplicar)
    $IPT -L DOCKER-USER -n >/dev/null 2>&1 || { echo "No existe la cadena DOCKER-USER (¿Docker arrancado?)" >&2; exit 1; }
    del_all
    # Se insertan al principio en orden inverso: el DROP queda el ultimo de las nuestras.
    $IPT -I DOCKER-USER 1 -s "$SUBNET" -m comment --comment "$TAG drop resto" -j DROP
    for d in $EXTRA_ALLOW; do
        $IPT -I DOCKER-USER 1 -s "$SUBNET" -d "${d%:*}" -p tcp --dport "${d#*:}" -m comment --comment "$TAG extra lab" -j ACCEPT
    done
    $IPT -I DOCKER-USER 1 -s "$SUBNET" -d "${ORACLE%:*}" -p tcp --dport "${ORACLE#*:}" -m comment --comment "$TAG oracle lamb" -j ACCEPT
    $IPT -I DOCKER-USER 1 -s "$SUBNET" -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment "$TAG established" -j ACCEPT
    $IPT -I DOCKER-USER 1 -s "$SUBNET" -d "$SUBNET" -m comment --comment "$TAG intra" -j ACCEPT
    $IPT -L DOCKER-USER -n --line-numbers | grep -E "num|$TAG"
    ;;
quitar)
    del_all; echo "Reglas $TAG quitadas."; $IPT -L DOCKER-USER -n --line-numbers
    ;;
comprobar)
    docker network inspect "$NET" >/dev/null 2>&1 || { echo "No existe la red $NET (docker compose up -d midpoint_data primero)" >&2; exit 1; }
    probe() {  # probe host port esperado(ok|bloqueado)
        local r
        if docker run --rm --network "$NET" --entrypoint bash postgres:16-bullseye -c "timeout 5 bash -c '</dev/tcp/$1/$2'" >/dev/null 2>&1; then r=ok; else r=bloqueado; fi
        printf '  %-28s %-9s esperado %-9s %s\n' "$1:$2" "$r" "$3" "$([[ $r == "$3" ]] && echo OK || echo '<<< FALLO')"
        [[ "$r" == "$3" ]]
    }
    fail=0
    probe "${ORACLE%:*}" "${ORACLE#*:}" ok || fail=1
    probe 192.168.15.168 389 bloqueado || fail=1
    probe 192.168.15.169 389 bloqueado || fail=1
    probe 192.168.12.136 8001 bloqueado || fail=1
    probe 192.168.12.136 3306 bloqueado || fail=1
    probe 20.190.160.1 443 bloqueado || fail=1      # login.microsoftonline.com (rango Microsoft)
    probe 149.154.167.220 443 bloqueado || fail=1   # api.telegram.org
    probe 1.1.1.1 53 bloqueado || fail=1
    [[ $fail -eq 0 ]] && echo "AISLAMIENTO OK" || { echo "AISLAMIENTO ROTO: no arrancar el clon"; exit 1; }
    ;;
*) sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

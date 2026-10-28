#!/usr/bin/env bash
#
# muestra-sim.sh
# ------------------------------------------------------------------------------
# Simulacion ANTES/DESPUES de la subida sobre una MUESTRA FIJA de usuarios
# (protocolo PRE-EJECUCION: SIM PRE -> cambio -> SIM POST comparada con la PRE).
#
# La simulacion es un recompute+reconcile en modo preview (patron ya usado en
# docs/runbooks/entra-enriquecimiento-estudiantes-2026-10-15/task-sim-idempotencia.xml):
# evalua las 433 expresiones Groovy del camino de cada usuario (Person-Base,
# archetypes, outbounds de LDAP/Koha/Zammad/Entra) sin escribir nada en los
# recursos ni en los usuarios.
#
# ORDENES
#   generar [N]                     solo lectura: N usuarios (20) por vinculo vivo
#                                   (215 alum, 216 trabajador, 217 estudiante) y N
#                                   sin vinculo vivo; orden determinista md5(oid).
#                                   Salida: OIDs, uno por linea (guardar en fichero;
#                                   NO commitear: es una muestra de personas reales).
#   tarea <etiqueta> <oids>         imprime el XML de la tarea de simulacion
#   comparar <tareaPRE> <tareaPOST> solo lectura: compara, por usuario y proyeccion,
#                                   estado (ADDED/MODIFIED/DELETED/UNMODIFIED) y
#                                   metricas de los resultados de ambas tareas
#
# Lanzar la tarea (devuelve su OID en la cabecera Location):
#   ./muestra-sim.sh tarea pre-F3 muestra.oids > sim-pre.xml
#   curl -sS -u administrator -X POST -H 'Content-Type: application/xml' \
#        --data-binary @sim-pre.xml -D - -o /dev/null http://localhost:8080/midpoint/ws/rest/tasks
#
# ENTORNO: PG_CONTAINER (midpoint-midpoint_data-1)
# ------------------------------------------------------------------------------
set -euo pipefail
PG_CONTAINER="${PG_CONTAINER:-midpoint-midpoint_data-1}"
sql() { docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$PG_CONTAINER" psql -U midpoint -d midpoint -tA -F$'\t' -v ON_ERROR_STOP=1; }

case "${1:-}" in
generar)
    N="${2:-20}"; [[ "$N" =~ ^[0-9]+$ ]] || { echo "N invalido" >&2; exit 2; }
    sql <<SQL
(SELECT oid FROM m_user WHERE ext ? '215' ORDER BY md5(oid::text) LIMIT $N)
UNION (SELECT oid FROM m_user WHERE ext ? '216' ORDER BY md5(oid::text) LIMIT $N)
UNION (SELECT oid FROM m_user WHERE ext ? '217' ORDER BY md5(oid::text) LIMIT $N)
UNION (SELECT oid FROM m_user WHERE NOT (ext ?| array['215','216','217']) ORDER BY md5(oid::text) LIMIT $N);
SQL
    ;;
tarea)
    TAG="${2:?falta etiqueta}"; F="${3:?falta fichero de OIDs}"
    [[ "$TAG" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "etiqueta invalida" >&2; exit 2; }
    VALUES=$(grep -oE '^[0-9a-f-]{36}$' "$F" | sed 's#.*#<q:value>&</q:value>#' | tr -d '\n')
    [[ -n "$VALUES" ]] || { echo "sin OIDs en $F" >&2; exit 2; }
    cat <<XML
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3" xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3">
  <name>SIM upgrade-4.11 ${TAG} ($(date +%Y-%m-%d))</name>
  <description>docs/upgrade-4.11: recompute+reconcile en preview sobre la muestra fija ($(grep -cE '^[0-9a-f-]{36}$' "$F") usuarios).</description>
  <ownerRef oid="00000000-0000-0000-0000-000000000002" type="UserType"/>
  <executionState>runnable</executionState>
  <activity>
    <work>
      <recomputation>
        <objects>
          <type>UserType</type>
          <query><q:filter><q:inOid>${VALUES}</q:inOid></q:filter></query>
        </objects>
        <executionOptions><reconcile>true</reconcile></executionOptions>
      </recomputation>
    </work>
    <execution><mode>preview</mode><configurationToUse><predefined>production</predefined></configurationToUse></execution>
  </activity>
</task>
XML
    ;;
comparar)
    PRE="${2:?falta OID de la tarea PRE}"; POST="${3:?falta OID de la tarea POST}"
    q() {
        sql <<SQL
SELECT p.objecttype, coalesce(p.nameorig,'-'), p.state,
       coalesce(array_to_string(ARRAY(SELECT unnest(p.metricidentifiers) ORDER BY 1), ','),'')
FROM m_simulation_result r JOIN m_simulation_result_processed_object p ON p.ownerOid = r.oid
WHERE r.roottaskreftargetoid = '$1' ORDER BY 1, 2, 3;
SQL
    }
    T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
    q "$PRE" > "$T/pre.tsv"; q "$POST" > "$T/post.tsv"
    echo "PRE:  $(wc -l < "$T/pre.tsv") objetos procesados; POST: $(wc -l < "$T/post.tsv")"
    echo "Estados PRE:";  cut -f3 "$T/pre.tsv"  | sort | uniq -c
    echo "Estados POST:"; cut -f3 "$T/post.tsv" | sort | uniq -c
    if diff "$T/pre.tsv" "$T/post.tsv" > "$T/diff.txt"; then
        echo "IGUALES: mismo estado y metricas para todos los objetos."
    else
        echo "DIFERENCIAS (< PRE, > POST):"; cat "$T/diff.txt"; exit 1
    fi
    ;;
*) sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

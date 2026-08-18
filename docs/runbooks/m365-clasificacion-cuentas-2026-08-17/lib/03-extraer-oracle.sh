#!/usr/bin/env bash
# Extrae de Oracle LAMB el MDM de personas. SOLO LECTURA (política absoluta).
# El contenedor midpoint_server tiene ojdbc11 pero NO javac; el host de PROD sí:
# se compila en el host y se copia el .class con docker cp.
# Salida: $M365_WORK/{ora_correo.tsv, ora_doc.tsv, ora_nombres.tsv}
set -euo pipefail
: "${M365_WORK:?define M365_WORK}"
source ~/.secrets/midpoint-upeu.env
source ~/.secrets/oracle-lamb.env

JAR=/opt/midpoint/var/lib/ojdbc11-23.6.0.24.10.jar
DSN='jdbc:oracle:thin:@192.168.13.9:1521/UPEU'
ssh_mp() { sshpass -p "$MIDPOINT_PROD_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=60 midpoint-prod "$@"; }

echo "→ preparando cliente JDBC en PROD…"
ssh_mp 'docker exec midpoint_server test -f /tmp/OraQ.class 2>/dev/null || (mkdir -p /tmp/orq && cat > /tmp/orq/OraQ.java <<'"'"'EOF'"'"'
import java.sql.*;
public class OraQ {
  public static void main(String[] a) throws Exception {
    Connection c = DriverManager.getConnection(a[0], a[1], a[2]);
    Statement s = c.createStatement(); s.setFetchSize(5000);
    ResultSet r = s.executeQuery(a[3]);
    ResultSetMetaData m = r.getMetaData(); int n = m.getColumnCount();
    StringBuilder h = new StringBuilder();
    for (int i=1;i<=n;i++) h.append(m.getColumnName(i)).append(i<n?"\t":"");
    System.out.println(h);
    while (r.next()) {
      StringBuilder b = new StringBuilder();
      for (int i=1;i<=n;i++){Object v=r.getObject(i);b.append(v==null?"":v.toString().replace("\t"," ").replace("\n"," ")).append(i<n?"\t":"");}
      System.out.println(b);
    }
    c.close();
  }
}
EOF
javac -d /tmp/orq /tmp/orq/OraQ.java && docker cp /tmp/orq/OraQ.class midpoint_server:/tmp/OraQ.class)' >/dev/null

ora() { ssh_mp "docker exec midpoint_server java -cp /tmp:$JAR OraQ '$DSN' '$ORACLE_USER' '$ORACLE_PASS' \"$1\""; }

# OJO: MOISES.PERSONA_NATURAL NO tiene NOMBRE/PATERNO/MATERNO (están en MOISES.PERSONA).
echo "→ correo institucional del MDM…"
ora "SELECT pn.ID_PERSONA, lower(pn.CORREO_INST) AS CORREO_INST, pn.NUM_DOCUMENTO, p.NOMBRE, p.PATERNO, p.MATERNO \
FROM MOISES.PERSONA_NATURAL pn LEFT JOIN MOISES.PERSONA p ON p.ID_PERSONA=pn.ID_PERSONA \
WHERE pn.CORREO_INST IS NOT NULL" > "$M365_WORK/ora_correo.tsv"

echo "→ documentos de identidad…"
ora "SELECT NUM_DOCUMENTO, min(ID_PERSONA) AS ID_PERSONA FROM MOISES.PERSONA_NATURAL \
WHERE NUM_DOCUMENTO IS NOT NULL GROUP BY NUM_DOCUMENTO" > "$M365_WORK/ora_doc.tsv"

echo "→ nombres del MDM completo…"
ora "SELECT ID_PERSONA, NOMBRE, PATERNO, MATERNO FROM MOISES.PERSONA WHERE NOMBRE IS NOT NULL" \
  > "$M365_WORK/ora_nombres.tsv"

# sede de egresados: MidPoint no la puebla para alumni, la vista de Oracle sí la tiene
echo "→ sede de egresados…"
ora "SELECT CODIGO, MAX(SEDE) AS SEDE FROM DAVID.VW_PERSONA_EGRESADO WHERE CODIGO IS NOT NULL GROUP BY CODIGO" \
  > "$M365_WORK/ora_sede_egresado.tsv" || echo "   (opcional, continúa)"

for f in ora_correo ora_doc ora_nombres; do
  n=$(wc -l < "$M365_WORK/$f.tsv")
  echo "   $f.tsv: $n filas"
  [ "$n" -gt 100 ] || { echo "   ⚠ $f.tsv sospechosamente corto"; exit 1; }
done

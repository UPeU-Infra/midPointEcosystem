# F1 · Resultado del ensayo en el laboratorio (3-nov-2026)

Clon de PROD (backup diario del 2-nov 22:30, dump sin auditoría + home) en el lab
`192.168.15.150`, proyecto `mp411`, puerto 8096. Se ejecutaron F2 y F3 completos, las dos
vueltas atrás y un segundo avance a 4.10.5, con los scripts de `upeu/infra/upgrade-4.11/`.

**Veredicto: la subida 4.10.2 → 4.10.5 → 4.11.0 funciona y las dos vueltas atrás también.**
La simulación de la muestra da **IGUALES** en las tres versiones. Quedan dos cosas sin ensayar
(Oracle y escritura real, §3) que pasan al canario de F3.

## 1. Condiciones (no son las de PROD)

| | Lab | PROD | Efecto |
|---|---|---|---|
| RAM | MidPoint 5 GB (heap 4 GB), Postgres 2,5 GB (`shared_buffers` 512 MB) | 10 GB + 5 GB | Decisión del 3-nov: clon reducido, sin parar nada del lab. Los arranques y la SIM pueden ser más lentos en el lab |
| BD | 5 GB, **sin datos de auditoría** | 26 GB (3-nov, tras la purga), auditoría desde sep-2026 | La copia local y el `run-sql` de auditoría serán más largos en PROD |
| Oracle LAMB | **inalcanzable**: `192.168.13.9:1521` responde *Connection refused* al `.150` (desde la Mac por VPN y desde el `.166` sí conecta) | accesible | Los 8 recursos Oracle no se pudieron probar contra Oracle (§3) |
| Aislamiento | 3 capas aplicadas y comprobadas | — | 0 conexiones a LDAP, Koha, Graph, Telegram ni DNS público |

## 2. Tiempos medidos

| Paso | Tiempo | Notas |
|---|---|---|
| `pg_restore` del dump diario (en serie) | 661 s | 2,7 GB de dump → 5 GB de BD |
| `bd-copia-local.sh crear` | 53–59 s | 5 GB ≈ 90 MB/s. **PROD (26 GB): ~5 min** |
| Arranque 4.10.2 → `healthy` | 63–74 s | |
| Arranque 4.10.5 → `healthy` | 64 s | |
| PATCH LDAP 3.9.4 + test | 17 s | |
| **Vuelta atrás F2 (R1–R6)** | **245 s** | 178 s son el test de los 12 recursos (Entra agota su timeout de 121 s porque la red lo bloquea) |
| Segundo avance a 4.10.5 (pasos 3–12, sin test de recursos) | 226 s | |
| `chown -R` del home | 2 s | |
| `run-sql --upgrade` repositorio (51 → 67) | 8 s | |
| `run-sql --upgrade` auditoría (10 → 16) | 7 s | Sin datos de auditoría en el lab ❓ en PROD |
| `ninja verify` de 4.11 | **1.531 s (25 min)** | No va en la ventana: se hace en F1 |
| `initial-objects` (informe todo / lista blanca / aplicar) | 26 / 22 / 25 s | |
| Arranque 4.11.0 → `healthy` | 75 s | UID 1000 |
| PATCH LDAP 3.10 + test | 16 s | |
| SIM muestra (PRE 4.10.2 / POST 4.10.5 / PRE-F3 / POST-F3) | 63 / 72 / 73 / 83 s | 73 usuarios, 330 objetos |
| SIM recon Oracle Trabajadores | — | No ensayable (Oracle inalcanzable) |
| **Vuelta atrás F3 (R1–R5)** | **86 s** | + ~170 s si se incluye el test de recursos |
| Test de los 12 recursos | ~170 s | En el lab todos fallan al conectar (red cortada) |

## 3. Lo que NO se pudo ensayar

1. **Los 8 recursos Oracle contra Oracle real** con ConnId 1.7 y ScriptedSQL 2.2.10, y la SIM de
   la recon de Trabajadores. El conector **carga** (`available=t`, test: `initialization`,
   `configure` e `initialize` en `success`); lo que falta es la conexión. Para ensayarlo hace falta
   que Oracle acepte al `.150` (petición al DBA/redes) o dejarlo al **canario del paso 21 de F3**.
2. **Escritura real** de LDAP 3.10, Koha 1.7.1 y Zammad 0.2.0 bajo ConnId 1.7 (etapa B opcional de
   F1). Queda para el canario del paso 21 de F3.

## 4. Hallazgos y correcciones (todas aplicadas en la rama)

| # | Hallazgo | Corrección |
|---|---|---|
| H1 | **El test de conexión SÍ contacta** el recurso aunque esté en `maintenance` | Resuelve un ❓: la capa 1 (red) es imprescindible; la 2 no basta sola |
| H2 | El transporte de Telegram (con el token) vive también en `notificationConfiguration/customTransport`; `aislar-midpoint.sh` solo quitaba `messageTransportConfiguration` | El script quita los dos y lo comprueba (`f\|f`) |
| H3 | `bd-copia-local.sh restaurar` sin terminal **salía en silencio** (el `read` fallaba con `set -e`): la vuelta atrás parecía hecha y no lo estaba | Ahora imprime `ABORTO: cancelado`; `--yes` documentado |
| H4 | `docker compose run` sin `-T` **se come el stdin**: dentro de un script, el resto de órdenes no se ejecuta | En los runbooks, `run --rm -T`. A mano, en terminal, no afecta |
| H5 | `ninja pre-upgrade-check` de 4.11 **no arranca** contra una BD en esquema 51 (su repositorio exige 67; también con `upgradeableSchemaAction=warn`) | F3 §1.3 pasa a una consulta SQL: versión de los nodos y `m_global_metadata` |
| H6 | El `chown` de F3 paso 9 montaba el home en `/var` de la imagen `postgres`, que declara `VOLUME /var/lib/postgresql/data`: creaba `lib/postgresql/data` **dentro del home** | Se monta en `/v`. Probado: todo 1000:1000 y sin rutas ajenas |
| H7 | La comprobación del informe de initial-objects buscaba los OID prohibidos en **todo** el informe: dio 1 falso positivo (`targetArchetypeRef` al 330 dentro de una política) | Se comparan solo los `objectToAdd oid`: 0 prohibidos y los 39 exactos |
| H8 | **`verify` de 4.11: 0 CRITICAL, 1 NECESSARY** (`SystemConfiguration` → `cleanupPolicy/objectResults`, eliminado en 4.11), 288 OPTIONAL, 9.027 avisos de *deprecated* | Nuevo `sysconfig-cleanup-objectresults-delete.xml` (+ `-rollback.xml`), probado en 4.10.5 ida y vuelta (204, versión +1, el resto de `cleanupPolicy` intacto). Va en F3 §1. Si se olvida, 4.11 arranca igual (medido) |
| H9 | F3 paso 16 consultaba el conector Koha **1.7.0** (`8c090235…`); el recurso usa el **1.7.1** (`51e26e79…`) | OID corregido. Con 4.11, 1.7.1 `available=t` |
| H10 | Cada arranque de 4.10.5 registra el LDAP 3.9.4 con **OID distinto** (`5cd85a8f…` y luego `32b02179…`) | Confirma que `ldap-connectorref.sh` debe buscar el OID en el momento (ya lo hace) |
| H11 | `ERROR InitialDataImport: Couldn't import archetype 89a34123… (Project)` en **cada** arranque, también en 4.10.2: choca con el archetype «Project» ya existente (`1d773496…`) | Preexistente, no lo trae la subida. No bloquea. Revisar aparte en F4 |
| H12 | La SIM marca 17 objetos `MODIFIED` en las cuatro corridas (también en 4.10.2) | Deriva preexistente de la muestra, igual en todas las versiones: no la causa la subida |

## 5. Criterio de salida a F2

| Criterio | Estado |
|---|---|
| 0 bloqueos sin resolver | ✅ (H1–H10 corregidos o resueltos) |
| Vueltas atrás dentro de objetivo | ✅ F2 245 s (< 15 min) · F3 86 s (< 20 min) |
| SIM POST igual a la PRE | ✅ **IGUALES** 4.10.2 = 4.10.5 = 4.11.0 |
| 8/8 Oracle `success` en 4.11 | ⚠️ **no medible en el lab** (H, §3.1): el conector carga; la conexión se prueba en el canario de F3 |
| Conectores propios `available=t` | ✅ Koha 1.7.1, Zammad 0.2.0, ScriptedSQL 2.2.10, msgraph 1.2.0.0 y LDAP 3.10 |

## 6. ❓ que siguen abiertos

- Texto exacto del log que indica «planificador en marcha» (F2 paso 12): `grep -i 'scheduler\|quartz'`
  no devuelve nada en 4.10.5 ni en 4.11. Verificar con `tareas-ventana.sh estado` (las tareas de
  sistema pasan a ejecutarse) en vez de con el log.
- `data_init` de 4.11-alpine con UID 1000 («Repository init is not needed»): el compose del lab lo
  neutraliza siempre, así que no se vio. Se verá en PROD en F3 paso 19.
- Duración del `run-sql` de auditoría con datos reales (PROD).

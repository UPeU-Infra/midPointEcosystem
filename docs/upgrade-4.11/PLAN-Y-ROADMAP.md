# MidPoint UPeU 4.10.2 → 4.11.0 — plan de acción y roadmap

**Fecha:** 27-oct-2026 · **Estado:** propuesta · **Base medida:** [`INVENTARIO-PROD-4.10.md`](INVENTARIO-PROD-4.10.md) (solo lectura, 27-oct)
**Release:** [4.11.0 «Čapek»](https://docs.evolveum.com/midpoint/release/4.11.0/), publicada el 21-oct-2026, soporte hasta el 20-oct-2028.

## 1. Decisión

Subir a 4.11.0 **en dos saltos** (4.10.2 → 4.10.5 → 4.11.0), primero ensayado completo en el laboratorio, y **sin adoptar
todavía la seguridad de expresiones de 4.11**. Esa adopción (migrar Groovy a MEL) es un proyecto aparte y posterior.

**Por qué ahora:** la 4.10 sigue con soporte, pero 4.11 corrige fallos que nos tocan (asignaciones duplicadas por
colisiones multihilo MID-10714, outbound de activación sobre shadows no gestionados MID-11029, crecimiento sin límite de
resultados en tareas largas MID-12197) y trae MFA TOTP para la consola. Subir pronto, con la configuración intacta,
es más barato que acumular saltos.

**Por qué en dos fases para las expresiones:** las 433 expresiones son Groovy y no declaran lenguaje. Medido en el
código de 4.11: si la SystemConfiguration no define perfiles ni `defaultScriptLanguage`, y `config.xml` no activa
`safeScriptingLanguagesOnly`, todo se evalúa como hoy. **Subir no obliga a reescribir nada; adoptar MEL sí** (3–5 semanas).

## 2. Lo que bloquea (todo es de plataforma)

| # | Bloqueante | Arreglo |
|---|---|---|
| B1 | La imagen 4.11 corre como **UID 1000**; hoy el contenedor corre como root y el home tiene archivos de root (keystore `0600`, `log/` `0750`). | `chown -R 1000:1000` del volumen de midpoint home con el contenedor parado; verificar que el keystore se lee. |
| B2 | Solo se sube a 4.11 desde la **última 4.10.x (4.10.5)**. | Salto intermedio 4.10.2 → 4.10.5. |
| B3 | Esquema de BD 51/10 → 67/16 (repo/auditoría) y el compose usa `upgradeableSchemaAction=stop`; el servicio `data_init` lanza `run-sql --create` si `ninja info` da error. | `ninja run-sql --upgrade --mode repository` y `--mode audit` antes de arrancar; neutralizar `data_init` durante la subida. |
| B4 | 4.11 crea `ma_audit_payload` con FK hacia los eventos: el script mensual de particiones (`audit-partition-maintenance.sh`) fallará al borrar. | Añadir payload al orden de exportación y borrado **antes del 1-dic**. |
| B5 | El recurso LDAP usa el conector **bundled** 3.9.2; 4.11 trae el 3.10. | PATCH del `connectorRef` (nunca PUT) y test connection. Sin esto, el LDAP (58.883 cuentas) queda parado. |

## 3. Riesgos altos y cómo se cubren

- **No importar la SystemConfiguration de 4.11** (ni la 702 ni la 004): trae `defaultScriptLanguage=mel` y perfiles por
  tipo que romperían las 433 expresiones a la vez. `ninja initial-objects` siempre con `--dry-run --report` y lista
  de exclusiones.
- **Dejar escrito `safeScriptingLanguagesOnly=false` en `config.xml`** para que una reconstrucción del volumen no lo active.
- **ConnId 1.7.0.0-M0 (milestone)** con los conectores externos: ScriptedSQL 2.2.10 (×8), Koha 1.7.0 y Zammad 0.2.0
  (estos dos llevan framework interno 1.5.2.0) y msgraph 1.2.0.0. Se prueban uno por uno en el laboratorio.
- **Imagen base Alpine por defecto:** el redimensionado de fotos de Entra usa `java.awt`/ImageIO. Se usa la variante
  `-ubuntu` (la de hoy) para no cambiar dos cosas a la vez.
- **Expresiones ad hoc del administrador (GUI/REST)** pasan a «ninguna» en 4.11 si no se configura
  `expressions/defaults/privilegedPrincipal`: configurarlo explícitamente.
- **Repo ≠ PROD** en conectores (Koha) y compose: alinear antes, porque el ensayo se monta desde el repo.

## 4. Roadmap

| Fase | Qué | Cuándo (propuesto) | Ventana |
|---|---|---|---|
| **F0 · Preparación** | Terminar y estabilizar los cambios en curso sobre 4.10.2 (activación por vínculo vivo global + lote; fusión de Hulda). Alinear repo↔PROD (compose, Koha). Arreglar el script de particiones de auditoría (B4). Preparar `config.xml` y compose para 4.11 (B1, B3). **Congelar cambios de configuración** desde el fin de F0. | 28-oct → 7-nov | — |
| **F1 · Ensayo en laboratorio (.150)** | Restaurar el backup de PROD en el lab, **con todos los recursos de escritura apuntando a destinos de laboratorio o con capabilities de escritura cerradas** (nunca escribir en el LDAP/Koha/Entra reales). Ejecutar 4.10.2 → 4.10.5 → 4.11.0 completo con el runbook, cronometrar cada paso, probar los 12 recursos (test connection + recon en preview), comparar SIM antes/después sobre una muestra fija. | 10 → 14-nov | Lab |
| **F2 · PROD: 4.10.2 → 4.10.5** | Salto de mantenimiento (esquema compatible). Una semana de observación con las recons diarias. | mar 18-nov | 16:30–20:30 UTC |
| **F3 · PROD: 4.10.5 → 4.11.0** | B1, B3, B5; initial objects con exclusiones; reindex; reactivar tareas una a una. | mar 25-nov | 16:30–21:30 UTC |
| **F4 · Estabilización** | Observación 1–2 semanas; script de particiones probado el 1-dic; initial objects de reports/dashboards/value policy en MEL (los 135 scripts de Evolveum no modificados). | 26-nov → 12-dic | — |
| **F5 · Adopción de seguridad 4.11** (proyecto aparte) | Migrar a MEL los 298 scripts UPeU (192 fáciles, 60 con API de MidPoint, 46 con Java/red/E/S), las 11 `function`, y sustituir el transporte de Telegram por HttpClient; luego perfiles por tipo y `safeScriptingLanguagesOnly=true`. TOTP para administradores. `displayName`/`preferredName`. | ene → mar 2027 (antes de la matrícula 2027-1) | Varias |

**Dependencias:** F1 no empieza sin F0 cerrada; F3 solo si F1 sale limpio y F2 lleva una semana sin incidencias.
**Evitar:** semanas de matrícula y cierres de ciclo; la 4.10.6 sale en enero (no se espera por ella).

## 5. Procedimiento de cada ventana PROD (resumen; detalle en el runbook de F1)

1. Antes (fuera de ventana): `ninja pre-upgrade-check` y `ninja verify -o verify.csv` con la ninja de la versión destino;
   0 errores de «deprecated/removed».
2. Suspender tareas programadas (lista en el inventario §6) y bloquear el acceso de usuarios dejando acceso admin.
3. Parar MidPoint (la BD sigue arriba); **backup completo**: `pg_dump` del repo y la auditoría + tar del midpoint home
   (keystore incluido), con `.sha256`, a S3.
4. F3 solamente: `chown -R 1000:1000` del home; `config.xml` con `safeScriptingLanguagesOnly=false`; `data_init` neutralizado.
5. `ninja run-sql --upgrade --mode repository` y `--mode audit`.
6. Cambiar la imagen en el compose (`4.10.5-ubuntu` / `4.11.0-ubuntu`) y arrancar; health check.
7. F3: PATCH `connectorRef` LDAP → 3.10; test connection de los 12 recursos.
8. F3: `ninja initial-objects --dry-run --report` con exclusiones (000, 702, 004…); revisar y aplicar.
9. Reindex de objetos; reactivar tareas de una en una empezando por las de solo lectura; medir.
10. **Vuelta atrás:** el esquema no se revierte. Parar, restaurar el dump y el home del paso 3, volver a la imagen anterior.
    Ensayada en F1 y cronometrada.

## 6. Criterios de éxito (medidos, no supuestos)

- Los 12 recursos en `success` en test connection; las 8 recons Oracle + Koha + Entra terminan con el mismo
  `resultStatus` que antes.
- `pendingOperationCount` = 0 y ninguna diferencia en la foto de estado de los 66.030 usuarios (`snapshot-estado.sql`)
  que no explique la propia recon del día.
- LDAP .168 = .169 (conteos y CSN).
- 0 errores de expresión en el log tras la primera pasada de cada recon.

## 7. Trabajo que NO entra en esta subida

midPilot (IA para conectores y mappings: requiere microservicio y LLM; evaluarlo aparte con datos anonimizados),
ITSM con kind `work`, políticas de foco por actividad. Se evalúan en F5 o después.

## 8. Catálogo de integraciones (consulta del 27-oct)

- **Entra / M365:** ya usamos el conector del catálogo (`MSGraphConnector 1.2.0.0`).
- **«Oracle Database»** del catálogo (`OracleConnector 1.1.0.0`) gestiona **cuentas de usuario de la propia base Oracle**;
  no sirve para leer los datos de LAMB (personas, matrículas, contratos). Seguimos con ScriptedSQL.

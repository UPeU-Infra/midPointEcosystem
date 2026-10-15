# ADR-067 — Escuelas Profesionales nuevas que el árbol no tiene (BORRADOR)

**Estado:** BORRADOR — **no aplicado**. Requiere aprobación de Alberto, simulación `preview` y canario,
y baseline regenerada **en el mismo commit** (contrato de cambio de
[`../../ARQUITECTURA-ARBOL-ORGANIZATIVO.md`](../../ARQUITECTURA-ARBOL-ORGANIZATIVO.md) §2, nivel 🟡).
**Fecha:** 2026-10-15 · **Origen:** «arregla los que faltan escuela» (Alberto); runbook
[`../../runbooks/estudiantes-campus-matricula-pregrado-2026-10-14/`](../../runbooks/estudiantes-campus-matricula-pregrado-2026-10-14/README.md).

## Contexto (medido el 15-oct-2026)

Tras el corte de campus/escuela por matrícula de pregrado y los alias del lookup `d9b1e0c2`
(misma fecha), quedan **143 estudiantes de pregrado activos** cuyo programa **no tiene org EP** en el
árbol. No es un alias que falte: son **carreras nuevas** (todas con P-code propio en VocBench, ninguna
con `CODIGO_SUNEDU2` en Oracle), y el árbol solo tiene las 26 `EP-*` del archetype `Academic-Program`.

| Carrera (ORG_AREA.NOMBRE en Oracle) | ID_AREA | ID_PROGRAMA_ESTUDIO | P-code (VocBench `program-pxx-byid`) | URI VocBench | Facultad (Oracle `ID_PARENT`) | Estudiantes hoy (feed) |
|---|---|---|---|---|---|---|
| CARRERA DE COMUNICACIÓN AUDIOVISUAL Y MEDIOS INTERACTIVOS | 8142 | 1107 (Lima) | P146 | `…/programa/comunicacion-audiovisual-y-medios-interactivos` | F. Ciencias Humanas y Educación | 49 (Lima) |
| Tecnología Médica en Laboratorio Clínico y Anatomía Patológica | 8153 | 1124 (Lima), 1326 (Juliaca, sin P-code) | P153 | `…/programa/tecnologia-medica-especialidad-de-laboratorio-clinico-y-anatomia-patol` | F. Ciencias de la Salud | 36 (Lima) |
| Tecnología Médica en Terapia Física y Rehabilitación | 8154 | 1125 (Lima), 1325 (Juliaca, sin P-code) | P155 | `…/programa/tecnologia-medica-especialidad-de-terapia-fisica-y-rehabilitacion` | F. Ciencias de la Salud | 23 (Lima) |
| EAP Negocios Internacionales y Gestión Portuaria | 8255 | 1266 (Lima) | P160 | `…/programa/negocios-internacionales-y-gestion-portuaria` | F. Ciencias Empresariales | 21 (Lima) |
| EP Ingeniería de ciberseguridad | 8137 | 1102 (Lima) | P151 | `…/programa/ingenieria-de-ciberseguridad` | F. Ingeniería y Arquitectura | 14 (Lima) |

Hay más carreras nuevas en Oracle **sin estudiantes en el feed hoy** (no entran en esta decisión, pero
el mismo criterio les aplicará): Ingeniería de Ciencia de Datos e IA (1100), Comunicación
Organizacional / y Publicidad / y Periodismo (1104–1106), Digital Business (1178/1199/1200), Computer
Science (1179/1203/1204).

⚠️ Los nombres de la tabla son los de Oracle. **El nombre oficial (Res. de creación / licenciamiento
SUNEDU) hay que confirmarlo con Registros Académicos** antes de fijar `displayName`; no se inventa.

## Decisión propuesta

1. **Una org EP por carrera**, archetype `Academic-Program` (`9f3b8e2a-4c7d-4b1e-a8f5-6d2c4e9a1b73`),
   `subtype=academic-program`, **un único padre**: su facultad. Nunca un campus: las orgs multi-padre
   con más de un ancestro proyectable generan **un shadow de OU por camino** (incidente del 6-ago).

   | name = identifier (INMUTABLE) | displayName (a confirmar) | Padre | P-code | URI |
   |---|---|---|---|---|
   | `EP-COM-AUD` | Comunicación Audiovisual y Medios Interactivos | `FACULTAD-EDUCACION` (id 8) | P146 | VocBench 1107 |
   | `EP-TM-LAB` | Tecnología Médica — Laboratorio Clínico y Anatomía Patológica | `FACULTAD-SALUD` (id 10) | P153 | VocBench 1124 |
   | `EP-TM-TFR` | Tecnología Médica — Terapia Física y Rehabilitación | `FACULTAD-SALUD` (id 10) | P155 | VocBench 1125 |
   | `EP-NIGP` | Negocios Internacionales y Gestión Portuaria | `FACULTAD-EMPRESARIALES` (id 12) | P160 | VocBench 1266 |
   | `EP-ICIB` | Ingeniería de Ciberseguridad | `FACULTAD-INGENIERIA` (id 9) | P151 | VocBench 1102 |

   Los códigos `EP-*` son **propuesta**: el `identifier` gobierna el RDN de la OU en LDAP y el
   conector **no sabe renombrar** (incidente del 5-ago). Fijarlos antes de crear; después son inmutables.

2. **Versionar** las 5 orgs en `upeu/orgs/academic-programs/academic-programs-pregrado.xml` (prohibido
   crearlas a mano en PROD) y regenerar `docs/baselines/arbol-organizativo-baseline.json` en el mismo commit.

3. **Alias en el lookup `d9b1e0c2`**: una fila por nombre de Oracle (tras quitar `EP `/`EAP`), con
   `label` = el `EP-*` nuevo y `value` = la URI de VocBench. Ojo: `resolveProgramCode` solo quita el
   prefijo `EP `; para «EAP Negocios…» la clave tiene que ser el texto completo `EAP Negocios
   Internacionales y Gestión Portuaria`. Mismo procedimiento que los alias del 15-oct (simular los tres
   consumidores: Estudiantes, Egresados, Trabajadores `TEACHING_PROGRAMS`).

4. **Mejor a medio plazo** (fuera de este ADR): resolver la escuela por `ID_PROGRAMA_ESTUDIO` y no por
   nombre (ADR-062/063 ya publican el ID). Con eso, una carrera nueva solo necesita su org EP.

## Efecto en LDAP (`ldap-identity-cache`, `7b4e1c2d-…`) — a verificar en la simulación

- **`generic/ou`** (toda org proyecta una OU, D4): cada EP nueva **crea** una OU. El DN es
  **jerárquico** (apila ancestros cuyo archetype está en `OU_ARCH`; el campus ya NO está desde v224):
  se espera `ou=ep-com-aud,ou=8,ou=org,dc=upeu,dc=edu,dc=pe`, `ou=ep-tm-lab,ou=10,…`,
  `ou=ep-tm-tfr,ou=10,…`, `ou=ep-nigp,ou=12,…`, `ou=ep-icib,ou=9,…`. Son **altas**, no movimientos;
  ninguna OU existente cambia de DN. **Verificar con el script real** del outbound `ri:dn` antes de
  ejecutar (R1/R2 del protocolo), no con este texto.
- **Personas**: `eduPersonOrgUnitDN` +1 valor para los 143 (vía `roleMembershipRef` a una org
  `Academic-Program`). El DN de la cuenta (`uid=…,ou=people`) no cambia.
- `scibackAcademicProgramCode` en la OU nueva (outbound de `generic/ou`).

## Efecto en Koha

Ninguno directo: `library_id`, `statistics_1` y la categoría no dependen de la org EP.

## Orden de ejecución (cuando se apruebe)

ADR aprobado → orgs en el repo + baseline → `python3 upeu/scripts/verificar-arbol-organizativo.py`
→ simulación `preview` (crear orgs + alias + recompute de los 143) leyendo el diff de `generic/ou` →
canario (1 org + sus alumnos) → lote → verificador 8/8 y LDAP en .168/.169.

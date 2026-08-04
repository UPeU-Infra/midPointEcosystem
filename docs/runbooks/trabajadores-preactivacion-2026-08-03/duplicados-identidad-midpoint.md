# 14 personas con dos identidades en MidPoint — análisis y plan

**Fecha:** 2026-08-04 · **Medido en vivo** en PROD · **Nada ejecutado: requiere decisión**
**Origen:** verificación previa al tier de correlación por `lambIdPersona`
([`correlacion-resuelta.md`](correlacion-resuelta.md) §2)

---

## 1. Qué son

14 personas tienen **dos objetos `User`** en MidPoint, con el mismo `lambIdPersona` (el
`ID_PERSONA` de Oracle) y el mismo nombre:

- uno creado por el canal **Estudiantes / Egresados** (código académico: `202212637`, `9610006`…)
- otro por el canal **Trabajadores** (código de trabajador o DNI: `03657510`, `007736542`…)

**No es un problema histórico.** Todos se crearon entre el **17-may y el 20-jul de 2026**, durante
la puesta en marcha del IGA: los canales se cargaron por separado y ninguno miraba al otro. El tier
de `lambIdPersona` (resource v324) **impide que aparezcan nuevos**, pero no toca los ya existentes:
el correlator actúa sobre shadows por vincular, no sobre `User` ya creados.

## 2. Los graves — 6 personas con **dos entradas LDAP vivas**

Ambas identidades activas, ambas con proyección en el directorio:

| `lambIdPersona` | Persona | Identidad A | Identidad B | Entradas LDAP |
|---|---|---|---|---|
| 201841 | Ken Jefrey Nieto Flores | `03657510` (trabajador) | `202212637` (estudiante) | **2 × `ou=people`** |
| 246076 | Enmanuel José Albarran Castillo | `07134778` (trabajador) | `202211499` (estudiante) | **2 × `ou=people`** |
| 77791 | Lisle Jahely Juarez Serquen | `201811693` (egresada) | `75609890` (trabajadora) | **2 × `ou=people`** |
| 220809 | Dayana Iveth Morales Paredes | `005705811` (trabajadora) | `202122320` (egresada) | `people` + `alumni` |
| 49661 | Jacksaint Saintila | `000837035` (trabajador) | `201020351` (egresado) | `people` + `alumni` |
| 74349 | Osclaris Jhoanna Martinez Avila | `01660870` (trabajadora) | `201711673` (egresada) | `people` + `alumni` |

Los tres primeros son los peores: **dos `uid` distintos para la misma persona en la misma OU**.
Cualquier consumidor del directorio (RIMS, InOut, Pulso DTI) los ve como dos personas.

## 3. Identidades archivadas que conservan accesos reales

Tres `User` en estado `archived` (`effectiveStatus=DISABLED`) siguen con proyecciones vivas:

| Persona | Identidad archivada | Proyecciones que conserva |
|---|---|---|
| Paúl Eduardo Villao Mendoza | `001502765` | LDAP `ou=people` + **Koha ILS** + **Koha consolidado** |
| Yahir Alexander Neira Curo | `324110503` | LDAP `ou=people` + **Koha consolidado** |
| Felix Manuel Lopez Pedrozo | `001914761` | LDAP `ou=people` + **Koha consolidado** |

Es decir: identidades dadas de baja **con carné de biblioteca activo**. El `existence` condicional
desplegado hoy (LDAP v222) hará que en el próximo recompute su entrada LDAP quede `disabled` —
pero **Koha no tiene ese arreglo**, y la entrada duplicada seguirá existiendo.

## 4. Los 5 restantes — menor gravedad

Una identidad activa y otra archivada cuya única proyección es el propio resource de origen
(`Oracle LAMB Trabajadores`), sin accesos que retirar:

`13890` Michael Orellana · `427076` Cristhian Chamba · `428877` Christian Ødegård ·
`72273` Albert Tacilla · `8536` Jeff Brañez

## 5. Por qué no se ha ejecutado nada

Fusionar identidades es **irreversible** y afecta a personas reales: mueve proyecciones, roles y
asignaciones entre objetos, y decide cuál de los dos `uid` sobrevive en el directorio — lo que a su
vez cambia el ancla `eduPersonUniqueId` que los consumidores guardan.

Requiere decidir, para cada par:

1. **Cuál identidad se conserva.** La regla natural sería *la que tiene el vínculo vivo más
   reciente*, pero en los 6 casos del §2 ambas están activas y ambas son legítimas: la persona
   **es** estudiante/egresado **y** trabajador a la vez.
2. **Qué pasa con el `uid` que desaparece** en LDAP y Koha, y a quién hay que avisar.
3. **Si se fusiona o se enlaza.** MidPoint 4.10 tiene `mergeObjects` en la API, pero necesita un
   `objectMergeType` declarado en `SystemConfiguration`, que hoy no existe.

## 6. Recomendación

**Tratarlo como un lote aparte, después de reactivar la reconciliación**, no antes. Razones:

- El tier de `lambIdPersona` ya **cierra la fuga**: no van a aparecer más.
- Los 14 son un número acotado y conocido, con nombre y apellido.
- Fusionar identidades mientras se estabiliza el canal de trabajadores mezcla dos riesgos que
  conviene mantener separados.

### ✅ Comprobado: NO hay buzones duplicados en Entra

Se verificó (04-ago) por ser barato y por el precedente del informe de duales entregado a DTI el
3-ago. **Ninguno de los 14 tiene dos buzones.** Solo una de las dos identidades proyecta a
`UPEU-EntraID-Graph` en cada caso:

| Persona | Identidad que tiene el buzón | Correo |
|---|---|---|
| Ken Jefrey Nieto Flores | `202212637` (estudiante) | `ken.nieto@upeu.edu.pe` |
| Dayana Iveth Morales Paredes | `202122320` (egresada) | `dayana.morales@upeu.edu.pe` |
| Enmanuel José Albarran Castillo | `07134778` (trabajador) | `enmanuel.albarran@upeu.edu.pe` |
| Felix Manuel Lopez Pedrozo | `202511206` (estudiante) | `manuel.lopez@upeu.edu.pe` |
| Osclaris Jhoanna Martinez Avila | `201711673` (egresada) | `osclarismartinez@upeu.edu.pe` |

**Esto acota el problema:** el correo no está duplicado. La duplicación se limita a **LDAP** y
**Koha**, y da además un criterio objetivo para elegir qué identidad conservar en la fusión —
**la que tiene el buzón**, porque es la que el usuario reconoce y con la que se autentica.

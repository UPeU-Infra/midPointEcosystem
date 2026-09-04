# Gobierno de los grupos LDAP del DTI desde MidPoint — canario cerrado

**03-sep-2026 · producción · los 5 criterios de aceptación cumplidos y verificados en vivo**

## Qué hace

MidPoint gobierna la pertenencia a los 22 grupos `cn=dti-*,ou=groups` a partir de
`extension/upeu:serviceDeskTeam`. Cambiar el equipo de una persona en el IGA la mueve de grupo
en el directorio sin tocar LDAP a mano, y un recompute reconstruye lo que alguien borre.

## Decisión de diseño: RoleType por equipo, NO OrgType

No es preferencia. **El Org DTI tiene proyección a LDAP** (`linkRef` → shadow `generic/ou` =
`ou=18,ou=org,…`), así que modelar los equipos como OrgType habría:

1. Creado **22 OUs nuevas** en `ou=org` — el `identifier` del OrgType gobierna el DN de su OU,
   que es el incidente del 5-6 de agosto.
2. Invadido el espacio de identificadores de **Oracle LAMB**: el `identifier` del DTI es `"18"`
   (= `areaId`) y ese árbol lo escribe el recurso `Oracle LAMB Org`. Los 22 equipos no existen
   en Oracle — serían dos autoridades sobre un mismo árbol sincronizado.
3. Tocado a las 64 personas, sumando `parentOrgRef`, que alimenta mappings de salida.

El equipo del DTI es **acceso a una aplicación** (alimenta las colas de agentes de Zammad), no
estructura organizativa: es un *Application Role* de manual.

**El slug es dato almacenado, nunca calculado.** Medido: **3 de 22 no se pueden derivar** del
nombre (`Coordinación STI · Lima` → `dti-coord-sti-lima` abrevia *Coordinación*). La unión se
hace por `identifier` del rol = valor EXACTO de `serviceDeskTeam`, acotada por
`subtype=dti-service-desk-team`. Ambas propiedades son core e indexadas → **cero cambios de
schema**.

## Lo aplicado

| # | Objeto | Método | Path |
|---|---|---|---|
| 1 | Recurso `7b4e1c2d-…` | PATCH add | `capabilities/configured/references` — referencia simulada `ri:group`, `direction=objectToSubject` |
| 2 | idem | PATCH add | `schemaHandling/objectType` → **id 497** `entitlement/group` sobre `ri:groupOfUniqueNames`, baseContext `ou=groups`, scope `one`, filtro `cn` empieza por `dti-` |
| 3 | idem | PATCH add | `schemaHandling/associationType` → **id 501** `ri:group`, `tolerant=false` |
| 4 | Template `855caaca-…` | PATCH add | `mapping` `T-autoassign-ar-dti-team-from-serviceDeskTeam` |
| 5 | Rol `d71a0001-…` | POST | `AR-DTI-Team-activos-digitales` |
| 6 | Tareas `d71a0003/0005` | POST | recon de grupos + recompute acotado |

**`tolerant=false` ratificado por Alberto**: MidPoint es autoritativo sobre la pertenencia. Es
seguro por construcción — el filtro `cn=dti-*` deja fuera cualquier grupo futuro no gobernado,
que queda invisible para la asociación y por tanto intocable. Medido: los 22
`groupOfUniqueNames` del árbol entero son `dti-*`; cero `groupOfNames`, cero `posixGroup`.

## 🔴 El ACL que faltaba — la causa real del fallo

El diseño era correcto desde el principio; **el directorio le negaba la escritura**. Había reglas
con `write` para `ou=people`, `ou=org` y `ou=alumni`, pero los grupos caían en el catch-all
`{5}to *`, donde `cn=midpoint` solo tenía `read`:

```
remove:uniqueMember=uid=200810434 de cn=dti-soporte-ti → insufficientAccessRights (50)
```

`tolerant=false` **sí decidía bien** — lo intentó, y el log lo prueba. Añadido:

```ldif
olcAccess: {5}to dn.subtree="ou=groups,dc=upeu,dc=edu,dc=pe"
  by dn="cn=admin,dc=upeu,dc=edu,dc=pe" write
  by dn="cn=midpoint,ou=services,dc=upeu,dc=edu,dc=pe" write
  by dn="cn=keycloak,dc=upeu,dc=edu,dc=pe" read
  by dn="cn=rims-reader,ou=services,dc=upeu,dc=edu,dc=pe" read
  by * none
```

**El índice `{5}` es esencial**: las ACL se evalúan en orden y gana la primera que casa. Detrás
del catch-all no se aplicaría nunca. Backup previo en `/tmp/olcAccess-backup-20260903.ldif`.

## Tres trampas encontradas al ejecutar

1. **`displayName` no existe en `ShadowAssociationDefinitionType`.** Con él, el PATCH del
   `associationType` da **HTTP 500** (`ItemDeltaBeanToNativeConversion`). Va solo en el nivel
   superior del associationType.
2. **Una tarea con `<recomputation>` vacío recomputa a TODOS.** La del canario no llevaba
   `<objects>`, así que en vez de una persona procesaba las 65.661. Se detecta porque
   `lastRunStartTimestamp` avanza y no termina. Suspendida sin modificar a nadie; sustituida por
   una acotada con `inOid`.
3. **Una tarea nueva nace `suspended` y `/run` la rechaza** («cannot be run now… State is
   SUSPENDED»). El orden correcto es **`resume` y después `run`**; si no, queda `RUNNABLE` con
   `lastRunStartTimestamp = nunca` y `node = ninguno`, que parece atasco y no lo es.

## Criterios verificados en vivo

| Criterio | Evidencia |
|---|---|
| 1 · mover de grupo sin tocar LDAP | expulsado del grupo ajeno; `dti-soporte-ti` volvió a 11 |
| 2 · reconstruir lo borrado a mano | `uniqueMember` repuesto tras borrarlo |
| 3 · 22 grupos / 64 membresías | **22 / 64** |
| 4 · `memberOf` correcto | DN exacto, nunca comodín |
| 5 · sobreviven `serviceDeskTeam`/`Level` | `Activos Digitales` / `N1` |

Recurso íntegro tras los 3 PATCH: `version 266`, **1.146 `xsd:element`**, 108 `complexType`,
testConnection 14/14 `success`, objectTypes 62/447/461 intactos.

**El criterio 2 exigió un miembro temporal**: `groupOfUniqueNames` no admite quedarse sin
`uniqueMember` y el grupo canario tiene una sola persona. Se usó a alguien de soporte-ti y se
retiró después. **9 de los 22 equipos son de una sola persona** y tendrán la misma limitación si
hay que probarlos aisladamente.

## Pendiente

- Desplegar los 21 equipos restantes desde `mapa-equipo-slug-VERIFICADO.json` (contrastado
  contra 4 fuentes, 64/64 — no re-derivar).
- Activar las dos tareas programadas, hoy `suspended`.
- Capa institución UPeU (ADR-054). Generalizable a `canonico/` cambiando el filtro `cn=dti-*` y
  el prefijo del `subtype`.

---

# Despliegue de los 22 equipos — COMPLETADO el 03-sep-2026

## Resultado

```
personas verificadas una por una: 64
EN EL GRUPO CORRECTO            : 64
incorrectas                     : 0
con equipo pero sin grupo       : 0
```

22 grupos · 64 membresías · 64 personas distintas (nadie en dos grupos) · `memberOf` 64/64.

**La verificación es cruzada, no de forma**: para cada una de las 64 personas se comparó el
grupo real en LDAP contra su `serviceDeskTeam` real en MidPoint, resuelto por el mapa
verificado. Que los totales cuadren no basta — podrían cuadrar estando todas cruzadas.

## Lo desplegado

- **22 roles** `AR-DTI-Team-*` (OIDs `d71a0001-0000-4000-a000-d71a000000NN`), todos HTTP 201.
- **Tareas activas** (`RUNNABLE`): `recon-ldap-dti-groups-daily` (3:30) y
  `recompute-dti-teams-daily` (4:15, acotada por `q:org` al Org DTI con scope SUBTREE).
- Tareas de despliegue ya cerradas: `recompute-dti-64-despliegue-inicial`,
  `recompute-canario-dti-activos-digitales-ACOTADA`.
- **Eliminada** la tarea `CANARIO DTI grupos - recompute+reconcile` por llevar el bloque
  `<recomputation>` vacío: reanudarla habría recomputado a los 65.661 usuarios.

## Dos trampas más, encontradas al desplegar

4. **El `fullObject` de MidPoint 4.10 es JSON, no XML.** Buscar `<serviceDeskTeam>` devuelve 0;
   el atributo vive en `"extension":{"serviceDeskTeam":"..."}`. Tres consultas seguidas
   devolvieron 4, 2 y 0 personas en lugar de 64 — **números plausibles, no errores**, que es
   justo lo que hace peligroso un extractor roto. La forma fiable es trocear por `{"user":` y
   parsear cada objeto con un decodificador JSON, no con expresiones regulares.
5. **El SSH a PROD empezó a fallar de forma intermitente** tras el volumen de conexiones de la
   sesión (deniega y entra al tercer intento). Todo script que consulte PROD en cadena debe
   llevar reintentos, o interpretará una denegación transitoria como un cero real.

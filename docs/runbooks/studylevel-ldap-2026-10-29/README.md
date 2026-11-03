# Publicar el nivel de programa en el LDAP — `scibackStudyLevel`

**Estado: PREPARADO, NO APLICADO** · 29-oct-2026
**Encargo:** punto 3 de `centro-medico-upeu/.../2026-10-29-midpoint-vigencia-matricula-ldap.md`
**Consumidor:** HIS del Centro Médico (OpenMRS), para la tarifa del paciente al admitirlo.

## Por qué este es el punto barato

El dato **ya existe en el foco**: `extension/sciback:studyLevel`, poblado en **17.813 de 17.814**
estudiantes (99,99 %, medido en PROD el 29-oct). No hay que calcular nada ni tocar Oracle: solo
publicarlo. No depende de la decisión de los días de gracia, ni toca el user-template (que es de
la sesión de correlación M365/EntraID).

## Por qué un atributo propio y no uno estándar

Ni **eduPerson 202208** (8 valores de `eduPersonAffiliation`, ninguno distingue nivel) ni
**SCHAC 1.6.0** (`.1`–`.21`) tienen nivel de estudio. Verificado contra `iga-canonical-standards`.
Por eso va al arco propio `1.3.6.1.4.1.47378`, OID **`.1.17`** (último usado: `.1.16`).

## Vocabulario (medido, no inventado)

| Valor en Oracle | n | Se publica como |
|---|---|---|
| Pregrado | 15.173 | `pregrado` |
| Segunda Especialidad | 978 | `segunda-especialidad` |
| Posgrado | 603 | `posgrado` |
| CEPRE | 462 | `cepre` |
| Idiomas | 238 | `idiomas` |
| Conservatorio de Música | 234 | `conservatorio` |
| Doctorado | 61 | `doctorado` |
| Diplomatura | 35 | `diplomatura` |
| Tesis | 27 | `tesis` ⚠️ |
| `pregrado`/`posgrado`/vacío (sucios) | 3 | los absorbe el `toLowerCase`, el vacío → ausente |

⚠️ **«Tesis» no parece un nivel sino un estado de matrícula.** Preguntar antes de publicarlo como
si lo fuera; de momento se mapea tal cual para no perder el dato.

**Sin default a propósito:** un nivel no previsto deja el atributo AUSENTE. Imputar un nivel
decidiría mal una tarifa de salud — mismo criterio que `scibackCampusCode`, y el precedente en
contra es el `getOrDefault(v,'LIMA')` del campus.

## Orden de aplicación

1. **Schema LDAP** — `../../upeu/ldap/rims-iga-contract/13-schema-studylevel.ldif`
   en **.168 y .169** (`cn=config` no replica). Re-verificar el ordinal `{1}` de `upeuPerson`
   antes: el re-add mueve el valor al final y el ordinal cambia.
2. **Purge schema + test connection** del resource `LDAP-IdentityCache-UPeU` en MidPoint,
   o el outbound falla con *«Definition of attribute not found in object class»*.
3. **PATCH del resource** — `patch-resource-studylevel.json` (objectType `[62]`, account/default).
   **Nunca PUT:** el `<schema>` cacheado se perdería y el resource quedaría `broken`.
4. **Canario**: recompute de UNA persona de pregrado y verificación en LDAP.
5. **Lote**: reconcile del resource LDAP — **fuera de 11:00–16:00 UTC** (acordado con la sesión de
   correlación M365: no se puede acotar, recorre ~58.900 cuentas) y con simulación previa.

## Verificación

Antes (debe dar 0):
```bash
source ~/.secrets/ldap-upeu.env && ldapsearch -x -LLL -H "ldap://192.168.15.168:389" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASS" -b "ou=people,$LDAP_BASE_DN" "(scibackStudyLevel=*)" dn | grep -c "^dn:"
```

Después del lote, por nivel (esperado ≈ la tabla de arriba):
```bash
source ~/.secrets/ldap-upeu.env && for N in pregrado posgrado doctorado segunda-especialidad cepre idiomas conservatorio diplomatura tesis; do printf "%-22s " "$N"; ldapsearch -x -LLL -H "ldap://192.168.15.168:389" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASS" -b "ou=people,$LDAP_BASE_DN" "(scibackStudyLevel=$N)" dn 2>/dev/null | grep -c "^dn:"; done
```

Control de no-regresión — el total con nivel no puede superar a los `student` vigentes:
```bash
source ~/.secrets/ldap-upeu.env && ldapsearch -x -LLL -H "ldap://192.168.15.168:389" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASS" -b "ou=people,$LDAP_BASE_DN" "(&(scibackStudyLevel=*)(!(eduPersonAffiliation=student)))" dn | grep -c "^dn:"
```
Debe dar **0**: nadie con nivel y sin matrícula vigente.

## Rollback

El atributo es aditivo y nadie lo consume aún. Para revertir: `PATCH` con `modificationType:
delete` del mismo elemento, y el atributo queda huérfano en el schema (inocuo, se deja).

## Alternativa que conviene considerar ANTES de aplicar esto

Publicar el **nivel** obliga al HIS a conocer la regla de negocio del seguro («¿cubre a CEPRE?»).
La alternativa estándar es publicar el **derecho** con `eduPersonEntitlement` (eduPerson `.1.7`,
*«URI que indica derecho de acceso»*), que **ya está disponible** en la objectClass `eduPerson` que
las personas llevan — es decir, **sin tocar `cn=config` en ningún nodo**:

```
eduPersonEntitlement: urn:mace:upeu.edu.pe:entitlement:centro-medico:seguro-estudiante
```

| | Nivel (`scibackStudyLevel`) | Derecho (`eduPersonEntitlement`) |
|---|---|---|
| Schema LDAP nuevo | sí, en .168 y .169 | **no hace falta** |
| Quién decide quién tiene seguro | el HIS | **el IGA** |
| Cambiar la cobertura | tocar el HIS | tocar un rol en MidPoint |
| Datos expuestos (Ley 29733) | nivel académico de 17.814 personas | solo el derecho |
| Estándar | atributo propio | eduPerson puro |

La skill `iga-canonical-standards` recomienda explícitamente `eduPersonEntitlement` para esto
(*«Mejor que exponer pertenencia a grupos»*, regla 12: no inventar atributos si el estándar cubre).

**No son excluyentes:** el nivel sirve para reportería y el entitlement para la decisión de tarifa.
Pero si solo se va a aplicar uno, el entitlement es más barato, más estándar y expone menos.

---

# Anexo — vigencia académica (puntos 1 y 2 del encargo), medido el 3-nov-2026

La gracia de matrícula **ya está decidida y desplegada**: N = 90 días, en PROD desde el 30-oct
(schema canónico **v35**). No hay que calcular nada en el recurso LDAP: los dos atributos existen
en el foco, namespace `urn:sciback:midpoint:person`, `xsd:string` `YYYY-MM-DD`, monovaluados.

| Ítem del foco | `m_ext_item` | Qué es |
|---|---|---|
| `studentEnrollmentLastEnd` (G1) | **348** | Fin **real** de matrícula, con memoria. Sube con la fuente y no baja cuando un semestre sale del horizonte del feed |
| `studentEnrollmentEffectiveEnd` (G2) | **347** | Fin **efectivo** = G1 + 90 días. Si hay otro vínculo vivo (215/216), G2 = G1 sin gracia. **Este es el que se publica como vigencia académica** |
| `liveAffiliationStudent` | **217** | El vínculo vivo. Es lo que sostiene `eduPersonAffiliation=student` |

**No usar `terminationDateStudent` como fin efectivo:** retrocede cuando un semestre sale del
horizonte del feed (medido por la sesión de la gracia: 21 de 46 casos tenían el 30-jun en vez del
28-oct).

## 🔴 Un G2 futuro NO prueba matrícula viva — medido

| | |
|---|---|
| Users con G1 y G2 poblados | **30.240** (incluye egresados: los atributos guardan memoria) |
| Users con `liveAffiliationStudent` (217) | **18.477** |
| G2 poblado **sin** 217 | **11.767** |
| **G2 en el futuro y sin 217** | **75** |

Si el HIS decidiera la cobertura solo con «`studentEnrollmentEffectiveEnd` ≥ hoy», **esas 75
personas pasarían como aseguradas sin tener matrícula viva**. Salieron del feed y G2 conserva la
memoria.

**Consecuencia para el diseño del outbound:** publicar G2 **condicionado a que exista el 217**, no
G2 crudo. Así el atributo del LDAP no puede mentir por sí solo y el HIS puede comparar una sola
fecha sin conocer la regla. La alternativa —publicar G2 siempre y exigir al HIS que además
compruebe `eduPersonAffiliation=student`— funciona igual, pero reparte la regla entre dos sistemas.

## Avisos de despliegue

- **`main` todavía no tiene estos atributos.** Están en PROD y en la rama local
  `fix/gracia-matricula-90` (sin push): `canonical/schemas/sciback-person-v1.0.xml` y
  `UserTemplate-Person-Base.xml`, commits `25a5f5f` y `27c0461`. **Leer la definición de PROD por
  REST, nunca la de `main`.**
- Igual que `studyLevel`: **nada en el recurso LDAP hasta cerrar F3** (4.11.0, el `connectorRef`
  vuelve a cambiar al LDAP 3.10).

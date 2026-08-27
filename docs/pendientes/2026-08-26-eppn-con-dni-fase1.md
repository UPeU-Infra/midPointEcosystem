# El ePPN llevaba el DNI — CORREGIDO (fases 1 y 2 aplicadas)

**26-ago-2026 · fases 1 y 2 APLICADAS en producción y verificadas**

Origen: observación levantada desde el proyecto `devsupeu`/Indico
(`prompt-midpoint-ldap.md`). Verificada aquí punto por punto contra producción.

## El defecto, en una frase

`personalNumber` guarda el `COD_APS` crudo de Trabajadores —que en parte del personal **es el
DNI**— y de ahí beben **dos** atributos del directorio: `eduPersonPrincipalName` y
`schacPersonalUniqueCode`. El `name`, en cambio, ya aplica la política correcta
(`A-name-canonical-codigo-or-codaps`: código académico si existe, `COD_APS` como respaldo).

Un solo defecto, dos atributos contaminados. La corrección canónica es la que el propio modelo
de la casa declara: **`eduPersonPrincipalName ← uid@upeu.edu.pe`**.

## Qué dice el estándar (verificado, no de memoria)

- eduPerson 202208 **no prohíbe** que el localpart sea un documento: exige unicidad, scope
  institucional y no reasignabilidad, y un DNI cumple las tres. **No es una violación del
  estándar.**
- **Sí es desviación del modelo canónico de UPeU**, cuya tabla de mapeo declara `ePPN ← uid`.
- El riesgo de privacidad **existe pero hoy no se materializa**: el modelo marca
  `schacPersonalUniqueID` (el DNI) como *no publicable* a los SPs, y REFEDS R&S obliga a liberar
  ePPN **o** ePUID. Si el ePPN llevara el DNI y se publicara, el documento legal saldría a
  Scopus, EBSCO y compañía. Medido: el scope `academic-databases-eduperson` existe pero
  **ningún cliente lo tiene asignado**.

## Alcance medido

| | |
|---|---|
| Users con `name` ≠ `personalNumber` | **4.073** (3.943 activos) |
| …con cuenta en el LDAP | 4.618 shadows: **2.949** en `ou=people` + **1.669** en `ou=alumni` |
| Entradas LDAP cuyo ePPN es el DNI teniendo `uid` correcto | 2.543 |
| Entradas cuyo **`uid` mismo es el DNI** | **1.782** (935 staff, 758 faculty, 8 student) |

Esa última fila es la que el informe original no separaba: **cambiar la fuente del mapping no
las arregla**, porque su `name` ya es el DNI. Su corrección exige renombrar identidades — el
*rename hell* del que advierte el libro, y lo que ya se abortó el 17-jul.

## Consumidores del ePPN (medido)

Muchos menos de los temidos:

| Consumidor | ¿Depende del ePPN? |
|---|---|
| Proveedores académicos | **No** — ningún cliente tiene el scope que lo publica |
| RIMS | Recibe el claim, pero **ancla por `eduPersonUniqueId`** (sus shadows son `15922@upeu.edu.pe`) |
| Keycloak | No federa LDAP; lo usa como regex `.+@upeu\.edu\.pe`, que un cambio de valor sigue cumpliendo |
| Koha | No lo usa (ancla en código y `externalSystemId`) |
| LDAP | Solo dos binds de lectura: `cn=keycloak` y `cn=rims-reader` |

## Fase 1 — APLICADA

`eduPersonPrincipalNamePrior` es lo que exige eduPerson al cambiar un ePPN, y **estaba a cero**.
Se añadió un mapping en **ambas ramas** del resource LDAP (v257 → **v259**) que lo calcula desde
la fuente vieja, solo cuando difiere de la nueva:

```groovy
if (pn == '' || nm == '' || pn == nm) return null
return pn + '@upeu.edu.pe'
```

Poblado por recompute **sin reconcile** (suficiente y ~30× más rápido que con él):

| Rama | Poblados |
|---|---|
| `ou=people` | **2.946 / 2.949** |
| `ou=alumni` | **1.666 / 1.669** |
| **Total** | **4.612 / 4.618 — 99,87 %** |

Integridad verificada en cada paso: `xsd:element` 2.292 sin cambios, `attributes` 58→59→60,
`connectorRef` intacto, test de conexión 15/15.

**Los 6 que faltan no son un fallo del mapping: su recompute se cuelga** (>2 min sin responder).
Uno de ellos, `200610808`, ya tenía su propia task de diagnóstico anterior a esto. Pendiente de
explicar aparte.

## Fase 2 — APLICADA

Dos cambios, no uno (el ePPN sale del template; el `schacPersonalUniqueCode` se calcula
directamente en el resource):

| Objeto | Cambio | Versión |
|---|---|---|
| `UserTemplate-Person-Base` | `C-eppn-from-name-codigo-institucional`: fuente `personalNumber` → `name` | v127 → **v128** |
| Resource LDAP, ramas `default` y `alumni` | `schac-unique-code-from-name-codigo-institucional`: misma sustitución | v259 → **v263** |
| Ambas ramas | **`tolerant=false`** en `schacPersonalUniqueCode` | idem |

Desplegado con simulación previa (`executionMode: preview`, que confirmó `MODIFIED` solo en el
foco y el shadow LDAP, y `UNMODIFIED` en Koha, Entra y Oracle), canario, lote de 50 y masivo de
4.038 en 4 hilos.

### Resultado medido sobre el árbol completo (78.577 entradas)

| | Antes | Después |
|---|---|---|
| ePPN = `uid` | 94,1 % | **100,0 %** (78.571) |
| ePPN = DNI | 2.543 | **1** |
| `schacPersonalUniqueCode` duplicado | 495 | **0** |
| Con `eduPersonPrincipalNamePrior` | 0 | **4.614** |

El DNI salió del identificador federado; sigue —y debe seguir— en `schacPersonalUniqueID`.

Nota de alcance: la medición inicial (50.070) era solo de `ou=people`; el árbol completo son
78.577 entradas. El alcance real era mayor y aun así quedó al 100 %.

## Dos trampas que costaron caro, y que valen para cualquier cambio futuro

1. **`strong` sobre un target multivalor AÑADE, no sustituye.** `schacPersonalUniqueCode` es
   multivalor y no declaraba `tolerant`, así que por defecto era tolerante: el canario quedó con
   el DNI **y** el código. Sin ese canario, las 4.038 fichas habrían salido duplicadas. El ePPN se
   libró solo por ser *single-value* en el esquema, no por diseño. (Es el patrón PM10 ya conocido.)
2. **Ningún recompute es "puramente aditivo".** Aplica *todos* los mappings, no solo el que se
   acaba de tocar. El poblado de la fase 1 —que se describió como inocuo— reescribió de paso el
   `schacPersonalUniqueCode` de **495 personas**, añadiéndoles el DNI. La fase 2 los limpió, pero
   la lección queda: al recomputar en masa hay que revisar **qué más** escribe ese objeto.

## Lo que sigue pendiente

- **1.782 personas cuyo `uid` ya es el DNI.** Este cambio **no las arregla**: su `name` es el
  documento. Exige renombrar identidades (*rename hell*), lo que se abortó el 17-jul. Decisión
  aparte.
- **6 personas cuyo recompute se cuelga** (>2 min sin responder), una con task de diagnóstico
  propia anterior a esto. Son las que quedan sin corregir (1 con ePPN = DNI y 5 sin clasificar).

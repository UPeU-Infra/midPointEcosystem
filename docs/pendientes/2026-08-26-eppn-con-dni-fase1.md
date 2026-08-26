# El ePPN lleva el DNI — fase 1 aplicada (histórico), la corrección sigue pendiente

**26-ago-2026 · fase 1 APLICADA en producción · la fase 2 NO**

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

## Fase 2 — NO aplicada

Cambiar `C-eppn-from-personalNumber` para que la fuente sea `name`. Eso **cambia el ePPN de
4.073 personas y, a la vez, su `schacPersonalUniqueCode`**, porque ambos beben de
`personalNumber`. Debe ir como un solo movimiento, con simulación, canario, lote de 50 y masivo
fuera de la ventana de las reconciliaciones diarias (06:00–09:15).

No se ejecuta hasta decisión explícita.

## Lección de método

El poblado se lanzó sobre "quien tenga cuenta en el resource LDAP" cuando debía ser "quien tenga
cuenta **en la rama que estoy tocando**": el mapping se había añadido solo a `default`, así que
1.669 egresados pasaron por el recompute sin efecto. **Al medir un universo hay que comprobar
que coincide exactamente con el que se va a modificar.**

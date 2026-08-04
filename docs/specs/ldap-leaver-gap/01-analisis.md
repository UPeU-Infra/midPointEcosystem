# Leaver gap del resource LDAP — análisis técnico y opciones

**Fecha:** 2026-08-03 · **Estado:** análisis, **nada ejecutado** · **Requiere decisión de arquitectura**
**Origen:** `docs/runbooks/bajas-trabajadores-sin-procesar-2026-08-03/RUNBOOK.md` (160 ex-trabajadores
con accesos vivos) y `docs/runbooks/ldap-dualshadow-dedup-265/RUNBOOK.md` (dual-shadow).

## El problema en una línea

El IGA **puede dar accesos pero no puede quitarlos** en `LDAP-IdentityCache-UPeU`
(`7b4e1c2d-…`) — ni moviendo la entrada ni deshabilitándola.

## Diagnóstico medido (03-ago)

### 1. El DN es fijo por objectType

```
account/default → 'uid=' + name + ',ou=people,dc=upeu,dc=edu,dc=pe'
account/alumni  → ou=alumni   (declarado "rama de CONSULTA, no de autenticacion")
generic/ou
```

Pasar de `AR-LDAP-Person` a `AR-LDAP-Alumni` cambia de objectType **y por tanto de DN**.
MidPoint tendría que renombrar/mover la entrada, y responde
`Operation not supported for COD(inetOrgPerson + eduPerson + …)`.

### 2. No hay capability de activation

Capabilities configuradas en el resource: `update`, `addRemoveAttributeValues`, `delete`,
`create`, `read`, `script`. **No hay `activation` ni `administrativeStatus`.** Sin bloque
`<native>` cacheado. El propio XML lo documenta como *"leaver gap"*.

### 3. Y no se puede añadir sin tocar OpenLDAP

El camino canónico de Evolveum para OpenLDAP es mapear `activation/administrativeStatus` a
`pwdAccountLockedTime` (overlay **ppolicy**). Medido en el directorio real:

```
overlays cargados: memberof · refint · sssvlv · syncprov     ← ppolicy NO está
módulos:  back_mdb · memberof · refint · sssvlv · syncprov   ← ppolicy NO está
entradas con pwdAccountLockedTime: 0
objectClass del sujeto: inetOrgPerson, eduPerson, schacPersonalCharacteristics,
                        schacEntryMetadata, midPointPerson, upeuPerson   ← sin pwdPolicy
```

**Conclusión: el atributo no existe y el overlay que lo provee no está cargado.** No es un
PATCH al resource: es un cambio en la plataforma LDAP.

## Por qué esto no es una tarea de configuración

Cualquier opción cruza el límite de MidPoint y toca la plataforma o el contrato con los
consumidores:

| Opción | Qué implica | Riesgo |
|---|---|---|
| **A. Cargar overlay `ppolicy`** + mapear `activation` → `pwdAccountLockedTime` | Modificar `cn=config` en **los 2 nodos** con replicación N-way; ppolicy además activa políticas de password | Medio-alto: mal configurado afecta la **autenticación de todos** |
| **B. Atributo de estado ya existente** (p. ej. `schacExpiryDate`) | Solo MidPoint; barato | **Puede ser cosmético**: un atributo no bloquea nada por sí solo |
| **C. Permitir `delete`** de la entrada al cesar | El resource ya tiene capability `delete`, pero está **bloqueado por diseño** (ver runbook dual-shadow) | Alto: irreversible, y borra la identidad del CRAI/InOut |
| **D. No mover de OU**: alumni en `ou=people` con distinto `eduPersonAffiliation` | Rediseño del modelo LDAP | Alto: cambia el DIT que ya consumen 4 sistemas |

### La pregunta que decide, y que no es técnica

**¿Qué comprueban realmente los consumidores?** Deshabilitar en LDAP solo corta el acceso si
quien autentica lo respeta:

- **WiFi 802.1X EAP-TLS** — valida el **certificado**, no el bind LDAP. Es muy posible que
  `pwdAccountLockedTime` **no corte nada** ahí; habría que revocar el certificado (EJBCA).
- **InOut (aforo CRAI)** — lee atributos LDAP; depende de si filtra por estado.
- **RIMS** — bind propio.
- **Apps con bind** — sí respetarían el bloqueo.

Sin responder esto, cualquier fix puede dar **falsa sensación de cierre**: la cuenta figura
deshabilitada y la persona sigue entrando al WiFi con su certificado.

## Recomendación

1. **Primero medir el contrato de cada consumidor** (qué comprueba WiFi/InOut/RIMS al
   autenticar y autorizar). Es lo que decide entre A, B, C y D — y hoy no está documentado.
2. **Diseñar el ciclo de vida en el directorio** de forma explícita: qué significa "cesado"
   en LDAP, en qué rama vive, qué atributo lo marca y quién lo respeta.
3. **Recién entonces** tocar el resource, con canario y ventana.

Mientras tanto, el corte de acceso efectivo para un caso urgente **no pasa por MidPoint**:
es revocar el certificado en EJBCA (WiFi) y/o la baja en cada aplicación.

## Lo que NO se debe hacer

- Aplicar un PATCH al resource "para que deshabilite" sin el overlay: no hay atributo destino.
- Cargar `ppolicy` en producción sin ventana ni prueba en los 2 nodos: afecta autenticación.
- Dar por resuelto el leaver gap con un cambio que solo escribe un atributo que nadie lee.

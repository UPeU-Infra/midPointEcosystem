# Canal ORCID self-service — RIMS → IGA (MidPoint)

**Estado:** DISEÑO (no aplicado) · **Fecha:** 2026-07-04
**Rama:** `feature/researcher-source-ingest`
**Skills:** `iga-canonical-standards` (IIA §1.3, eduPersonOrcid §3.1, eduPersonUniqueId como ancla de
correlación §11.4, NIST IAL §2), `midpoint-best-practices` (inbound-only, Reality vs Policy, resource REST)

---

## 0. Problema y decisión de dirección

El investigador registra su **ORCID** en el RIMS (UI self-service). MidPoint debe **gobernar** ese ORCID
y publicarlo a LDAP como `eduPersonOrcid` (outbound ya existente con validación MOD 11-2).

**Restricción arquitectónica clave:** ya existe un canal **MidPoint → RIMS vía SCIM**
(resource `RIMS-SciBack`, OID `09a81691-…895e`, dirección **saliente**: MidPoint empuja identidad a
`https://rims.upeu.edu.pe/scim/v2`, correlación por `externalId = eduPersonUniqueId`). Ese canal
**NO sirve** para traer el ORCID porque va en sentido contrario (MidPoint es master, escribe; no lee).

**Decisión: canal INBOUND separado RIMS → MidPoint, patrón PULL.**
MidPoint lee un endpoint del RIMS mediante un **resource REST inbound (read-only)** y correla por
**ePUID (`eduPersonUniqueId`)**. Es el patrón canónico: el dato que el titular afirma (self-asserted,
IAL1) fluye hacia el master, que lo valida y decide si lo publica.

### Por qué PULL y no PUSH (RIMS empuja a MidPoint por REST)

| Criterio | PULL (MidPoint lee RIMS) — RECOMENDADO | PUSH (RIMS escribe a MidPoint REST) |
|---|---|---|
| Master de identidad | MidPoint decide cuándo y qué ingiere (Reality vs Policy) | RIMS tendría que conocer OIDs/credenciales de escritura de MidPoint |
| Superficie de ataque | RIMS solo expone lectura de un feed acotado | Abrir REST de escritura de MidPoint a otro sistema |
| Idempotencia / reproceso | Reconciliación nativa MidPoint (reejecutable) | RIMS debe implementar reintentos/dedupe |
| Consistencia con el resto | Igual que LAMB/Entra (MidPoint lee sus fuentes) | Excepción al patrón |
| Acoplamiento | RIMS no sabe de MidPoint | RIMS acoplado al modelo MidPoint |

PUSH solo se justificaría si se requiriera latencia inmediata (evento). Para ORCID (dato de baja
frecuencia) el PULL programado (p. ej. cada 6–24 h) es suficiente y más limpio.

---

## 1. Arquitectura del canal (PULL)

```
Investigador ──UI──► RIMS (self-service ORCID)
                       │  valida MOD 11-2 en el RIMS (front + back)
                       │  guarda orcid + ancla ePUID por usuario
                       ▼
             RIMS expone feed READ-ONLY:
             GET /scim/v2/Users?filter=orcid pr        (o vista/endpoint dedicado)
                       ▲
                       │  (token OAuth2 client_credentials, ya usado por el canal saliente)
   MidPoint resource REST "RIMS-ORCID-INBOUND" ──lee──┘
     correla por externalId = eduPersonUniqueId (ePUID)
     inbound weak-pero-autoritativo-para-self-service → sciback:orcid
                       ▼
     Object template / outbound existente ──► LDAP eduPersonOrcid (revalida MOD 11-2)
                       ▼
              Keycloak lee LDAP → assertion SAML/OIDC (eduPersonOrcid .1.16)
```

---

## 2. Qué implementa el RIMS (para pasar a su chat)

1. **UI self-service ORCID** en el perfil del investigador:
   - Campo ORCID con máscara `0000-0000-0000-0000`.
   - **Validación MOD 11-2 (ISO 7064) en el front Y en el back** del RIMS antes de persistir. No
     aceptar un ORCID con checksum inválido (evita basura aguas abajo).
   - **Recomendado (mejor IAL):** botón "Verificar con ORCID" que haga el flujo OAuth de ORCID
     (authenticate) para confirmar que el titular controla ese ORCID → sube el proofing de IAL1
     (self-asserted) a algo verificado. Si se implementa, marcar el registro como `orcidVerified=true`.
2. **Persistir por usuario:** `orcid` (formato `0000-0000-0000-0000`) + su **ancla de correlación
   `eduPersonUniqueId`** (el mismo ePUID que MidPoint ya escribió al RIMS por el canal SCIM saliente,
   campo `externalId`). Opcional: `orcidVerified`, `orcidUpdatedAt`.
3. **Exponer un feed de lectura** que MidPoint pueda consultar:
   - Opción A (preferida, reusa lo existente): endpoint SCIM `GET /scim/v2/Users` filtrable, incluyendo
     `externalId` (=ePUID) y un atributo/extension `orcid` en el recurso User. MidPoint filtra
     `orcid pr` (present).
   - Opción B: endpoint dedicado `GET /api/iga/researcher-orcids` que devuelva `[{ epuid, orcid,
     orcidVerified, updatedAt }]`. Más simple de gobernar/permisar (solo lectura, solo estos campos).
   - **Recomendación: Opción B** — feed mínimo, dedicado, read-only, sin exponer todo el User SCIM.
4. **Autenticación del feed:** reutilizar el realm/cliente OAuth2 de Keycloak (`keyid.upeu.edu.pe`
   realm `upeu`) con un **scope de solo lectura** distinto del `scim:write` que usa el canal saliente
   (p. ej. `iga:orcid:read`). El cliente MidPoint usa `client_credentials` (igual mecánica que el
   resource SCIM actual).
5. **Semántica de borrado:** si el investigador borra su ORCID en RIMS, el feed debe reflejarlo
   (ausencia o `orcid=null`) para que MidPoint pueda retirarlo. Definir si RIMS soporta "tombstone".

---

## 3. Qué implementa el IGA (MidPoint)

1. **Nuevo resource REST inbound `RIMS-ORCID-INBOUND`** (separado del `RIMS-SciBack` saliente; no
   mezclar direcciones en un resource). Connector REST/scripted (mismo ConnId scripted REST que ya usa
   `RIMS-SciBack`, o el connector REST genérico), configurado contra el feed §2.3-B.
   - `kind=account`, `intent=orcid-feed`.
   - `focus/type = UserType`, **sin archetypeRef** (no crea personas).
2. **Correlación por ePUID:**
   - Atributo del feed `epuid` → correla contra `UserType` cuyo `extension/sciback:eduPersonUniqueId`
     (o el path canónico del ePUID en el schema) iguala. El resource saliente ya usa
     `$focus/extension/sciback:eduPersonUniqueId` como `externalId` → simetría perfecta.
3. **Inbound `orcid`:**
   - `source = orcid` del feed → `target = extension/sciback:orcid`.
   - **Validación MOD 11-2 en el inbound** (defensa en profundidad; el mismo script del resource CSV
     §F y del outbound LDAP). Descartar si inválido.
   - **Strength:** ver §4 (decisión de precedencia self-service vs CSV DGI).
4. **Reactions:** `linked`/`unlinked` → synchronize/link; `unmatched` → **no-op** (ePUID sin foco =
   registro huérfano en RIMS; informar, no crear).
5. **Task de import/reconciliation** programada (cada 6–24 h) o disparada por webhook si RIMS avisa.
6. **Publicación a LDAP:** ninguna acción nueva — el outbound `eduPersonOrcid` (LDAP
   `ldapidentitycacheupeu`) ya existe con revalidación MOD 11-2. Al poblarse `sciback:orcid`, se publica
   solo.

---

## 4. Validación MOD 11-2: dónde (respuesta: en los TRES puntos, defensa en profundidad)

| Punto | Rol | Obligatorio |
|---|---|---|
| **RIMS front** | UX inmediata; no molestar con round-trip | Recomendado |
| **RIMS back** | Impide persistir basura auto-declarada | **Sí** (gate de escritura del titular) |
| **IGA inbound** | El master no confía ciegamente en la fuente; normaliza a `0000-0000-0000-0000` | **Sí** |
| **IGA outbound LDAP** | Ya existe; última barrera antes de publicar `eduPersonOrcid` | **Sí (ya está)** |

Razón canónica: el ORCID es **self-asserted (NIST IAL1)**; el master valida forma (checksum) en la
frontera de ingesta y no delega la corrección al sistema aguas arriba. Si RIMS implementa la
verificación OAuth ORCID (§2.1), sube la confianza pero **no elimina** la validación de checksum del IGA.

---

## 5. Precedencia self-service (RIMS) vs respaldo (CSV DGI)

Ambos canales pueden aportar `sciback:orcid`. Decisión de IIA:

- **IIA primaria del ORCID = el investigador (self-service RIMS).** El titular es quien puede afirmar su
  ORCID con certeza (`iga-canonical §1.3`: "Afiliación/identificadores auto-afirmables → el usuario").
- **CSV DGI = respaldo (weak).** Por eso en `02-resource-renacyt-csv.xml` el inbound `orcid` es
  **`weak`** y el inbound RIMS es **la fuente que gana**.

Implementación de la precedencia (evitar que dos strong se pisen):
- CSV DGI: `strength=weak` (no sobrescribe si ya hay valor).
- RIMS inbound: `strength=strong` **con condición** — o bien strong incondicional (self-service manda),
  o strong solo si `orcidVerified=true` y weak si no verificado. **Recomendación:** RIMS strong
  incondicional (el titular es autoridad); DGI weak (solo llena vacíos). Documentar en ADR.

---

## 6. Correlación por ePUID — nota

- `eduPersonUniqueId` es el ancla correcta entre RIMS y MidPoint (ya lo es en el canal saliente).
- NO correlar por ORCID (circular: es el dato que se ingiere) ni por email (reasignable).
- El ePUID del RIMS proviene del propio MidPoint (canal SCIM saliente escribió `externalId`), así que la
  simetría está garantizada: MidPoint reconoce sus propios ePUID.

---

## 7. Pendientes

- **PENDIENTE 1:** decidir Opción A (SCIM filtrado) vs B (endpoint dedicado) del feed → recomendado B.
- **PENDIENTE 2:** ¿RIMS implementará verificación OAuth ORCID (sube IAL)? Si sí, definir `orcidVerified`.
- **PENDIENTE 3:** connector REST a usar en MidPoint (scripted REST existente vs connector REST genérico)
  y su OID.
- **PENDIENTE 4:** path canónico exacto del ePUID en el schema (`extension/sciback:eduPersonUniqueId`)
  y confirmación de que está poblado en todos los focos investigador.
- **PENDIENTE 5:** semántica de borrado/tombstone del ORCID en el feed RIMS.
- **PENDIENTE 6:** frecuencia de la task (6 h vs 24 h) según SLA del RIMS.

---

## 8. Reparto de trabajo (resumen)

| Componente | RIMS (para su chat) | IGA / MidPoint |
|---|---|---|
| UI self-service ORCID | ✅ | — |
| Validación MOD 11-2 front+back | ✅ | también en inbound (§4) |
| Persistir orcid + ancla ePUID | ✅ | — |
| Feed read-only (endpoint B) + scope OAuth `iga:orcid:read` | ✅ | consume |
| Resource REST inbound `RIMS-ORCID-INBOUND` | — | ✅ |
| Correlación por ePUID | expone ePUID | ✅ correla |
| Inbound → `sciback:orcid` (strong) | — | ✅ |
| Publicación LDAP `eduPersonOrcid` | — | ✅ (ya existe) |
| Verificación OAuth ORCID (opcional, +IAL) | ✅ (si se decide) | lee `orcidVerified` |

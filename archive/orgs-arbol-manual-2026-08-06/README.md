# Árbol organizativo manual — archivado 2026-08-06

**No importar a PROD.** Material histórico.

## Por qué se archiva

Decisión de Alberto (6-ago-2026): **la fuente de verdad del árbol organizativo es
Oracle LAMB**. El resource Org sincroniza y genera las orgs `AREA-NNN` — 353 en
producción.

Estos archivos describían un árbol diseñado a mano que **nunca llegó a existir en
PROD**, verificado con parsing XML real del inventario repo↔PROD:

| Org | Qué era |
|---|---|
| `UPeU` | la organización **raíz** |
| `Facultades`, `Rectorado`, `Posgrado`, `AreaTecnologia` | nodos troncales |
| `DIR-CRAI-JULIACA`, `DIR-CRAI-TARAPOTO` | unidades de campus |
| `COLEGIO-UNION` | unidad adscrita |

Mantenerlos versionados hacía que el repo describiera una estructura inexistente,
y cualquier sesión que lo leyera razonaba sobre datos falsos — es lo que ocurrió al
analizar el árbol de sedes. Ver memoria `medir-no-razonar`.

## Por qué NO se desplegaron en vez de archivarse

**Toda org proyecta una OU a LDAP.** Importarlas habría creado OUs nuevas sobre una
estructura que ya viene de Oracle, duplicando el árbol. Lección del incidente de
sedes del 5-ago (`identifier-org-gobierna-dn-ldap-2026-08-05`).

## ✅ Edición quirúrgica de los dos archivos MIXTOS — HECHA el 2026-08-06

Contenían orgs vivas en PROD junto a las ausentes, así que archivarlos enteros habría
borrado configuración en uso. Se retiraron **solo las ausentes**, conservando las vivas:

| Archivo original | Conserva (en PROD) | Retiradas → aquí |
|---|---|---|
| `upeu/orgs/050-GobiernoAdmin.xml` | **26** | 24 → `050-GobiernoAdmin-RETIRADAS.xml` |
| `upeu/orgs/campus/org-campus-lima-units.xml` | **6** | 8 → `org-campus-lima-units-RETIRADAS.xml` |

Sin pérdidas: 26+24=50 y 6+8=14, los totales originales.

Las 32 retiradas son cajas del organigrama oficial **sin área correspondiente en
`ELISEO.ORG_AREA`** (Defensoría, PRODAC, Misión, Gestión Curricular, Centro de Idiomas,
Conservatorio, CEPRE…). Por D2 del documento rector, ese hueco es un **gap que se reporta a
Planificación/GTH**, no estructura que MidPoint deba fabricar.

Con esto, `KNOWN_PENDING_FILES` del verificador queda **VACÍA**: el repo ya no describe
ninguna org que no exista en producción.

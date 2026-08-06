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

## Pendiente: dos archivos MIXTOS que NO se archivaron

Contienen orgs vivas en PROD junto a las ausentes, así que archivarlos enteros
habría borrado configuración en uso:

| Archivo | En PROD | Ausentes |
|---|---|---|
| `upeu/orgs/050-GobiernoAdmin.xml` | **26** | 24 |
| `upeu/orgs/campus/org-campus-lima-units.xml` | **6** | 8 |

Requieren edición quirúrgica: retirar solo las 32 orgs ausentes y conservar las 32
vivas. No se hizo aquí por ser una operación más delicada que un `git mv`.

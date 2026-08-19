# AR-Koha-Catalogador-Multisede — NUNCA DESPLEGADO, SUPERSEDED

**Archivado el 17-ago-2026. No importar a PROD.**

## Qué era

Un rol de aplicación (OID `e4537815-77de-43ec-a1a1-db1495fbb552`) que añadía el
subpermiso Koha `edit_any_item` al paquete técnico, para que el catalogador de
Biblioteca Lima (Jaime, `borrowernumber=150`) pudiera editar los ejemplares de la
Biblioteca CIA. Venía acompañado de un cableado en el mapping
`user-permissions-from-effective-koha-staff-role` del resource `koha-upeu`.

## Por qué se archiva

**El problema se resolvió en Koha, sin MidPoint.** El 17-ago-2026 se creó un
grupo de bibliotecas nativo (`library_groups`) llamado **«Campus Lima»** con la
opción *Limit item editing by group* activada y BUL + CIA como miembros.

Verificado en vivo tras el cambio:

```
Jaime  (BUL, catalogador) ->  BUL=1  BUJ=0  BUT=0  CIA=1
Lazaro (BUJ, control)     ->  BUL=0  BUJ=1  BUT=0  CIA=0
```

Es **mejor solución** que este rol en dos aspectos:

1. **Alcance acotado.** El grupo da exactamente BUL+CIA. `edit_any_item` es global
   por diseño de Koha: habría abierto las cuatro sedes, y además el borrado de
   ejemplares ajenos (`Koha::Item::safe_to_delete` pasa por el mismo chequeo).
2. **No toca el aprovisionamiento.** Los grupos de bibliotecas son configuración
   de Koha, no atributos del patron, así que MidPoint no interviene: no hay
   mapping que mantener, ni riesgo de PATCH sobre el resource, ni nada que se
   revierta en un recompute.

## Qué se revirtió

- El cableado en `upeu/resources/koha-upeu.xml` (commit `10376a5`) se retiró: el
  mapping vuelve a su forma anterior, sin `def extra` ni `+ extra`.
- Este XML se movió aquí. **Nunca llegó a importarse a PROD.**

## Lo que sigue siendo válido de su cabecera

El análisis del XML archivado documenta hallazgos verificados contra Koha 26.05
que conservan valor:

- Sin library groups, un catalogador queda **confinado a su propia sucursal**
  aunque `IndependentBranches=0` (`Koha::Patron::libraries_where_can_see_things`,
  rama `else` que hace `push $self->branchcode`). Confirmado como comportamiento
  intencionado en el [bug 40588](https://www.mail-archive.com/koha-bugs@lists.koha-community.org/msg648547.html).
- Cambiar la biblioteca de sesión («Set library») **no** amplía la edición de
  ejemplares: el chequeo mira `borrowers.branchcode`, no `userenv->{branch}`.
- Activar `IndependentBranches` **anularía** los library groups y dejaría
  `edit_any_item` inerte. Si algún día se evalúa activarlo, hay que rediseñar
  este caso antes, no después.

Contexto completo: `upeu-koha/context/32-separacion-por-sede-y-barcode-opac-2026-08-17.md`.

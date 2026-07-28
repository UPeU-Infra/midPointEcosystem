# 🔴 RETRACTACIÓN del commit `4e8d1a2` — el "bug del conector Koha" NO EXISTE

**Fecha de la retractación:** 2026-07-28
**Commit retractado:** `4e8d1a2` — *"feat(koha): acceso staff/intranet CIA (rol nuevo) + gap Jaime Lima detectado"* (2026-07-26)

---

## Qué afirmaba el commit (FALSO)

El mensaje de `4e8d1a2` cierra con este párrafo:

> *"Aplicado a producción vía PATCH REST + recompute. Verificado en producción: el shadow de
> Josué apunta a `patron_id=678` (no existe en Koha; su cuenta real es 23300) y el de Jaime a
> `patron_id=150` (pertenece a otra persona, Ethel Altez Ortiz, verificada intacta). **Las
> escrituras del conector no llegan a Koha real y no lo reportan como error** — pendiente de
> investigar alcance."*

**Nada de eso es cierto.**

## Por qué es falso

La verificación se hizo contra **`~/.secrets/koha-prod.env`** → `192.168.12.135` / `koha_bul`:
el **Koha VIEJO, archivado y retirado el 19-jul-2026**, que ya no está gobernado por MidPoint.
Sus `borrowernumber` son un universo independiente: que un ID coincida numéricamente con uno de
`koha_upeu` es **casualidad, no identidad**.

El Koha vigente — el que gobierna el resource `koha-upeu` (`e10a539a-cb7f-4c72-a19f-60f7f62e4b96`)
— es **`~/.secrets/koha-plus-prod.env`** → `192.168.12.136` / `koha_upeu`.

## La realidad, verificada contra `koha_upeu` el 2026-07-28

| | Lo que declaraba el shadow de MidPoint | Realidad en `koha_upeu` |
|---|---|---|
| Josué Agustín Llancachagua (`678`) | `library_id=CIA`, `flags=4`, 9 permisos | ✅ `branchcode=CIA`, `categorycode=staff`, `flags=4`, **9 permisos** |
| Jaime Vilcazán Quispe (`150`) | `flags=4`, 9 permisos | ✅ `Vilcazan Quispe, Jaime Aurelio`, `flags=4`, **9 permisos** |
| Patrons en branch `CIA` | 1 | ✅ 1 |

- El conector **escribió correctamente**: cada valor proyectado por MidPoint está en la base.
- **No** silencia errores. **No** hay `UPDATE` que falle sin reportar.
- **No** hay cruce de identidades ni shadows apuntando a la cuenta de otra persona.
- La sesión de MidPoint que investigó esto de forma independiente midió **99,85 % de shadows
  sanos, 0 duplicados, 0 cruces de identidad** — consistente con lo verificado aquí.

## Qué queda sin efecto

1. **La sospecha sobre `connector-koha`** (que haría `UPDATE ... WHERE patron_id=?` sin
   verificar *affected rows*). Infundada: el conector usa la **REST API** de Koha
   (`PUT /patrons/{uid}`) con manejo explícito de `404`, nunca SQL crudo.
2. **El handoff redactado para la sesión de MidPoint** pidiendo medir el alcance del "drift de
   correlación" y auditar el conector: parte de una premisa falsa.
3. **La conclusión de que "el fix de CIA no se había aplicado"**. Sí se había aplicado, desde el
   primer intento. El trabajo posterior de rehacerlo fue innecesario (aunque inocuo: convergió
   al mismo estado correcto).

## Qué SÍ es válido del commit `4e8d1a2`

Todo el resto. El cambio funcional es correcto y está verificado en producción:

- Rol `AR-Koha-Librarian-CIA-Admin` (`3e753452-dee7-4eee-822e-dd6a8c9539cb`).
- Bucket `costCenter=94` (CIA) en los outbounds `flags` y `user_permissions` de
  `upeu/resources/koha-upeu.xml`, con paquete técnico (`flags=4`) y **sin** superlibrarian —
  deliberado, para no romper la separación por campus que da `IndependentBranches`.
- `library_id` reconociendo `campusWorker=='CIA'` con prioridad sobre `campusStudent`.

## Regla operativa derivada

> Antes de afirmar que algo está roto en Koha, **imprimir el host/DB al que se está
> consultando** y confirmar que es `.136`/`koha_upeu` (`koha-plus-prod.env`). `koha-prod.env`
> *suena* a producción pero apunta al sistema archivado.

Ya existía una memoria de proyecto advirtiendo esta trampa exacta, escrita tras un incidente
idéntico el 26-jul. **Se volvió a caer en ella el 27-jul.** Costo: un diagnóstico falso de "bug
crítico" reportado al usuario, trabajo rehecho, este mensaje de commit erróneo en la historia
permanente, y un handoff inútil a otra sesión.

Contexto completo de la sesión:
`productos/koha/instituciones/upeu/upeu-koha/context/28-migracion-inei-526-y-correccion-diagnostico-2026-07-28.md`

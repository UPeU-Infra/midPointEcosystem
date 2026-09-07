# Snapshot y comparación del directorio Entra ID (M365 UPeU)

Copia fechada del directorio completo para poder **detectar cambios no autorizados** y
**reconstruir el valor anterior** de un atributo si algo se sobrescribe.

**Solo lectura.** Usa el `User.Read.All` que la app `MidPoint-UPeU` ya tiene concedido:
no hace falta pedir permisos nuevos ni tocar nada en M365.

## Uso

```bash
cd ~/proyectos/productos/iga/canonico/docs/runbooks/entra-snapshot
./snapshot-entra.sh
```

Captura el directorio (~7 min, ~76.000 cuentas), verifica la integridad y, si ya había un
snapshot previo, **muestra automáticamente qué cambió** y deja el detalle en un CSV.
Esa automatización es deliberada: un backup que hay que acordarse de comparar no se compara nunca.

Comparar dos snapshots cualesquiera a mano:

```bash
python3 comparar-snapshots.py <antiguo.json> <nuevo.json> [--csv salida.csv]
```

## Dónde vive y por qué ahí

`~/backups/entra-snapshots/` — **fuera del repositorio y fuera de `~/.cache`**.

- Fuera del repo porque son **datos personales de ~76.000 personas** (Ley 29733). Nunca a git,
  nunca a servicios de terceros. Carpeta en `700`, ficheros en `600`.
- Fuera de `~/.cache` porque esa carpeta es borrable por convención y esto no debe perderse.

## Qué es y qué NO es

| Sirve para | No sirve para |
|---|---|
| Saber qué cambió entre dos fechas | Restaurar con un clic |
| Reconstruir el valor anterior de un atributo | Recuperar atributos no escribibles |
| Dejar evidencia fechada para auditoría | Protegerte si nadie compara el después |

**Entra ID no tiene «snapshot/restore» nativo.** Lo único de Microsoft es la papelera de
usuarios borrados (30 días), que solo cubre eliminaciones, no cambios de atributos: si se
sobrescribe un `mail` o un `department`, Microsoft **no guarda el valor anterior en ningún sitio
recuperable**. Este fichero sería la única copia del «antes».

**Restaurar no es automático.** Habría que reescribir desde el snapshot con `PATCH /users/{id}`,
lo que exige `User.ReadWrite.All` — permiso que hoy la app **no tiene** (solo `User.Read.All`,
`Directory.Read.All`, `Group.Read.All`, `AuditLog.Read.All`). Es decir: el rollback sería tan
delicado como la operación que pretende arreglar. La red de seguridad real antes de escribir es
la **simulación de MidPoint**, no este backup.

## Primera comparación: 17-ago → 7-sep 2026

| | |
|---|---|
| Cuentas | 75.344 → **75.919** |
| Altas | 581 |
| Bajas | 6 |
| Cuentas modificadas | 2.358 (2.548 atributos) |

Desglose: 2.300 cambios de contraseña (normal), **159 correos** (cuentas que pasaron de sin buzón
a con buzón: aprovisionamiento, no manipulación), 29 nombres para mostrar, 24 nombres, 23
apellidos, **7 cambios de estado de cuenta** (4 deshabilitadas, 3 rehabilitadas) y **6 cambios de
UPN**.

Los cambios de estado y de UPN son los que conviene mirar en cada corrida: son los que alteran
quién puede entrar y con qué identidad.

## Cadencia sugerida

Mensual como mínimo, y **siempre antes y después de cualquier operación de escritura** sobre el
directorio. Los snapshots se acumulan por fecha en la misma carpeta; 43 MB cada uno.

## Contexto: hoy nadie escribe en Entra desde el IGA

Medido el 7-sep-2026 en producción: de los **12 recursos** de MidPoint, `UPEU-EntraID-Graph`
tiene `create`, `update` y `delete` **configurados en `false`**, **0 mappings outbound** y 2 de
sus 3 `objectType` en `proposed`. Enriquecer Entra desde MidPoint exigiría abrir tres candados a
la vez (permiso `User.ReadWrite.All`, capabilities y outbounds) — ninguno de los tres por sí solo
escribiría nada. Ver [`../m365-clasificacion-cuentas-2026-08-17/RUNBOOK.md`](../m365-clasificacion-cuentas-2026-08-17/RUNBOOK.md).

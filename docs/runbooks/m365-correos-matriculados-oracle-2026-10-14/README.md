# Correo institucional que falta en Oracle — matriculados de pregrado (2026-10-14)

Pedido del ticket GLPI **52507** (reporte de estudiantes activos para el proyecto de logueo, Ing. Barrantes)
y de la reunión de coordinación del 14-oct-2026: completar `MOISES.PERSONA_NATURAL.CORREO_INST` de los
matriculados de pregrado con el correo que **existe** en M365. La carga la ejecuta el equipo LAMB (Ever);
para el IGA, Oracle es **solo lectura**.

## Un comando

```bash
./generar.sh                 # semestre 283 = 2026-2
SEMESTRE=290 ./generar.sh    # otro semestre
```

Deja en `~/Downloads`: `Correos_para_cargar_Oracle_*.xlsx` (lo que se carga, para Ever), `Correos_por_revisar_*.xlsx` (conflictos, para Mesa de Servicios), `UPDATE_CORREO_INST_*.sql` (sin COMMIT)
y `ROLLBACK_CORREO_INST_*.sql`. Unos 10 minutos (7 son la descarga del tenant). Requiere la VPN.

## Reglas

- Pregrado = persona con **cualquier** contrato de pregrado con cursos en el semestre. Quien lleva además
  Idiomas o Posgrado sigue siendo de pregrado (el 13-oct se clasificaron mal 922 por tomar un solo nivel).
- Solo se propone una dirección que existe hoy como **buzón** en Entra ID. Orden: correo de MidPoint →
  cuenta cuyo usuario es el documento o el código → nombre exacto (este siempre va a «Confirmar»).
- **No se cambia el usuario de nadie** (decisión del 14-oct, a mitad de ciclo): `DNI@upeu.edu.pe` se informa
  tal cual.
- El SQL **solo completa lo que falta**: `CORREO_INST` vacío, numérico o con un correo no institucional. Si
  Oracle ya tiene una dirección con nombre (aunque no exista en M365), va a «Confirmar».
- Pasan a «Confirmar»: nombre de la cuenta que no coincide, cuenta deshabilitada, correo que ya es de otra
  ficha, documento con otra ficha (aviso de Owen), mismo correo para 2 personas.
- **Cuenta sin buzón ≠ sin cuenta.** El lote de admisión de julio-2026 se creó sin licencia: la cuenta existe
  y Oracle ya tiene el correo, pero `mail` está vacío. Crearles otra sería un duplicado → hoja 4.

## Candados del UPDATE

Cada fila exige `ID_PERSONA` + `ID_TIPODOCUMENTO` + `NUM_DOCUMENTO` y que `CORREO_INST` siga valiendo lo leído
al generar. Va en bloques PL/SQL de 400 con contador, y termina con un `SELECT` que debe devolver el total.
Antes de entregar se comprobó en Oracle (solo `SELECT`) que **4.495/4.495** filas cumplían los candados y que
la verificación final devolvía 0.

## Resultado del 14-oct-2026

| | Personas |
|---|---|
| Matriculados de pregrado 2026-2 | 15.307 |
| Oracle ya apunta a un buzón real | 8.199 |
| **1 Cargar en Oracle** (1.701 son `DNI@`) | **4.495** |
| 2 Confirmar antes (434 solo por nombre) | 490 |
| 3 Sin cuenta en M365 (156 con posible cuenta) | 1.615 |
| 4 Tiene cuenta sin licencia (405 con Oracle ya correcto) | 508 |

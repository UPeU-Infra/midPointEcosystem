# Prompt para MidPoint — 438 estudiantes activos sin PXX en LDAP

> Escrito desde InOut el 12-ago-2026. Medido en vivo contra `ldap://192.168.15.168`,
> no supuesto. **Es lo único que InOut necesita aprovisionado**: todo lo demás que
> encontramos (multiplicidad de códigos, formatos, duplicados, texto libre donde
> esperábamos códigos) ya lo absorbe InOut y no requiere nada de su lado.

---

## El hueco

`scibackAcademicProgramSuneduCode` no llega para **438 estudiantes activos** de programas
licenciados.

Filtro exacto:

```
(&(objectClass=inetOrgPerson)
  (eduPersonAffiliation=member)
  (eduPersonAffiliation=student)
  (!(scibackAcademicProgramSuneduCode=*)))
```

Devuelve 7.027, pero **6.573 son correctos**: CEPRE, Inglés, Conservatorio, cursos taller y
diplomaturas, que no son programas licenciados y cuya cobertura debe ser 0 % (Ley 30220
art. 46). Los 438 restantes sí están en unidades académicas reales.

### Dónde están

| unidad declarada en `ou` | estudiantes |
|---|---|
| Facultad de Ciencias Empresariales | 196 |
| Escuela General de Posgrado | 120 |
| Facultad de Ciencias de la Salud | 115 |
| Arquitectura y Urbanismo | 6 |
| EP Derecho | 1 |

Nótese que en la mayoría el `ou` es el nombre de la **facultad**, no de un programa: se les
aprovisionó la unidad pero no el programa.

### Qué traen y qué no

De los 438:

- **291** traen `eduPersonOrgUnitDN` o `eduPersonEntitlement` con la URI del concepto
- **147** no traen **ninguna** de las dos: solo el nombre de la facultad en `ou`

Muestra de esos 147, para que puedan verificarlos directamente:

```
uid=202014209   ou=Facultad de Ciencias de la Salud
uid=202421212   ou=Escuela General de Posgrado
uid=202421191   ou=Escuela General de Posgrado
uid=200310777   ou=Facultad de Ciencias Empresariales
uid=201150167   ou=Escuela General de Posgrado
```

---

## Por qué InOut no puede resolverlo por su cuenta

Es la parte que importa, y la comprobamos antes de escribir esto.

Construimos un mapa `URI del concepto → PXX` a partir del propio directorio: 19.213 personas
publican **ambos**, así que la correspondencia se puede deducir por mayoría. Salieron 66 URIs
con un PXX inequívoco (≥90 % de acuerdo). Con ese mapa, de los 438 solo se resuelven **16**.

Los otros 422 no se resuelven por dos motivos distintos:

1. **La URI no distingue la modalidad.** Los 86 de `programa/administracion` y los 106 de
   `programa/contabilidad-gestion-tributaria` tienen la URI, pero ese concepto agrupa
   `P04`/`P05`/`P95` y `P08`/`P09`/`P96` respectivamente. La URI no dice cuál de las tres, y
   ante SUNEDU son programas distintos. **Es precisamente el motivo por el que el ADR-005
   manda publicar el PXX al lado de la URI**: uno identifica la disciplina, el otro el
   programa licenciado concreto.
2. **147 no traen ninguna pista de programa**, solo la facultad.

Dicho de otro modo: no es que InOut no esté leyendo algo que ustedes ya publican. Lo
verificamos atributo por atributo, y el dato no está en LDAP de ninguna forma que permita
derivarlo sin adivinar la modalidad.

---

## Lo que se pide

Aprovisionar `scibackAcademicProgramSuneduCode` para esos 438. Nada más: ni un atributo
nuevo, ni un cambio de formato, ni deduplicar nada.

Probablemente se resuelva solo con el paso ya planeado en
[`PROMPT-consumir-puente-tesauro-2026-08-05.md`](PROMPT-consumir-puente-tesauro-2026-08-05.md):
reemplazar la LookupTable estática que hoy resuelve el programa **por nombre** por la tabla
generada desde `ID_PROGRAMA_ESTUDIO`. Ese documento estima que la cobertura de
`academicProgramUri` sube del 58,8 % al ~99 %. Si el PXX viaja con ella, este hueco se cierra
sin trabajo específico.

Si tras ese paso quedan estudiantes sin PXX porque su programa **no tiene** código en el A4/A8
—posible en Escuela General de Posgrado—, digan cuáles: InOut los reportará como «sin
programa», que es lo correcto, en vez de fingir un dato.

---

## Verificación

Cuando esté aprovisionado, esta consulta debe devolver solo los no licenciados (~6.573):

```bash
ldapsearch -x -LLL -H ldap://192.168.15.168:389 -D "<bind>" -w "<pass>" \
  -b ou=people,dc=upeu,dc=edu,dc=pe \
  "(&(objectClass=inetOrgPerson)(eduPersonAffiliation=member)(eduPersonAffiliation=student)(!(scibackAcademicProgramSuneduCode=*)))" \
  uid ou | grep -c '^dn:'
```

Del lado de InOut se ve sin SSH en `GET /admin/sync/health`, que reporta la cobertura de cada
campo por corrida: hoy `program` está al 66,81 % en el proveedor `ldap`.

## Trampas verificadas

- Los `192.168.x` pueden no responder **directo** desde una Mac y sí desde el jumphost OCI
  (`64.181.225.0`, key `~/.oci/jumphost_key`), que tiene ruta propia a la LAN. Un sondeo
  directo fallido **no** significa que la red esté caída — a nosotros nos pasó al medir esto.
- Usar `.168`: el nodo `.169` tiene deriva de `sizelimit`.
- `cn` y `ou` vienen en base64 (`ou::`) cuando llevan tildes, y LDIF pliega las líneas largas:
  hay que desplegarlas antes de decodificar. `ldapsearch -o ldif-wrap=no` no lo respeta el
  cliente de estos hosts.

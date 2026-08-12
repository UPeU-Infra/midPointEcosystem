# Prompt para la sesión de identidad (MidPoint / LDAP / Koha)

> Escrito desde InOut el 12-ago-2026. Todo lo de abajo está medido contra producción, no supuesto.
> **No es una petición de cambio en InOut**: son datos de las fuentes que InOut solo lee.

---

## El síntoma, y por qué importa

El sync del padrón de InOut rechaza **7 personas todos los días** con `IdentityCollision`.
No es un fallo de InOut: es su guarda de identidad negándose a fusionar dos registros que
declaran carnés distintos bajo el mismo documento.

**Seis de esas personas escanean como «Sin identificar» en el kiosko** cuando usan su carné
actual. Verificado en el código: el escaneo busca la credencial en el padrón, no la encuentra,
intenta rellenar desde LDAP, la colisión aborta el `upsert`, y cae en `unidentified`. Como el
`upsert` nunca cuaja, el carné **jamás llega a indexarse** — se repite en cada escaneo, no se
autocorrige.

El aforo sigue contándolas (InOut mide ocupación, no controla acceso), pero salen sin nombre,
sin facultad y sin programa en todos los reportes.

---

## Los 7 casos, con su causa

### B · LDAP tiene DOS entradas para la misma persona (2 casos)

Mismo `scibackDocumentNumber`, mismo `cn`, dos `uid` distintos, ambas en `ou=people`:

| documento | uid A | uid B | nombre |
|---|---|---|---|
| `60233598` | `324110503` | `202623077` | Yahir Alexander Neira Curo |
| `75609890` | `201811693` | `75609890` | Lisle Jahely Juarez Serquen |

Reproducible:

```bash
ldapsearch -x -LLL -H ldap://192.168.15.168:389 -D "<bind>" -w "<pass>" \
  -b ou=people,dc=upeu,dc=edu,dc=pe "(scibackDocumentNumber=60233598)" uid cn
```

Ojo a `75609890`: uno de los dos `uid` **es el propio documento**.

### C · El carné del padrón es el DNI, y llegó desde Koha (3 casos)

| documento | carné guardado | uid real en LDAP | nombre |
|---|---|---|---|
| `70596558` | `70596558` | `202622857` | Gonzalo Reymundo Soto |
| `75580413` | `75580413` | `201710512` | Hank Cruz Bonifacio |
| `76954791` | `76954791` | `202622864` | Jhessica Esther Diaz Portocarrero |

En estos, LDAP tiene **una sola** entrada y es correcta. El carné conflictivo viene de
`borrowers.cardnumber` de Koha, donde para algunos patrons el cardnumber **es literalmente el
DNI** en vez del código institucional.

### D · Carné = DNI en una fila de origen LDAP (2 casos)

| documento | carné guardado | uid real en LDAP | nombre |
|---|---|---|---|
| `72624529` | `72624529` | `201910711` | Jefferson Apolinar Rojas Burga |
| `78546736` | `78546736` | `202624609` | Yahaira Isabel Eustaquio Pascual |

LDAP hoy tiene una sola entrada, con el código institucional correcto. Pero la fila del padrón
guarda el DNI como carné y su `source` dice `ldap`. **No pude determinar** si LDAP publicó el
DNI como `uid` en algún momento anterior o si el valor llegó por Koha y otro proveedor
actualizó después el campo `source`. Es la pregunta abierta de este documento.

---

## Lo que se pide decidir

**1. ¿Cuál es el carné institucional de una persona, y puede tener más de uno?**

La guarda de InOut asume que **una persona tiene exactamente un carné**: es lo que la hace
capaz de detectar dos humanos distintos compartiendo documento. Si la respuesta institucional
es que un híbrido (trabajador que además estudió) legítimamente tiene dos códigos, hay que
decirlo, porque entonces la premisa de la guarda es falsa y habrá que rediseñarla.

Caso real que motiva la pregunta —**no está entre los 7, no da error**, pero muestra el
patrón—: *Osclaris Jhoanna Martinez Avila*, documento `1660870`, aparece como trabajadora con
carné `01660870` en LDAP y como egresada con carné `201711673` en Koha. Ambos parecen
legítimos. Esa persona está hoy duplicada en el padrón de InOut y se dejó así a propósito,
porque borrar cualquiera de las dos filas le quitaría un carné con el que puede escanear.

**2. Deduplicar las 2 entradas de LDAP (grupo B).** Dos entradas activas para la misma persona
hacen ambiguo cualquier consumidor que resuelva por documento. Si una es histórica, debería
retirarse o marcarse; si ambas son válidas, aplica la pregunta 1.

**3. Decidir qué hacer con el `cardnumber` de Koha cuando es el DNI (grupo C).** Son 3 casos
detectados por colisión, pero el patrón es más amplio: en Koha el `cardnumber` no es un
identificador consistente —a veces es el DNI de 8 dígitos, a veces un código por año—. Si Koha
va a seguir siendo proveedor de respaldo, conviene normalizarlo allí o declarar que su
cardnumber no es autoritativo.

**4. Aclarar el grupo D**, que es lo que InOut no pudo resolver desde fuera: ¿publicó LDAP el
DNI como `uid` en algún momento?

---

## Lo que InOut ya arregló de su lado (no hace falta pedirlo)

Había una **tercera causa que sí era nuestra** y está corregida (`b9c99ed`, en producción):
el `person_key` se derivaba del documento tal cual, así que `01261673` y `001261673` —el mismo
número con distinto relleno de ceros— creaban dos personas distintas. Eso explicaba **5 de las
12** colisiones originales; ahora la clave ignora los ceros de relleno cuando el valor es
íntegramente numérico. Las 7 restantes son las de este documento.

Si al revisar las fuentes aparece que el relleno de ceros también se propaga a otros sistemas,
vale la pena normalizarlo en origen: nosotros lo absorbemos, pero cada consumidor tendrá que
hacer lo mismo por su cuenta.

---

## Verificación

Cuando esté resuelto, esta consulta sobre la BD de InOut debe devolver **0**:

```sql
SELECT count(*) FROM provider_sync_runs
WHERE provider = 'ldap' AND errors > 0 AND started_at > now() - interval '1 day';
```

Y en los logs del backend no debe aparecer `IdentityCollision`:

```bash
docker compose logs backend --since 24h | grep -c IdentityCollision
```

## Trampas verificadas

- Los hosts `192.168.x` (LDAP `.168`/`.169`) solo responden con la VPN de UPeU levantada o el
  túnel WireGuard del jumphost OCI. Si no responde ninguno, es la red — no el servidor.
- Usar `.168`: el nodo `.169` tiene deriva de `sizelimit`.
- Los valores de `ou` y `cn` vienen en **base64** (`ou::`) cuando llevan tildes, y LDIF pliega
  las líneas largas: hay que desplegarlas antes de decodificar o el base64 sale truncado.
- `ldapsearch -o ldif-wrap=no` **no lo respeta** el cliente instalado en estos hosts.

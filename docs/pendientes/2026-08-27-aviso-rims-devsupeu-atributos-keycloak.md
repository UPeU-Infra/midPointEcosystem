# Aviso a RIMS y devsupeu-backend: os cambia el `eppn`, y el `affiliation` que recibís es de mayo

**27-ago-2026 · de: IGA (MidPoint) · para: responsables de `rims-upeu`, `rims-upeu-legacy`, `devsupeu-backend`**

Van dos cosas en el mismo aviso porque son el mismo problema: **Keycloak guarda copias de
atributos de identidad que nadie mantiene**, y vuestras tres aplicaciones son las únicas que las
leen.

---

## 1. Lo que acaba de cambiar: el `eppn` de 1.497 personas

**Qué ha pasado.** El 26-ago el IGA corrigió el `eduPersonPrincipalName` en el directorio: el
estándar eduPerson 202208 exige que el ePPN no sea un dato personal reasignable, y en UPeU una
parte del personal lo tenía construido sobre el **DNI**. El ePPN canónico pasó a ser
`<código institucional>@upeu.edu.pe`.

Keycloak se quedó con la versión anterior y **os ha estado sirviendo el valor viejo tres meses**.
Hoy se ha alineado con el directorio.

**Qué significa para vosotros.** Si vinculáis registros por el claim `eppn`, veréis cambiar el
identificador de **1.497 personas**. De ellas, **1.500 tenían literalmente un DNI** como ePPN
(el resto, otros valores antiguos).

**Cómo reconciliar sin perder el vínculo.** El directorio conserva el valor anterior en
**`eduPersonPrincipalNamePrior`**, que existe exactamente para esto:

```
uid: 200010003
eduPersonPrincipalName:      200010003@upeu.edu.pe   ← el nuevo
eduPersonPrincipalNamePrior: 41557134@upeu.edu.pe    ← el que teníais
```

Se consulta por LDAP. Si necesitáis el mapeo completo viejo→nuevo, lo entregamos en CSV.

**Por qué se ha hecho sin esperar.** Era un dato personal publicado en un claim de identidad
federada; el cambio ya estaba hecho en la fuente desde agosto y Keycloak era el único sitio donde
seguía expuesto.

---

## 2. Lo que sigue mal y necesita una respuesta vuestra: `affiliation`

**El dato que recibís es una foto de mayo-junio de 2026.** Medido el 27-ago sobre las 53.723
personas presentes en Keycloak y en el IGA:

| | |
|---|---|
| Coinciden | 43.335 |
| **Difieren** | **3.014 (6,5 %)** |
| **El token dice afiliación activa y el IGA dice egresado** | **753** |

Se desvía en las dos direcciones (895 `alum`→`student`, 636 `student`→`alum`, 449
`staff`→`faculty`…), lo que descarta un retraso de propagación: es una foto fija.

**Por qué.** Los 54.366 usuarios del realm son **cuentas locales** (`federation_link = NULL`)
creadas en una importación masiva —33.198 en mayo y 20.073 en junio— desde una **federación LDAP
que después se retiró**. Los atributos quedaron congelados en ese instante. La cadena
MidPoint → Entra ID → Keycloak no los refresca: Keycloak solo pide `openid profile email` a Entra
ID, y su `syncMode` es `IMPORT` (escribe únicamente al crear la cuenta).

### La pregunta

> **¿Vuestra aplicación toma decisiones de acceso con `affiliation`, o solo lo muestra o registra?**

- **Si solo lo mostráis o registráis:** el dato es inexacto, pero no hay incidente de acceso.
  Lo corregimos igualmente, sin urgencia.
- **Si autorizáis con él:** hay **753 personas conservando permisos que el IGA ya les retiró**, y
  hay que cambiar de fuente.

### Si autorizáis, la vía correcta es el LDAP

Lo fija el ADR-058: *«Keycloak dice QUIÉN eres. El LDAP dice QUÉ eres. Si el dato te importa para
decidir algo, no lo leas del token.»* RIMS ya tiene su bind `cn=rims-reader`.

**Dos avisos que muerden en silencio si montáis un bind nuevo:**

1. **`olcSizeLimit` es 10.000 y trunca las listas sin devolver error.** Solo `cn=midpoint` y
   `cn=rims-reader` tienen `size=unlimited`. Un bind nuevo lo necesita desde el primer día, o
   leerá resultados incompletos creyéndolos completos.
2. **`ldap.upeu.edu.pe` no resuelve al LDAP real** — apunta a `192.168.13.160`, que no responde
   ni en 389 ni en 636. Hay que conectar por IP.

---

## 3. Un apunte sobre `LDAP_ID`, por si no lo sabíais

`rims-upeu-legacy` publica el claim `epuid` leyendo el atributo interno **`LDAP_ID`** de
Keycloak, que es el UUID que dejó la federación ya retirada. Funciona, pero está apoyado en un
resto de algo que ya no existe: si alguien limpia ese sedimento —cosa que estuvo a punto de
pasar hoy— ese claim se queda vacío sin previo aviso. Conviene moverlo a una fuente viva.

---

## 4. Lo que no vamos a hacer

**No vamos a re-federar el LDAP en Keycloak ni a montar un proceso que copie atributos.** Es lo
que creó este problema: la copia envejece en cuanto la sincronización se detiene, y ya se detuvo
una vez. La dirección correcta es la contraria — que estos atributos dejen de vivir en Keycloak
y se lean del directorio cuando hagan falta.

Cualquier duda, respondemos. Y si preferís una llamada corta para verlo con los datos delante,
mejor todavía.

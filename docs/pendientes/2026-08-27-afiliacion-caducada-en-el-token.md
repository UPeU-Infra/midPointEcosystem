# La afiliación que viaja en el token está caducada para 3.014 personas

**27-ago-2026 · para DTI y los equipos de las 12 aplicaciones federadas**
**Estado: medido en producción. Antes de actuar hace falta una respuesta de cada equipo.**

## Resumen en tres líneas

El claim `primaryAffiliation` que Keycloak entrega a las aplicaciones **no lo mantiene nadie**:
es una copia guardada en cada cuenta que no se refresca. Comparado con lo que el IGA sabe hoy,
**difiere para 3.014 personas (6,5 %)**. En **753** de ellas el token concede una afiliación
activa a alguien que el IGA ya tiene como egresado.

**Si tu aplicación decide accesos con ese claim, esas 753 personas conservan permisos que el IGA
ya les retiró.** Si solo lo muestras o lo registras, no hay riesgo de seguridad — pero el dato
que enseñas puede estar equivocado.

## Qué se midió

53.723 personas presentes a la vez en Keycloak y en el IGA:

| | |
|---|---|
| Coinciden | 43.335 |
| **Difieren** | **3.014 (6,5 %)** |

Desglose de las discrepancias:

```
895  el token dice alum     y el IGA dice student     ← acceso de MENOS
636  el token dice student  y el IGA dice alum        ← acceso de MÁS
449  el token dice staff    y el IGA dice faculty
435  el token dice alum     y el IGA dice faculty
286  el token dice alum     y el IGA dice staff
 82  el token dice staff    y el IGA dice student
 69  el token dice faculty  y el IGA dice alum
```

Se desvía **en las dos direcciones**, lo que descarta un retraso de propagación: es una foto sin
mantenimiento. Unos se quedaron congelados al graduarse; otros, al ser contratados.

Los **895 con acceso de menos** no son un riesgo de seguridad, pero sí de servicio: gente a la
que una aplicación puede estar negándole lo que le corresponde, y que probablemente no lo ha
reportado porque no sabe que debería tenerlo.

## Por qué pasa

Nadie aprovisiona Keycloak. Verificado el 27-ago:

- **MidPoint no tiene resource de Keycloak** — ninguno de sus 12 lo es.
- **Los mappers del IdP no escriben la afiliación**: los 4 solo copian `username`, `firstName`,
  `lastName` y `email`.
- El cliente `midpoint-provisioner` existe y tiene permisos de `manage-users`, pero **nunca ha
  pedido un token**: 0 eventos.
- Las 23 escrituras registradas sobre usuarios vienen de la **consola de administración**.

Los atributos de identidad de Keycloak son **una foto del pasado**. El 26-ago el IGA corrigió el
`eduPersonPrincipalName` de ~4.600 personas y Keycloak no se enteró; el desfase de afiliación es
el mismo fenómeno, pero sobre el dato que sí decide accesos.

## Quién recibe el claim

**13 de 19 clientes habilitados** reciben atributos de identidad en el token:

| Vía | Clientes |
|---|---|
| Scope `upeu` (`primaryAffiliation`, `facultyShortName`) | `koha-upeu`, `indico-upeu`, `librechat`, `onyx`, `guia-node`, `mayan-sgc`, `sgc-frappe`, `cloudflare-access`, `dgi-ingest-connector`, `rims-provisioning`, `devsupeu-backend`, `midpoint-provisioner` |
| Mappers propios | `rims-upeu` (`eppn`, `epuid`, `affiliation`, `eduperson_entitlement`), `devsupeu-backend` |

## Lo que se pide a cada equipo — una sola pregunta

> **¿Tu aplicación toma decisiones de acceso con `primaryAffiliation` del token, o solo lo usa
> para mostrar o registrar?**

De la respuesta depende todo lo demás. Sin ella, cualquier acción es a ciegas.

## La alternativa correcta, y ya hay precedente

Lo dice el ADR-058: **«Keycloak dice QUIÉN eres. El LDAP dice QUÉ eres. Si el dato te importa
para decidir algo, no lo leas del token.»**

Quien necesite la afiliación para autorizar debe leerla del LDAP, como ya hace RIMS con su bind
`cn=rims-reader`. El IGA puede provisionar un bind de solo lectura por aplicación. **Dos avisos
que van con él, porque los dos muerden en silencio:**

1. **`olcSizeLimit` es 10.000 y trunca sin error visible.** Solo `cn=midpoint` y
   `cn=rims-reader` tienen `size=unlimited`. Un bind nuevo lo necesita desde el primer día, o
   leerá listas incompletas creyéndolas completas.
2. **`ldap.upeu.edu.pe` NO resuelve al LDAP real** — apunta a `192.168.13.160`, que no responde
   ni en 389 ni en 636. Hay que conectar por IP hasta que se corrija el DNS.

## Lo que NO se propone

- **Sincronizar Keycloak con el LDAP**, ni por federación ni por un proceso que copie atributos.
  La federación la prohíbe el ADR-058 explícitamente, y copiar reconstruye el mismo problema: la
  copia vuelve a envejecer entre pasadas.
- **Resucitar `midpoint-provisioner`.** Un cliente con permiso para modificar 54.000 usuarios que
  nadie usa es superficie de ataque sin contrapartida. Si se confirma que no hace falta, retirarlo.

## Mientras se decide

Documentar el claim como **informativo y potencialmente caducado**. Es honesto, no rompe nada y
evita que una aplicación nueva lo adopte para autorizar creyéndolo fiable.

## Anexos

- Lista de las 753 personas con afiliación activa en el token y `alum` en el IGA:
  `riesgo-afiliacion.txt` (no se incluye aquí por ser dato personal).
- Método: volcado completo de ambos lados y cruce por `username`/`name`. Reproducible con el
  script `desfase-afiliacion.sh`.

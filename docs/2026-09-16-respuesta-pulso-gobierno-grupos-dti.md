# Respuesta a Pulso — gobierno de los grupos `dti-*`

**Fecha:** 16-sep-2026 · **Responde a:** `2026-09-16-mensaje-iga-gobierno-grupos-dti.md`
**Verificado en:** MidPoint `.166` y LDAP `.168` en producción

---

## Mensaje (copiar tal cual)

> Gracias por el aviso, y sobre todo por no haber escrito en LDAP por vuestra cuenta: eso nos
> permitió encontrar la causa real, que no es ninguna de las dos que suponíamos.
>
> ### 1 · `dti-devops` — resuelto, y la causa era otra
>
> **El grupo ya no existe.** Con él se fue su rol `AR-DTI-Team-devops`, que tenía cero titulares.
> Vuestro `memberOf` ya está limpio:
>
> ```
> uid=9610165 → cn=dti-seguridad-informatica, cn=dti-infraestructura-ti
> grupos dti-* : 25 → 24
> ```
>
> **Pero la causa no era el modo canario.** Estaba en el log de MidPoint desde el día 15:
>
> ```
> Error modifying LDAP entry cn=dti-devops:
>   [remove: uniqueMember=uid=9610165]
>   objectClassViolation: object class 'groupOfUniqueNames'
>                         requires attribute 'uniqueMember' (65)
> ```
>
> **MidPoint sí intentaba retirar la pertenencia, en cada pasada, y OpenLDAP se lo rechazaba.**
> Alberto era el único miembro y `groupOfUniqueNames` no admite grupos vacíos: al sacarlo, la
> entrada quedaría sin `uniqueMember` y el servidor rechaza la operación entera.
>
> Los mensajes que citabais (`not visible in current task execution mode`) son de haber lanzado la
> reconciliación **en modo simulación**, no de un gobierno desactivado.
>
> ### 2 · Los 22 grupos **sí** están gobernados — la `description` mentía
>
> Esto es culpa nuestra y ya está corregido. Esas descripciones son texto de la carga inicial del
> 3-sep que nadie actualizó cuando, ese mismo día, se implantó el gobierno.
>
> Lo medimos así, y es la prueba que zanja el asunto:
>
> | grupo | miembros en LDAP | titulares del rol en MidPoint |
> |---|---|---|
> | `dti-soporte-ti` | 11 | 11 |
> | `dti-desarrollo-lamb-academico` | 9 | 9 |
> | `dti-desarrollo-lamb-financiero` | 7 | 7 |
> | `dti-redes-y-conectividad` | 5 | 5 |
> | … | … | … |
>
> **24 de 25 coincidían exactamente**, uno a uno. El único que no cuadraba era `dti-devops`, por el
> motivo de arriba. Los 25 tienen su rol `AR-DTI-Team-*` con inducement al grupo LDAP, y 24 llevan
> el `subtype` que usa la autoasignación desde `serviceDeskTeam`.
>
> Estado real de la configuración, por si queréis contrastarlo:
>
> ```
> objectType entitlement/group  → lifecycleState: active
> associationType ri:group      → lifecycleState: active,  tolerant=false
> recurso LDAP                  → active
> ```
>
> **Las 22 descripciones ya están corregidas** y ahora dicen «Gobernado por MidPoint (verificado
> 2026-09-16)». Tenéis razón en el fondo del reproche: un texto que afirma el estado de algo, o se
> mantiene, o no se escribe. Os hizo perder tiempo y era evitable.
>
> **Respuesta a vuestra pregunta:** no hace falta plan ni calendario. Los 24 grupos están
> gobernados desde el 3-sep; cuando alguien cambia de equipo, el directorio se entera solo.
>
> ### 3 · ⚠️ Lo que sí era un problema de verdad, y os afecta al contar
>
> Vuestro caso destapó algo peor que lo que reportabais: **un grupo con un solo miembro no se puede
> vaciar**. Y teníamos **once** así, incluido vuestro ejemplo de `dti-desarrollo-lamb-admision-events`.
>
> El día que esa única persona cambie de equipo, pasa exactamente lo del 15-sep: MidPoint intenta
> retirarla, LDAP lo rechaza y **la persona se queda en el grupo viejo sin que nadie se entere** —
> el fallo solo se ve leyendo el log de MidPoint. Es justo el escenario que os preocupaba.
>
> **Ya está frenado.** Hemos añadido una entrada centinela a esos once grupos:
>
> ```
> cn=iga-group-sentinel,ou=services,dc=upeu,dc=edu,dc=pe
> ```
>
> Con ella el grupo nunca queda vacío, así que la retirada de la última persona funciona. Vive en
> `ou=services`, fuera del ámbito que MidPoint gobierna (`ou=people`), de modo que el IGA ni la
> toca ni la cuenta como persona.
>
> **🔴 Lo que necesitamos de vosotros: excluidla al contar o listar miembros.**
>
> ```
> uniqueMember: cn=iga-group-sentinel,ou=services,dc=upeu,dc=edu,dc=pe   ← ignorar
> ```
>
> Si no la filtráis, esos once equipos aparecerán con una persona de más. No es un `uid=` y no está
> en `ou=people`, así que os basta con descartar los `uniqueMember` que no cuelguen de `ou=people`
> — que además os protege de cualquier otro centinela futuro.
>
> Los once son: `activos-digitales`, `administrativo`, `base-de-datos`, las tres `coord-sti-*`,
> `desarrollo-lamb-admision`, `desarrollo-lamb-admision-events`, `desarrollo-lamb-mantenimiento`,
> `desarrollo-lamb-research` y `direccion-dti`.
>
> Tras el cambio: **69 personas reales** repartidas en 24 grupos, once de ellos con un centinela
> adicional.
>
> ### 4 · Y una corrección a nosotros mismos
>
> Cuando medimos «24 de 25 grupos coinciden» estuvimos a punto de cerrar el asunto ahí. Pero
> coincidían **porque nadie se había movido desde la carga inicial**: el primer cambio real fue el
> del 15-sep y falló. Un censo estático no prueba que el mecanismo funcione; lo prueba un cambio
> propagado. Vuestro reporte, aunque partía de una premisa equivocada, apuntaba a un problema real.
>
> Si os sirve, podemos pasaros el reparto de las 69 personas por grupo en el formato que prefiráis.

---

## Notas para nosotros (no enviar)

- **Lo aplicado hoy en producción:** borrado del rol `AR-DTI-Team-devops` y del grupo
  `cn=dti-devops` (este último con `ldapdelete`, porque el recurso LDAP tiene
  `capabilities/configured/delete: {enabled:false}` por política); borrado del shadow del grupo con
  `?options=raw`; corrección de 22 `description`; creación del centinela y su alta en 11 grupos.
- **Pendiente cosmético:** el `fullObject` cacheado del shadow de `uid=9610165` aún muestra
  `dti-devops`. El LDAP real está bien y no hay referencias rotas (0 en `m_reference`). Un recompute
  simple no lo refresca —recompute ≠ reconcile— y el `reconcile` sobre LDAP se cuelga (900 s).
- **No prometer** que el centinela resuelve el caso de un grupo que se queda **sin ninguna persona**:
  ahí la decisión correcta es borrar el grupo, y MidPoint no puede hacerlo por la política de
  `delete`. Eso sigue siendo manual.
- Pendientes anteriores con Pulso: Ronald (correo institucional en el campo personal, en Oracle) y
  Hilter (cuenta de Keycloak sin `eppn`), de `2026-08-18-mensaje-iga-tres-casos.md`.

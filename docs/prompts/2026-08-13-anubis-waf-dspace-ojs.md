# Prompt — desplegar Anubis (WAF anti-scraping) en DSpace y OJS

**Para:** sesión de DSpace / OJS en AWS · **Origen:** sesión IGA-MidPoint, 13-ago-2026

---

## Guía a seguir

**https://waf.lareferencia.info/docs/**

Guía operativa de **LA Referencia** para proteger con **Anubis + Nginx Proxy Manager**
portales y repositorios institucionales latinoamericanos. Está escrita exactamente para
este caso de uso: DSpace y portales académicos de la región.

Proyecto: https://github.com/TecharoHQ/anubis

---

## Prompt

> Necesito proteger nuestros repositorios DSpace y el portal OJS del scraping masivo de
> bots de IA, siguiendo la guía de LA Referencia: **https://waf.lareferencia.info/docs/**
>
> **Contexto que lo motiva.** En el Koha de UPeU medimos tráfico automatizado sostenido
> contra el OPAC: **20.000–31.000 peticiones por hora, constantes desde las 3 de la
> madrugada**, el 81 % contra la búsqueda con facetas. El servidor llegó a `load 13`, con
> 3 workers vivos de 16 y 2 GB libres de 24. No se puede filtrar por IP porque todo el
> tráfico externo entra por un proxy y comparte la misma IP de origen. DSpace y OJS están
> expuestos a lo mismo y con más razón: son justamente el tipo de contenido que rastrean
> los scrapers de IA.
>
> **Lo que pido:**
>
> 1. Evaluar si la arquitectura de la guía (`Internet → Nginx Proxy Manager → Anubis →
>    backend`, todo en Docker) encaja con nuestro despliegue actual, y decir en qué punto
>    concreto se insertaría Anubis en cada servicio.
> 2. Redactar la `botPolicy` para nuestro caso, no copiarla tal cual.
> 3. Desplegar primero en **UN** servicio (el menos crítico) y medir el efecto antes de
>    extenderlo.
>
> **Requisitos innegociables — verificar ANTES de poner nada en producción:**
>
> - **El cosechado OAI-PMH NO puede romperse.** ALICIA/CONCYTEC y RENATI cosechan
>   nuestros repositorios; si Anubis los bloquea, dejamos de reportar al Estado y eso
>   tiene consecuencias normativas, no solo técnicas. La guía trae
>   `path_regex: ^/OAI.*$ → ALLOW`: confirmar que cubre las rutas reales de nuestro
>   DSpace y probar un cosechado completo tras el despliegue.
> - **Google debe seguir indexando.** La guía marca como red confiable el rango
>   `66.249.64.0/20`. Verificar que la indexación sigue viva después.
> - **Handle.Net y los identificadores persistentes** deben resolver igual.
> - Los **bots de IA** (GPTBot, ClaudeBot, Amazonbot) sí se bloquean: es el objetivo.
>
> **Dos cosas que NO están confirmadas y hay que verificar antes de decidir:**
>
> - La guía habla de «un desafío criptográfico casi invisible para humanos», pero **no
>   dice explícitamente si exige JavaScript en el cliente**. Si lo exige, cualquiera con
>   JS desactivado queda fuera de un repositorio público. Confirmarlo en la documentación
>   de Anubis antes de desplegar.
> - El propio proyecto advierte: *«Anubis is a bit of a nuclear response. This will result
>   in your website being blocked from smaller scrapers and may inhibit "good bots" like
>   the Internet Archive.»* Decidir conscientemente si aceptamos perder Internet Archive.
>
> **Nota de licencia:** la guía indica que las funciones avanzadas de Anubis son de la
> versión comercial (50 USD/año); ella usa solo la open source. Confirmar que lo que
> necesitamos está en la versión libre.
>
> Antes de tocar producción, medir el volumen de bots actual en cada servicio (logs de
> Nginx/Apache por hora y por user-agent) para tener la línea base y poder demostrar
> después que sirvió.

---

## Por qué encaja mejor en DSpace/OJS que en Koha

La guía asume **Nginx Proxy Manager en Docker**, que es como están desplegados nuestros
DSpace y OJS. El Koha de UPeU va con **Apache + un balanceador institucional
(`pr-lb-intranet1`, 192.168.12.199)** que administra Redes, así que ahí la inserción es
más intrusiva y depende de terceros.

En DSpace/OJS el punto de inserción es nuestro y el patrón de la guía aplica casi directo.

## Antes de Anubis, lo barato

En Koha detectamos que **no existe `robots.txt`**. Comprobar si en DSpace/OJS existe y
está bien puesto: los rastreadores que se identifican (Baiduspider aparecía en nuestros
logs) lo respetan, y un `Crawl-delay` puede bajar mucho el volumen sin efectos
secundarios ni software nuevo que mantener.

Anubis es la respuesta para los que **falsifican** el user-agent, que son los que quedan
después.

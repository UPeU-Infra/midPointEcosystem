# Los 4.386 errores de login de Indico son bots extranjeros, no usuarios

**27-ago-2026 · diagnóstico. No se ha modificado nada.**

## Conclusión

**No hay fallo en Indico ni en Keycloak, y ningún usuario está afectado.** Los errores son
tráfico automatizado extranjero golpeando el endpoint de login. Lo que sí producen es **ruido que
degrada la auditoría** del realm.

## Lo medido

| | |
|---|---|
| `IDENTITY_PROVIDER_LOGIN_ERROR` / `cookie_not_found` en `indico-upeu` | **2.303** |
| `invalidRequestMessage` sin cliente asociado | **1.990** |
| IPs distintas | **489** |
| **IPs compartidas entre los dos grupos** | **399** — es el mismo tráfico |
| **Logins exitosos de `indico-upeu` en 7 días** | **0** |

## Por qué son bots y no personas

**Ninguna de las 489 IPs pertenece a rangos peruanos.** Las que más golpean:

| IP | Propietario | País |
|---|---|---|
| 193.202.84.104 | FT-GreatFlower | 🇫🇮 Finlandia |
| 81.167.26.57 | Lyse (residencial) | 🇳🇴 Noruega |
| 147.135.213.27 | RIPE / OVH | 🇳🇱 Países Bajos |
| 95.108.213.223 | **Yandex** | 🇷🇺 Rusia |
| 51.83.6.238 | OVH | 🇫🇷 Francia |

Datacenters y un crawler identificado (Yandex). El reparto refuerza el diagnóstico: 248 IPs con
2-5 peticiones, 134 con 6-20, 102 con una sola — dispersión de rastreo, no de usuarios.

Y el pico está en **sábado 22 (590) y domingo 23 (775)**, cuando menos gente usa una plataforma
de eventos académicos.

`cookie_not_found` es exactamente lo que produce un crawler: sigue el enlace de «iniciar sesión»
que Indico expone públicamente, llega al endpoint del *broker* sin haber iniciado el flujo, y no
encuentra la cookie de sesión de autenticación.

## Lo que sí importa de esto

**El ruido se está comiendo la auditoría.** Con `eventsExpiration` a 7 días, la tabla de eventos
tiene **4.293 eventos de basura frente a ~1.076 legítimos** (koha-upeu 851, rims-provisioning 213,
sgc-frappe 12): el 80 % es ruido. Esa tabla es la única fuente para saber qué clientes se usan de
verdad — hoy mismo hizo falta para descartar que el sedimento de atributos tuviera consumidores.

## Propuesta (nada aplicado)

1. **Limitar por tasa en Caddy** las rutas `/realms/upeu/broker/*` y
   `/realms/upeu/protocol/openid-connect/auth`. Los crawlers no respetan `robots.txt`; el rate
   limit sí los frena y no molesta a un usuario real, que hace un intento cada vez.
2. **Revisar si Indico debe exponer el enlace de login a usuarios anónimos** en páginas
   indexables. Es la puerta por la que entran.
3. **No tocar la retención de eventos** hasta reducir el ruido: subirla solo guardaría más basura.

## Aparte: escaneo de vulnerabilidades contra el host

En los registros del proxy aparecen peticiones a `/.well-known/acme-challenge/cloud.php`,
`xmrlpc.php` y `license.php`. Es escaneo genérico buscando PHP. **No hay PHP en ese host**, así
que no hay riesgo directo, pero confirma que el servidor está siendo sondeado desde fuera y
refuerza la recomendación del rate limit.

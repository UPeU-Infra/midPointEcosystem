# Koha: filtrado local de bots y anomalías de red — estado al 14-ago-2026

**Para:** la sesión de Claude que trabaja Koha
**De:** la sesión del IGA (MidPoint). Todo lo de aquí está **medido en vivo el 14-ago-2026**,
no inferido. Lo que no pude probar está marcado como tal.

---

## Por qué existe este encargo

El OPAC se saturó el 13-ago (load **43,58**, 1 worker) y bloqueó la reconciliación de
Estudiantes del IGA. Se pidió a Redes filtrar en el proxy; Rudy respondió que **a nivel global
no se puede** —«es el proxy externo, se bloquea y ni una app funcionaría»— así que **el filtro
tiene que vivir en el propio servidor de Koha**. Eso es lo que se montó, y lo que queda.

## 🔴 CORRECCIÓN (14-ago, tarde): hay DOS Koha, y este prompt trata el viejo

Al diagnosticar un fallo del IGA se descubrió que **`192.168.12.135` no es el Koha que
gobierna MidPoint**:

| Host | Qué es | Estado |
|---|---|---|
| **`.136`** `koha-plus-prod` | Instancia **consolidada** `koha_upeu`, una sola, 4 branches (BUL/BUJ/BUT/CIA), **33.582 patrons, 32.892 vigentes**, categorías nuevas (`student`, `alum`, `staff`, `faculty`) | **el vivo — lo que MidPoint aprovisiona** |
| **`.135`** `koha-app-prod-nodo1` + BD en **`.130`** | Las **4 bases viejas** separadas (`koha_bul`, `koha_buj`, `koha_but`, `koha_cia`), categorías antiguas (`ESTUDI`, `DOCEN`), **casi todos los patrons expirados** | **el viejo, en retirada** |

**Todo lo que describe este prompt —Apache, fail2ban, mod_remoteip, el escáner de WordPress—
ocurre en `.135`, el viejo.** Sigue siendo trabajo válido (ese OPAC está publicado y recibe
tráfico), pero **la prioridad debe revisarse**: si `.135` está en retirada, quizá la respuesta
correcta no es blindarlo sino apagarlo. Y lo que sí hay que verificar es si **`.136` tiene la
misma exposición** — no se ha mirado.

Dato que lo prueba: los 33.582 patrons de `koha_upeu` cuadran con los 33.578 shadows de Koha
que MidPoint tiene registrados. Las bases de `.130` no cuadran con nada del IGA.

## Acceso

```bash
source ~/.secrets/koha-prod.env
sshpass -p "$KOHA_SSH_PASS" ssh koha-upeu     # 192.168.12.135, ProxyJump bastion-alberto
```

`sudo` **no es passwordless**; se usa con el mismo password:
`echo "$KOHA_SSH_PASS" | sudo -S -p '' <comando>`.
⚠️ Ojo: `KOHA_PROD_PASS` es de la API web, **no** de SSH. Confundirlos da `Permission denied`.

Instancias y puertos: `bul`=8000 (Lima), `buj`=8002 (Juliaca), `but`=8004 (Tarapoto),
`cia`=8006. Los `-intra` van en el puerto siguiente de cada uno.

---

## 1. La pieza que hacía imposible el filtrado local

`mod_remoteip` ya estaba activo con `RemoteIPHeader X-Forwarded-For`, pero
`RemoteIPTrustedProxy` **solo declaraba `192.168.12.200`**. El proxy que entrega el tráfico es
**`pr-lb-intranet1` = `192.168.12.199`**, que no estaba declarado: su tráfico se registraba con
la IP del proxy y era indistinguible del de cualquier usuario.

**Aplicado:** `RemoteIPTrustedProxy 192.168.12.200 192.168.12.199`
(`/etc/apache2/conf-available/remoteip.conf`, backup `.bak-20260814-0533`).

Consecuencia: `REMOTE_ADDR` ya es la **IP real del cliente**, y se puede bloquear a un bot
concreto **sin tocar el proxy y sin afectar a nadie más**.

**Límite que hay que tener presente:** para el tráfico que llega **por el proxy**, iptables no
sirve — todos los paquetes llevan la IP del proxy, y `192.168.12.0/24` está (correctamente) en
`ignoreip`. Ese filtro tiene que vivir en **Apache**. Para el que llega **directo** —como el
escáner— fail2ban sí lo bloquea.

## 2. Quién estaba entrando

`119.8.198.149` (Huawei Cloud): **504 peticiones el 13-ago** a `/wp-login.php`, `/wp-admin/*`,
`/wp-includes/*` contra **Juliaca**. **Las 504 recibieron HTTP 200**, porque el OPAC de Juliaca
devuelve su página de login ante *cualquier* URL inexistente. Cada una hace renderizar el OPAC
entero — y el 200 le confirma al escáner que vale la pena volver. Sigue picando hoy (17
peticiones a las 02:50).

**fail2ban vigilaba solo Lima.** El bot fue justo a la única puerta sin vigilancia.

## 3. Lo aplicado (todo local, con backups `.bak-20260814*`)

| Qué | Dónde | Verificado |
|---|---|---|
| Proxy `.199` como trusted | `conf-available/remoteip.conf` | sí |
| Bloqueo de rutas WordPress/`.env`/`.git` | `/etc/koha/apache-shared-opac-antibot.conf` | **403 en bul, but, cia** |
| Lista de baneo dinámica (`RewriteMap txt:`) | `/etc/apache2/koha-banned.txt` | declarada; sin usar aún |
| Jail **`koha-scanner`** (nueva) | `/etc/fail2ban/jail.d/koha.conf` | ver abajo |
| Jail **`koha-bot-flood`** extendida a las 4 instancias | idem | activa |

Formato de la lista de baneo: una línea `<ip> ban`. Apache la relee sola: **banear NO requiere
recargar Apache**.

**Validación del filtro contra el ataque real** (`fail2ban-regex` sobre el log del 13-ago):

```
376 de 646 líneas matchean · 0 falsos positivos sobre 267 líneas de tráfico legítimo
```

Con `maxretry=3` el escáner habría caído en la tercera petición.

---

## 🔴 Pendiente 1 — Juliaca no acepta el bloqueo en Apache (sin explicar)

En `bul`, `but` y `cia` el antibot funciona (403). **En `buj` no surte efecto nada:**

- ni `RewriteRule … [F,L]` — **tampoco la regla anti-Meta del 17-jun**, que sí funciona en las
  otras tres;
- ni `<LocationMatch>` + `Require all denied`, ni **antes** ni **después** de los `Include`.

Y sin embargo:

- un `Header always set X-SciBack-Test` **del mismo vhost sí llega** a la respuesta → las
  directivas del vhost **se están aplicando**;
- el log confirma que la petición cae en `opac-buj-access.log` → **es ese vhost**;
- `apache2ctl -S` da `*:8002 buj.myDNSname.org (buj.conf:4)`, un solo vhost en ese puerto;
- `configtest` = `Syntax OK` y el `graceful` recarga (los workers cambian de PID).

Probé cuatro variantes; ninguna prendió. **No lo cierro y no quiero adivinar más.**
Hoy Juliaca está cubierta solo por fail2ban, que actúa en red y no depende de Apache.

Pistas para retomarlo:
- `buj` responde **200 a CUALQUIER URL inexistente** (`/no-existe-xyz` → 200 con la página de
  login), mientras `bul` responde 404 con la misma configuración compartida. Averiguar quién
  genera ese 200 probablemente explica también por qué el filtro no aplica.
- Única diferencia textual encontrada entre `bul.conf` y `buj.conf`: `Define instance "buj"`
  **con comillas** frente a `Define instance bul` sin ellas. No he probado si es relevante.
- Sospecha no verificada: alguna sección de los `Include` compartidos que reabra la
  autorización, o que la petición salga del pipeline antes de la fase de autorización.

## 🔴 Pendiente 2 — `but` y `cia` no tienen Plack corriendo

Su OPAC devuelve **503**: no existen `/var/run/koha/but/plack.sock` ni el de `cia`; solo están
los de `buj` y `bul`, creados en el reinicio del **12-ago 03:05**.

**Es preexistente — no lo causaron estos cambios** (lo comprobé por los sockets y el
`proxy:error … No such file or directory`, no por suposición). **Falta decidir si Tarapoto y
CIA deben estar sirviendo su OPAC**; si deben, están caídos desde el 12-ago.

## 🟡 Pendiente 3 — el OPAC de Lima no recibe tráfico externo desde el 11-ago

`opac-bul-access.log` lleva **0 bytes** desde el 11-ago, cuando en julio hacía 5–7 MB/día.
**No es un log roto**: un canario (`curl` al OPAC) se registró correctamente. Es **ausencia de
peticiones**. Merece explicación: o el tráfico público entra por otra ruta, o algo dejó de
apuntar aquí. `biblioteca.upeu.edu.pe` responde 200 pero **tarda 9,7 s**, y su petición no
aparece en este log.

## 🟡 Pendiente 4 — `robots.txt`

Los OPAC no lo tienen. No frena a un escáner malicioso, pero sí a los crawlers legítimos que
también pesan.

---

## Lo que NO hay que hacer (aprendido a golpes)

1. **No bloquear la IP del proxy** (`192.168.12.199` / `.200`) ni el rango `192.168.12.0/24`:
   corta a toda la universidad. Es literalmente lo que advirtió Rudy.
2. **No usar `Require not ip` sin `mod_remoteip` bien configurado**: el 13-ago no matcheó nunca
   porque Apache veía la IP del proxy. Se perdió una tarde en eso.
3. **`<RequireAll>` no es válido directamente en `VirtualHost`**, y en su día `mod_rewrite`
   parecía no estar cargado — **lo estaba**: el `apache2ctl -M` se ejecutó sin `sudo` y falló
   en silencio. **Comprobar siempre que el comando de diagnóstico devolvió algo**, no
   interpretar el vacío como respuesta.
4. **No tocar `bul.conf.bak.20260504`** ni los `.bak-*`: son la vía de vuelta.
5. Antes de concluir que algo está roto, **lanzar un canario**. El log a 0 de Lima parecía un
   logging roto y era ausencia de tráfico; la diferencia cambia por completo el diagnóstico.

## Contexto del que depende otro equipo

El IGA **reanuda la reconciliación de Estudiantes** cuando Koha tiene margen (hoy load 0,41, así
que hay). Esa reconciliación aprovisiona patrons en Koha: si el OPAC vuelve a saturarse, el
canal de identidad se para otra vez. Por eso importa cerrar los pendientes 1 y 2.

Contacto de Redes para el proxy: **Rudy** (`pr-lb-intranet1`, 192.168.12.199).

#!/usr/bin/env python3
"""
reniec-enrich-apiperu.py — Step 5: Enriquecimiento RENIEC vía apiperu.dev

Para usuarios con dataQualityStatus=pending (o sin el campo), consulta
apiperu.dev para validar el DNI y actualiza MidPoint con el resultado.

CUOTA: 100 consultas/mes a apiperu.dev. Usar --dry-run para simular.

Uso:
  python3 reniec-enrich-apiperu.py [--dry-run] [--max N] [--status STATUS]

  --dry-run        Simula sin PATCH en MidPoint ni consumir cuota apiperu.dev
  --max N          Máximo de usuarios a procesar (default: 100)
  --status STATUS  Qué usuarios buscar:
                     pending          → extension/upeu:dataQualityStatus = 'pending'
                     none             → sin campo dataQualityStatus
                     pending_or_none  → ambos (default)

Secretos requeridos:
  ~/.secrets/midpoint-upeu.env  → MIDPOINT_ADMIN_PASS
  ~/.secrets/apiperu.env        → API_PERU_TOKEN

Servidores:
  MidPoint: http://192.168.15.166:8080/midpoint/ws/rest
  apiperu:  https://apiperu.dev/api/dni/{dni}

Namespaces usados:
  upeu (urn:upeu:midpoint:local)      → dataQualityStatus, reniecValidationDate
  sb   (urn:sciback:midpoint:person)  → taxId (URN DNI)

taxId URN format: urn:schac:personalUniqueID:pe:DNI:PE:{8 dígitos}
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

# ─── Constantes ───────────────────────────────────────────────────────────────

MIDPOINT_BASE   = "http://192.168.15.166:8080/midpoint/ws/rest"
MIDPOINT_USER   = "administrator"
APIPERU_BASE    = "https://apiperu.dev/api"
TAX_ID_PREFIX   = "urn:schac:personalUniqueID:pe:DNI:PE:"
NS_UPEU         = "urn:upeu:midpoint:local"
NS_SB           = "urn:sciback:midpoint:person"

# Mínimo de tokens RENIEC que deben aparecer en MidPoint para considerar match
MATCH_THRESHOLD = 0.6

# ─── Logging ──────────────────────────────────────────────────────────────────

_log_file = Path(__file__).parent / f"reniec-enrich-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─── Secretos ─────────────────────────────────────────────────────────────────

def load_secret(env_path: str, key: str) -> str:
    """Lee una variable de un archivo .env estilo shell (KEY=VALUE)."""
    path = Path(os.path.expanduser(env_path))
    if not path.exists():
        sys.exit(f"ERROR: Archivo de secretos no encontrado: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    sys.exit(f"ERROR: Clave '{key}' no encontrada en {path}")


# ─── Utilidades de nombres ────────────────────────────────────────────────────

_TILDES = str.maketrans("ÁÉÍÓÚÜáéíóúüÑñ", "AEIOUUaeiouuNn")


def _normalize(name: str) -> str:
    """Uppercase, sin tildes, sin espacios extra."""
    return re.sub(r"\s+", " ", name.upper().translate(_TILDES)).strip()


def names_match(reniec_given: str, reniec_family: str, mp_given: str, mp_family: str) -> bool:
    """
    True si los nombres RENIEC coinciden suficientemente con los de MidPoint.
    Compara tokens: al menos MATCH_THRESHOLD de los tokens RENIEC deben
    aparecer en el conjunto combinado de tokens MidPoint.
    """
    r_tokens = set(_normalize(f"{reniec_given} {reniec_family}").split())
    m_tokens = set(_normalize(f"{mp_given} {mp_family}").split())
    # Eliminar tokens triviales (1 char)
    r_tokens = {t for t in r_tokens if len(t) > 1}
    m_tokens = {t for t in m_tokens if len(t) > 1}
    if not r_tokens or not m_tokens:
        return False
    overlap = len(r_tokens & m_tokens) / len(r_tokens)
    return overlap >= MATCH_THRESHOLD


# ─── DNI helpers ──────────────────────────────────────────────────────────────

def extract_dni(tax_id: str) -> Optional[str]:
    """Extrae el DNI (8 dígitos) de la URN taxId. None si no es DNI válido."""
    if not tax_id or not tax_id.startswith(TAX_ID_PREFIX):
        return None
    dni = tax_id[len(TAX_ID_PREFIX):]
    return dni if re.fullmatch(r"\d{8}", dni) else None


# ─── MidPoint REST helpers ────────────────────────────────────────────────────

def mp_session(password: str) -> requests.Session:
    s = requests.Session()
    s.auth = (MIDPOINT_USER, password)
    s.headers.update({
        "Content-Type": "application/xml",
        "Accept": "application/json",
    })
    return s


def _build_filter_xml(status_filter: str) -> str:
    if status_filter == "pending":
        return """
        <equal>
          <path xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:dataQualityStatus</path>
          <value>pending</value>
        </equal>"""
    if status_filter == "none":
        return """
        <not><exists>
          <path xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:dataQualityStatus</path>
        </exists></not>"""
    # pending_or_none
    return """
        <or>
          <equal>
            <path xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:dataQualityStatus</path>
            <value>pending</value>
          </equal>
          <not><exists>
            <path xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:dataQualityStatus</path>
          </exists></not>
        </or>"""


def search_users(session: requests.Session, status_filter: str, page_size: int = 500) -> list:
    """Busca usuarios MidPoint según el filtro de status. Devuelve lista de dicts."""
    filter_xml = _build_filter_xml(status_filter)
    all_users: list = []
    offset = 0

    while True:
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<query xmlns="http://prism.evolveum.com/xml/ns/public/query-3">
  <filter>{filter_xml}</filter>
  <paging>
    <orderBy>name</orderBy>
    <offset>{offset}</offset>
    <maxSize>{page_size}</maxSize>
  </paging>
</query>"""

        resp = session.post(f"{MIDPOINT_BASE}/users/search", data=body.encode())
        if resp.status_code != 200:
            log.error(f"Búsqueda falló HTTP {resp.status_code}: {resp.text[:300]}")
            break

        data = resp.json()
        # MidPoint puede envolver la lista en {"object": {"object": [...]}} o {"object": [...]}
        outer = data.get("object", data)
        raw = outer.get("object", []) if isinstance(outer, dict) else outer
        if isinstance(raw, dict):
            raw = [raw]  # un solo resultado
        if not raw:
            break

        all_users.extend(raw)
        log.debug(f"  Página offset={offset}: +{len(raw)} usuarios")
        if len(raw) < page_size:
            break
        offset += page_size

    return all_users


def get_ext(user: dict, field: str) -> Optional[str]:
    """
    Extrae un campo de extension del usuario MidPoint.
    Maneja los formatos de serialización JSON:
      - "field": value
      - "ns#field": value
      - "{ns}field": value
    """
    ext = user.get("extension") or {}
    if not isinstance(ext, dict):
        return None
    for key, val in ext.items():
        local = key.split("#")[-1].split("}")[-1]
        if local == field:
            return val
    return None


def patch_user(session: requests.Session, oid: str, status: str, dry_run: bool) -> bool:
    """Actualiza dataQualityStatus y reniecValidationDate en MidPoint."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<objectModification
    xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"
    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3">
  <itemDelta>
    <modificationType>replace</modificationType>
    <path xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:dataQualityStatus</path>
    <value>{status}</value>
  </itemDelta>
  <itemDelta>
    <modificationType>replace</modificationType>
    <path xmlns:upeu="urn:upeu:midpoint:local">extension/upeu:reniecValidationDate</path>
    <value>{now_iso}</value>
  </itemDelta>
</objectModification>"""

    if dry_run:
        log.info(f"    [DRY-RUN] PATCH {oid} → {status} @ {now_iso}")
        return True

    resp = session.patch(f"{MIDPOINT_BASE}/users/{oid}", data=body.encode())
    if resp.status_code in (200, 204):
        return True
    log.error(f"    PATCH fallido {oid}: HTTP {resp.status_code} — {resp.text[:200]}")
    return False


# ─── apiperu.dev ──────────────────────────────────────────────────────────────

def query_apiperu(dni: str, token: str, dry_run: bool) -> Optional[dict]:
    """
    Consulta apiperu.dev para el DNI dado.
    Devuelve el dict `data` de la respuesta o None si falla.
    En dry_run devuelve datos ficticios para no consumir cuota.
    """
    if dry_run:
        log.info(f"    [DRY-RUN] apiperu.dev/api/dni/{dni} — sin consumir cuota")
        return {
            "nombres": "NOMBRE SIMULADO",
            "apellido_paterno": "APELLIDO",
            "apellido_materno": "MATERNO",
        }

    url = f"{APIPERU_BASE}/dni/{dni}"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
    except requests.RequestException as exc:
        log.error(f"    apiperu.dev excepción para DNI {dni}: {exc}")
        return None

    if resp.status_code == 200:
        payload = resp.json()
        if payload.get("success") and payload.get("data"):
            return payload["data"]
        log.warning(f"    apiperu.dev DNI {dni}: success=false — {resp.text[:120]}")
        return None
    elif resp.status_code == 404:
        log.warning(f"    apiperu.dev DNI {dni}: no encontrado (404)")
        return None
    else:
        log.error(f"    apiperu.dev DNI {dni}: HTTP {resp.status_code} — {resp.text[:120]}")
        return None


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enriquece usuarios MidPoint con validación RENIEC vía apiperu.dev",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplo: python3 reniec-enrich-apiperu.py --dry-run --max 10",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simula sin hacer cambios ni consumir cuota")
    parser.add_argument("--max", type=int, default=100, metavar="N",
                        help="Máximo de usuarios a procesar (default: 100)")
    parser.add_argument("--status", default="pending_or_none",
                        choices=["pending", "none", "pending_or_none"],
                        help="Filtro de dataQualityStatus (default: pending_or_none)")
    args = parser.parse_args()

    log.info("=" * 64)
    log.info("reniec-enrich-apiperu.py — Step 5 calidad de datos RENIEC")
    log.info(f"  dry-run : {args.dry_run}")
    log.info(f"  max     : {args.max}")
    log.info(f"  status  : {args.status}")
    log.info(f"  log     : {_log_file}")
    log.info("=" * 64)

    # Cargar secretos
    mp_pass  = load_secret("~/.secrets/midpoint-upeu.env", "MIDPOINT_ADMIN_PASS")
    api_tok  = load_secret("~/.secrets/apiperu.env", "API_PERU_TOKEN")

    session = mp_session(mp_pass)

    # ── 1. Buscar candidatos ──────────────────────────────────────────────────
    log.info(f"[1/4] Buscando usuarios con dataQualityStatus={args.status} ...")
    candidates = search_users(session, args.status)
    log.info(f"      Candidatos encontrados: {len(candidates)}")

    # ── 2. Filtrar: DNI válido + no manual_override ───────────────────────────
    valid: list[tuple[dict, str]] = []
    skipped_no_dni = 0
    skipped_override = 0

    for user in candidates:
        tax_id = get_ext(user, "taxId")
        if not tax_id:
            skipped_no_dni += 1
            continue
        dni = extract_dni(tax_id)
        if not dni:
            skipped_no_dni += 1
            continue
        current_status = get_ext(user, "dataQualityStatus")
        if current_status == "manual_override":
            skipped_override += 1
            continue
        valid.append((user, dni))

    log.info(f"[2/4] Con DNI válido: {len(valid)} "
             f"(sin DNI: {skipped_no_dni}, manual_override: {skipped_override})")

    to_process = valid[:args.max]
    log.info(f"[3/4] A procesar (limitado a --max={args.max}): {len(to_process)}")
    if not to_process:
        log.info("      Nada que procesar. Fin.")
        return

    # ── 3. Procesar ───────────────────────────────────────────────────────────
    stats = {
        "reniec_validated": 0,
        "mismatch": 0,
        "api_error": 0,
        "patch_ok": 0,
        "patch_error": 0,
    }

    for idx, (user, dni) in enumerate(to_process, 1):
        oid       = user.get("oid", "?")
        username  = user.get("name", "?")
        mp_given  = user.get("givenName") or ""
        mp_family = user.get("familyName") or ""

        log.info(f"  [{idx:3}/{len(to_process)}] {username} | OID:{oid} | DNI:{dni}")

        # Consultar apiperu.dev
        data = query_apiperu(dni, api_tok, args.dry_run)
        if not data:
            stats["api_error"] += 1
            log.warning(f"           → SKIP (sin respuesta apiperu.dev)")
            continue

        # Extraer nombres (apiperu.dev puede variar el nombre de los campos)
        reniec_given  = (data.get("nombres") or data.get("nombre") or "").strip()
        reniec_family = " ".join(filter(None, [
            (data.get("apellido_paterno") or data.get("ap_paterno") or "").strip(),
            (data.get("apellido_materno") or data.get("ap_materno") or "").strip(),
        ]))

        log.info(f"           RENIEC: '{reniec_given} {reniec_family}' "
                 f"| MP: '{mp_given} {mp_family}'")

        # Determinar resultado
        if names_match(reniec_given, reniec_family, mp_given, mp_family):
            new_status = "reniec_validated"
        else:
            new_status = "mismatch"
            log.warning(f"           MISMATCH: nombres no coinciden")

        stats[new_status] += 1

        # PATCH en MidPoint
        if patch_user(session, oid, new_status, args.dry_run):
            stats["patch_ok"] += 1
            log.info(f"           → {new_status} ✓")
        else:
            stats["patch_error"] += 1

    # ── 4. Resumen ────────────────────────────────────────────────────────────
    log.info("=" * 64)
    log.info("[4/4] RESUMEN:")
    log.info(f"  reniec_validated : {stats['reniec_validated']}")
    log.info(f"  mismatch         : {stats['mismatch']}")
    log.info(f"  api_error        : {stats['api_error']}")
    log.info(f"  patch_ok         : {stats['patch_ok']}")
    log.info(f"  patch_error      : {stats['patch_error']}")
    if args.dry_run:
        log.info("  [DRY-RUN] No se realizaron cambios reales ni se consumió cuota.")
    log.info(f"  Log guardado en  : {_log_file}")
    log.info("=" * 64)


if __name__ == "__main__":
    main()

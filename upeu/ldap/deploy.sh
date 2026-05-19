#!/usr/bin/env bash
# deploy.sh — OpenLDAP Identity Cache UPeU
# Servidor: ldap-identity-trust (192.168.15.168)
#
# USO:
#   ./deploy.sh up        — desplegar y configurar todo desde cero
#   ./deploy.sh status    — verificar estado
#   ./deploy.sh schemas   — (re)cargar schemas eduPerson + SCHAC + midPointPerson
#   ./deploy.sh verify    — verificar estructuras LDAP
#   ./deploy.sh down      — bajar contenedores (NO borra datos)
#   ./deploy.sh destroy   — bajar Y borrar volúmenes (DESTRUCTIVO)
#
# PREREQS: sshpass instalado, ~/.secrets/ldap-upeu.env con:
#   LDAP_PROD_HOST, LDAP_PROD_USER, LDAP_PROD_PASS
#   LDAP_ADMIN_PASS, LDAP_MIDPOINT_PASS, LDAP_KEYCLOAK_PASS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HOME/.secrets/ldap-upeu.env"
REMOTE_DIR="/opt/ldap"

# Cargar secretos
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: No existe $ENV_FILE" >&2
    exit 1
fi
source "$ENV_FILE"

SSH="sshpass -p $LDAP_PROD_PASS ssh -o StrictHostKeyChecking=no ${LDAP_PROD_USER}@${LDAP_PROD_HOST}"
SCP="sshpass -p $LDAP_PROD_PASS scp -o StrictHostKeyChecking=no"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
err() { echo "[ERROR] $*" >&2; exit 1; }

cmd_up() {
    log "=== FASE 2: Despliegue OpenLDAP Identity Cache ==="

    # 1. Preparar directorio remoto
    log "Creando estructura en $REMOTE_DIR..."
    $SSH "sudo mkdir -p $REMOTE_DIR/ldifs $REMOTE_DIR/secrets && sudo chown -R ${LDAP_PROD_USER}:${LDAP_PROD_USER} $REMOTE_DIR"

    # 2. Generar password SSHA para service accounts
    log "Generando password hashes SSHA para service accounts..."
    # Usar slappasswd dentro del contenedor (se hace después del primer arranque)
    # Por ahora guardamos las passwords en plaintext en el secreto — bitnami acepta {SSHA} o plaintext
    echo "${LDAP_ADMIN_PASS}" > /tmp/ldap_admin_password.txt
    chmod 600 /tmp/ldap_admin_password.txt

    # 3. Copiar archivos al servidor
    log "Copiando archivos al servidor..."
    $SCP /tmp/ldap_admin_password.txt "${LDAP_PROD_USER}@${LDAP_PROD_HOST}:$REMOTE_DIR/secrets/ldap_admin_password.txt"
    $SSH "chmod 600 $REMOTE_DIR/secrets/ldap_admin_password.txt"

    # Copiar docker-compose.yml
    $SCP "$SCRIPT_DIR/docker-compose.yml" "${LDAP_PROD_USER}@${LDAP_PROD_HOST}:$REMOTE_DIR/docker-compose.yml"

    # Copiar LDIFs base (solo 01 y 02 — los de schema se cargan post-arranque)
    $SCP "$SCRIPT_DIR/ldifs/01-base.ldif" "${LDAP_PROD_USER}@${LDAP_PROD_HOST}:$REMOTE_DIR/ldifs/01-base.ldif"
    $SCP "$SCRIPT_DIR/ldifs/02-midpointperson.ldif" "${LDAP_PROD_USER}@${LDAP_PROD_HOST}:$REMOTE_DIR/ldifs/02-midpointperson.ldif"
    $SCP "$SCRIPT_DIR/ldifs/03-eduperson.ldif" "${LDAP_PROD_USER}@${LDAP_PROD_HOST}:$REMOTE_DIR/ldifs/03-eduperson.ldif"
    $SCP "$SCRIPT_DIR/ldifs/04-schac.ldif" "${LDAP_PROD_USER}@${LDAP_PROD_HOST}:$REMOTE_DIR/ldifs/04-schac.ldif"

    # 4. Arrancar contenedores
    log "Arrancando contenedores..."
    $SSH "cd $REMOTE_DIR && docker compose up -d"

    # 5. Esperar a que OpenLDAP esté sano
    log "Esperando healthcheck OpenLDAP (max 60s)..."
    for i in $(seq 1 12); do
        if $SSH "docker inspect openldap --format '{{.State.Health.Status}}' 2>/dev/null" | grep -q "healthy"; then
            log "OpenLDAP healthy!"
            break
        fi
        if [[ $i -eq 12 ]]; then
            err "OpenLDAP no alcanzó estado healthy en 60s. Ver logs: docker logs openldap"
        fi
        sleep 5
    done

    # 6. Cargar schemas eduPerson + SCHAC + midPointPerson
    cmd_schemas

    # 7. Actualizar passwords de service accounts con SSHA
    log "Configurando passwords de service accounts..."
    $SSH "docker exec openldap ldapmodify -x -H ldap://localhost:1389 \
        -D 'cn=admin,dc=upeu,dc=edu,dc=pe' \
        -w '${LDAP_ADMIN_PASS}' <<'EOF'
dn: cn=midpoint,ou=services,dc=upeu,dc=edu,dc=pe
changetype: modify
replace: userPassword
userPassword: ${LDAP_MIDPOINT_PASS}

dn: cn=keycloak,ou=services,dc=upeu,dc=edu,dc=pe
changetype: modify
replace: userPassword
userPassword: ${LDAP_KEYCLOAK_PASS}
EOF"

    # 8. Verificar estructura
    cmd_verify

    log "=== Despliegue completado ==="
    log "LDAP: ldap://192.168.15.168:389"
    log "phpLDAPadmin: http://192.168.15.168:8081"
    log "Admin DN: cn=admin,dc=upeu,dc=edu,dc=pe"
    log "MidPoint SA: cn=midpoint,ou=services,dc=upeu,dc=edu,dc=pe"
    log "Keycloak SA: cn=keycloak,ou=services,dc=upeu,dc=edu,dc=pe"
    rm -f /tmp/ldap_admin_password.txt
}

cmd_schemas() {
    log "Cargando schemas eduPerson, SCHAC y midPointPerson..."

    # eduPerson — via ldapadd con EXTERNAL (dentro del contenedor como root LDAP)
    if $SSH "docker exec openldap ldapsearch -Y EXTERNAL -H ldapi:/// -b 'cn=eduPerson,cn=schema,cn=config' -s base 2>/dev/null" | grep -q "eduPerson"; then
        log "Schema eduPerson ya existe, saltando."
    else
        log "Cargando eduPerson..."
        $SSH "docker exec openldap ldapadd -Y EXTERNAL -H ldapi:/// -f /ldifs/03-eduperson.ldif" && log "eduPerson cargado OK" || log "WARN: eduPerson ya existia o error"
    fi

    # SCHAC
    if $SSH "docker exec openldap ldapsearch -Y EXTERNAL -H ldapi:/// -b 'cn=schac,cn=schema,cn=config' -s base 2>/dev/null" | grep -q "schac"; then
        log "Schema SCHAC ya existe, saltando."
    else
        log "Cargando SCHAC..."
        $SSH "docker exec openldap ldapadd -Y EXTERNAL -H ldapi:/// -f /ldifs/04-schac.ldif" && log "SCHAC cargado OK" || log "WARN: SCHAC ya existia o error"
    fi

    # midPointPerson
    if $SSH "docker exec openldap ldapsearch -Y EXTERNAL -H ldapi:/// -b 'cn=midpointperson,cn=schema,cn=config' -s base 2>/dev/null" | grep -q "midpointperson"; then
        log "Schema midPointPerson ya existe, saltando."
    else
        log "Cargando midPointPerson..."
        $SSH "docker exec openldap ldapadd -Y EXTERNAL -H ldapi:/// -f /ldifs/02-midpointperson.ldif" && log "midPointPerson cargado OK" || log "WARN: midPointPerson ya existia o error"
    fi

    log "Schemas verificados:"
    $SSH "docker exec openldap ldapsearch -Y EXTERNAL -H ldapi:/// -b 'cn=schema,cn=config' -s one -LLL dn 2>/dev/null | grep cn="
}

cmd_status() {
    log "=== Estado del servicio LDAP ==="
    $SSH "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'openldap|phpldap|NAMES'"
    $SSH "docker inspect openldap --format 'Health: {{.State.Health.Status}}' 2>/dev/null || echo 'Contenedor no existe'"
}

cmd_verify() {
    log "=== Verificación de estructura LDAP ==="

    log "Búsqueda base dc=upeu,dc=edu,dc=pe:"
    $SSH "ldapsearch -x -H ldap://localhost:389 -b 'dc=upeu,dc=edu,dc=pe' -s base '(objectClass=*)' dn 2>/dev/null || \
          docker exec openldap ldapsearch -x -H ldap://localhost:1389 -b 'dc=upeu,dc=edu,dc=pe' -s base '(objectClass=*)' dn" 2>/dev/null || true

    log "OUs existentes:"
    $SSH "ldapsearch -x -H ldap://localhost:389 -b 'dc=upeu,dc=edu,dc=pe' -s one '(objectClass=organizationalUnit)' dn 2>/dev/null || \
          docker exec openldap ldapsearch -x -H ldap://localhost:1389 -b 'dc=upeu,dc=edu,dc=pe' -s one '(objectClass=organizationalUnit)' dn" 2>/dev/null || true

    log "Service accounts:"
    $SSH "ldapsearch -x -H ldap://localhost:389 -b 'ou=services,dc=upeu,dc=edu,dc=pe' '(objectClass=inetOrgPerson)' dn 2>/dev/null || \
          docker exec openldap ldapsearch -x -H ldap://localhost:1389 -b 'ou=services,dc=upeu,dc=edu,dc=pe' '(objectClass=inetOrgPerson)' dn" 2>/dev/null || true

    log "Test bind MidPoint service account:"
    $SSH "ldapsearch -x -H ldap://localhost:389 \
        -D 'cn=midpoint,ou=services,dc=upeu,dc=edu,dc=pe' \
        -w '${LDAP_MIDPOINT_PASS}' \
        -b 'dc=upeu,dc=edu,dc=pe' -s base '(objectClass=*)' dn 2>&1 | head -5" 2>/dev/null || true
}

cmd_down() {
    log "Bajando contenedores (datos preservados)..."
    $SSH "cd $REMOTE_DIR && docker compose down"
}

cmd_destroy() {
    log "ADVERTENCIA: Esto eliminará TODOS los datos LDAP."
    read -r -p "Confirmar destruccion (escribe 'destruir'): " confirm
    if [[ "$confirm" != "destruir" ]]; then
        log "Cancelado."
        exit 0
    fi
    $SSH "cd $REMOTE_DIR && docker compose down -v"
    log "Volúmenes eliminados."
}

# Dispatch
case "${1:-help}" in
    up)       cmd_up ;;
    schemas)  cmd_schemas ;;
    status)   cmd_status ;;
    verify)   cmd_verify ;;
    down)     cmd_down ;;
    destroy)  cmd_destroy ;;
    *)
        echo "USO: $0 {up|schemas|status|verify|down|destroy}"
        exit 1
        ;;
esac

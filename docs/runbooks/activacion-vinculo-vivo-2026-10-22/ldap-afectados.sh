#!/bin/bash
# Desde el Mac (VPN). Solo lectura. uso: ldap-afectados.sh <host 168|169> > ldap-<host>-<pre|post>.tsv
# Estado real en OpenLDAP de los 150 afectados: dn, midPointAccountStatus (ausente = habilitada), ePA.
set -euo pipefail
source ~/.secrets/ldap-upeu.env
H=192.168.15.$1; D=$(cd "$(dirname "$0")" && pwd)
F="(|$(cut -f2 "$D/lotes/afectados.tsv" | tail -n +2 | sed 's/.*/(uid=&)/' | tr -d '\n'))"
ldapsearch -x -LLL -o ldif-wrap=no -H "ldap://$H:${LDAP_PORT:-389}" -D "$LDAP_MIDPOINT_DN" -w "$LDAP_MIDPOINT_PASS" -b "$LDAP_BASE_DN" "$F" \
  dn midPointAccountStatus eduPersonAffiliation eduPersonPrimaryAffiliation \
| awk 'BEGIN{OFS="\t"} /^dn: /{if(dn)print dn,st,epa,pri; dn=substr($0,5); st="(habilitada)"; epa=""; pri=""} /^midPointAccountStatus: /{st=$2} /^eduPersonAffiliation: /{epa=epa (epa?",":"") $2} /^eduPersonPrimaryAffiliation: /{pri=$2} END{if(dn)print dn,st,epa,pri}' | sort

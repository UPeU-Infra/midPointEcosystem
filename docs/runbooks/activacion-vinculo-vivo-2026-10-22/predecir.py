#!/usr/bin/env python3
"""Simulador fuera de MidPoint del diseno activacion-vinculo-vivo (22-oct). uso: predecir.py <dir con ds.tsv>
ds.tsv = salida de ds.sql. Modelo: R1/R2/R3 retiran 217/215/216 sin cuenta Oracle viva enlazada; L pasa
active->archived (terminationDate o evidencia laboral) o ->draft si no queda item vivo; ACT borra DISABLED si
queda item vivo; effective = ENABLED si lifecycle active y admin != DISABLED. No modela: smartwifiGuest ni el
rol de bibliotecario en Koha, ni la completitud de perfil de L (solo baja de active, nunca sube)."""
import sys, collections, re, json
S=sys.argv[1]
U=[]
for l in open(S+'/ds.tsv'):
    f=l.rstrip('\n').split('\t')
    if not re.match(r'^[0-9a-f]{8}-',f[0]): continue
    k=['oid','name','lc','adm','eff','w','s','a','term','termS','mot','idp','wl','wd','wattr','sl','sd','sattr','al','aattr','ldap','koha','zam','emp','arch','prim','aff']
    u=dict(zip(k,f)); 
    for x in ('wl','wd','sl','sd','al','emp'): u[x]=int(u[x])
    U.append(u)
NONPERSON={'00000000-0000-0000-0000-000000000002'}
def nonperson(u): return u['oid'] in NONPERSON or 'service-account' in u['arch'] or 'System user' in u['arch']
C=collections.Counter
res=[]
for u in U:
    np_=nonperson(u)
    nw=u['w'] if u['wl']>0 else ''
    ns=u['s'] if u['sl']>0 else ''
    na=u['a'] if u['al']>0 else ''
    if np_: nw,ns,na=u['w'],u['s'],u['a']
    live=bool(u['w'] or u['s'] or u['a']); nlive=bool(nw or ns or na)
    lc=u['lc']; nlc=lc
    if not np_ and not nlive and lc=='active':
        nlc='archived' if (u['term'] or u['emp']) else 'draft'
    nadm=u['adm']
    if not np_ and u['adm']=='DISABLED' and nlive: nadm=''
    neff='ENABLED' if (nlc in ('active','') and nadm!='DISABLED') else 'DISABLED'
    if lc=='' : neff=u['eff']
    u.update(nw=nw,ns=ns,na=na,live=live,nlive=nlive,nlc=nlc,nadm=nadm,neff=neff,
             ret=''.join(x for x,o,n in (('W',u['w'],nw),('S',u['s'],ns),('A',u['a'],na)) if o and not n))
    res.append(u)
json.dump(res,open(S+'/res.json','w'))
def key(u): return (u['lc'] or '(null)', 'W' if u['w'] else '-', 'S' if u['s'] else '-', 'A' if u['a'] else '-')
print('== tabla: clase(lc,vivos hoy) -> eff hoy -> eff nuevo')
t=C((key(u),u['eff'],u['neff'],u['nlc']) for u in res)
for k,v in sorted(t.items()): print(k,v)
print('== retracciones', C(u['ret'] for u in res if u['ret']))
print('== cambios eff', C((u['eff'],u['neff']) for u in res if u['eff']!=u['neff']))
print('== cambios lc', C((u['lc'],u['nlc']) for u in res if u['lc']!=u['nlc']))
print('== cambios adm', C((u['adm'],u['nadm']) for u in res if u['adm']!=u['nadm']))

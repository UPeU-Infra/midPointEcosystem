#!/usr/bin/env python3
# uso: graph.py get <upn_o_id>...   -> JSON por usuario con SELECT fijo (solo lectura)
import os,sys,json,urllib.request,urllib.parse,time
SEL="id,userPrincipalName,mail,displayName,accountEnabled,givenName,surname,employeeId,employeeType,jobTitle,department,officeLocation,city,country,companyName,usageLocation"
def env():
    d={}
    for l in open(os.path.expanduser('~/.secrets/upeu-infra.env')):
        l=l.strip()
        if l.startswith('export '): l=l[7:]
        if '=' in l and not l.startswith('#'):
            k,v=l.split('=',1); d[k]=v.strip().strip('"').strip("'")
    return d
def token():
    e=env()
    data=urllib.parse.urlencode({'client_id':e['MIDPOINT_AZ_CLIENT_ID'],'client_secret':e['MIDPOINT_AZ_CLIENT_SECRET'],'scope':'https://graph.microsoft.com/.default','grant_type':'client_credentials'}).encode()
    r=urllib.request.urlopen(f"https://login.microsoftonline.com/{e['MIDPOINT_AZ_TENANT_ID']}/oauth2/v2.0/token",data)
    return json.load(r)['access_token']
def get(t,u):
    for i in range(4):
        try:
            req=urllib.request.Request(f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(u)}?$select={SEL}",headers={'Authorization':'Bearer '+t})
            return json.load(urllib.request.urlopen(req))
        except urllib.error.HTTPError as ex:
            if ex.code==404: return {'_error':404,'_q':u}
            if ex.code in (429,503,504): time.sleep(2*(i+1)); continue
            return {'_error':ex.code,'_q':u}
    return {'_error':'retries','_q':u}
if __name__=='__main__':
    t=token()
    out=[get(t,u) for u in sys.argv[2:]]
    for o in out: o.pop('@odata.context',None)
    print(json.dumps(out,ensure_ascii=False,indent=0 if len(out)>1 else 1))

import urllib.request, urllib.parse, json, sys, time

TENANT=sys.argv[1]; CID=sys.argv[2]; SECRET=sys.argv[3]

def token():
    data=urllib.parse.urlencode({"client_id":CID,"client_secret":SECRET,
        "scope":"https://graph.microsoft.com/.default","grant_type":"client_credentials"}).encode()
    r=urllib.request.urlopen("https://login.microsoftonline.com/%s/oauth2/v2.0/token"%TENANT,data)
    return json.load(r)["access_token"]

tok=token()
fields="id,displayName,userPrincipalName,mail,accountEnabled,createdDateTime,signInActivity,proxyAddresses,givenName,surname"
url="https://graph.microsoft.com/v1.0/users?$select=%s&$top=500"%fields
out=[]; pages=0; t0=time.time()
while url:
    req=urllib.request.Request(url, headers={"Authorization":"Bearer "+tok})
    try:
        r=urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        if e.code==401:
            tok=token(); continue
        if e.code==429:
            time.sleep(5); continue
        print("HTTP",e.code,e.read()[:200].decode(),file=sys.stderr); break
    d=json.load(r)
    for u in d.get("value",[]):
        sia=u.get("signInActivity") or {}
        out.append({
            "id":u.get("id"),"upn":u.get("userPrincipalName"),"mail":u.get("mail"),
            "display":u.get("displayName"),"given":u.get("givenName"),"surname":u.get("surname"),
            "enabled":u.get("accountEnabled"),"created":u.get("createdDateTime"),
            "lastInteractive":sia.get("lastSignInDateTime"),
            "lastNonInteractive":sia.get("lastNonInteractiveSignInDateTime"),
            "proxy":u.get("proxyAddresses") or []
        })
    pages+=1
    if pages%10==0: print("...%d users en %ds"%(len(out),time.time()-t0),file=sys.stderr)
    url=d.get("@odata.nextLink")
json.dump(out,open("/tmp/entra_users.json","w"))
print("TOTAL usuarios:",len(out),"en %ds"%int(time.time()-t0))

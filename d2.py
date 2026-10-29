import requests,re
B="https://mi-web-python-fin0.onrender.com"
s=requests.Session(); s.headers["User-Agent"]="Mozilla/5.0"
p=s.post(B+"/login",data={"username":"xx_zz","password":"yy_zz"},allow_redirects=False)
print("status",p.status_code,"| loc",p.headers.get("Location"),"| len",len(p.text),"| form",'name="password"' in p.text,"| cookies",len(s.cookies))
open("f.html","w").write(p.text)
t=" ".join(re.sub(r"<[^>]+>"," ",p.text).split())
print("TEXTO:",t[:400])

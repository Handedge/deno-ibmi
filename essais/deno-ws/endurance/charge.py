"""Endurance test of the Deno web service on IBMI, run from LINUXBUILD.

Constant rate (10 requests/s by default) over a mix of routes, for a given duration (48 h by
default). Every minute, one line in charge.csv: request count, errors, p50/p95/p99/max latencies.
Detailed errors go to erreurs.log (the first 100, then one in 100).
Stops by itself at the end of the duration, or as soon as a STOP file exists in the output directory.

Usage: python3 charge.py [--hote 192.0.2.82] [--debit 10] [--heures 48] [--sortie ~/endurance]
"""
import argparse
import concurrent.futures as cf
import pathlib
import random
import ssl
import threading
import time
import urllib.error
import urllib.request

# (weight, name, relative url, https): mostly light requests, some Db2 and HTTPS, one Db2 wait
ROUTES = [
    (55, "bonjour", "/bonjour?nom=endurance", False),
    (15, "db2_systeme", "/db2/systeme", False),
    (10, "db2_tables", "/db2/tables?schema=QSYS2&limite=20", False),
    (3, "db2_attente", "/db2/attente?secondes=1", False),
    (2, "db2_pool", "/db2/pool", False),
    (15, "https_bonjour", "/bonjour?nom=endurance-tls", True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hote", default="192.0.2.82")
    ap.add_argument("--debit", type=float, default=10.0)
    ap.add_argument("--heures", type=float, default=48.0)
    ap.add_argument("--sortie", default=str(pathlib.Path.home() / "endurance"))
    a = ap.parse_args()
    sortie = pathlib.Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    stop = sortie / "STOP"
    stop.unlink(missing_ok=True)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False          # local deno-ibmi CA: we measure stability, not the PKI
    ctx.verify_mode = ssl.CERT_NONE
    poids = [r[0] for r in ROUTES]
    verrou = threading.Lock()
    minute = {"n": 0, "err": 0, "lat": [], "par_route": {}}
    total = {"n": 0, "err": 0}
    nb_err_log = [0]
    flog = (sortie / "erreurs.log").open("a", buffering=1)

    def requete(route):
        _, nom, chemin, tls = route
        url = f"{'https' if tls else 'http'}://{a.hote}:{3444 if tls else 3081}{chemin}"
        t0 = time.perf_counter()
        err = None
        try:
            with urllib.request.urlopen(url, timeout=30, context=ctx if tls else None) as r:
                r.read()
                if r.status != 200:
                    err = f"HTTP {r.status}"
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001 — any failure counts as an error
            err = f"{type(e).__name__}: {e}"
        dt = (time.perf_counter() - t0) * 1000
        with verrou:
            minute["n"] += 1
            minute["lat"].append(dt)
            pr = minute["par_route"].setdefault(nom, [0, 0])
            pr[0] += 1
            if err:
                minute["err"] += 1
                pr[1] += 1
                nb_err_log[0] += 1
                if nb_err_log[0] <= 100 or nb_err_log[0] % 100 == 0:
                    flog.write(f"{time.strftime('%F %T')} {nom} {err} ({dt:.0f} ms) [erreur n°{nb_err_log[0]}]\n")

    def p(lat, q):
        return lat[min(len(lat) - 1, int(q * len(lat)))] if lat else 0

    csv = sortie / "charge.csv"
    if not csv.exists():
        csv.write_text("horodatage;requetes;erreurs;p50_ms;p95_ms;p99_ms;max_ms;erreurs_par_route\n")
    fin = time.time() + a.heures * 3600
    pas = 1.0 / a.debit
    prochaine = time.time()
    prochaine_minute = time.time() + 60
    print(f"charge : {a.debit} req/s vers {a.hote} pendant {a.heures} h, sortie {sortie}", flush=True)
    with cf.ThreadPoolExecutor(64) as ex:
        while time.time() < fin and not stop.exists():
            ex.submit(requete, random.choices(ROUTES, poids)[0])
            prochaine += pas
            attente = prochaine - time.time()
            if attente > 0:
                time.sleep(attente)
            elif attente < -5:              # server overloaded: do not try to catch up forever
                prochaine = time.time()
            if time.time() >= prochaine_minute:
                prochaine_minute += 60
                with verrou:
                    lat = sorted(minute["lat"])
                    n, e, pr = minute["n"], minute["err"], minute["par_route"]
                    minute.update(n=0, err=0, lat=[], par_route={})
                total["n"] += n
                total["err"] += e
                detail = ",".join(f"{k}={v[1]}" for k, v in sorted(pr.items()) if v[1])
                with csv.open("a") as f:
                    f.write(f"{time.strftime('%F %T')};{n};{e};{p(lat, .5):.0f};{p(lat, .95):.0f};"
                            f"{p(lat, .99):.0f};{(lat[-1] if lat else 0):.0f};{detail}\n")
    print(f"fin : {total['n']} requêtes, {total['err']} erreurs", flush=True)


if __name__ == "__main__":
    main()

"""Endurance test of the Deno web service on IBMI, run from LINUXBUILD.

Constant rate (10 requests/s by default) over a mix of routes, for a given duration (48 h by
default). Every minute, one line in charge.csv: request count, errors, p50/p95/p99/max latencies.
Detailed errors go to erreurs.log (the first 100, then one in 100).
Stops by itself at the end of the duration, or as soon as a STOP file exists in the output directory.

Usage: python3 load.py [--hote 192.0.2.82] [--debit 10] [--heures 48] [--sortie ~/endurance]
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
    ap.add_argument("--host", default="192.0.2.82")
    ap.add_argument("--rate", type=float, default=10.0)
    ap.add_argument("--hours", type=float, default=48.0)
    ap.add_argument("--output", default=str(pathlib.Path.home() / "endurance"))
    a = ap.parse_args()
    output = pathlib.Path(a.output)
    output.mkdir(parents=True, exist_ok=True)
    stop = output / "STOP"
    stop.unlink(missing_ok=True)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False          # local deno-ibmi CA: we measure stability, not the PKI
    ctx.verify_mode = ssl.CERT_NONE
    weights = [r[0] for r in ROUTES]
    lock = threading.Lock()
    minute = {"n": 0, "err": 0, "lat": [], "per_route": {}}
    total = {"n": 0, "err": 0}
    error_count = [0]
    error_log = (output / "errors.log").open("a", buffering=1)

    def send_request(route):
        _, name, path, tls = route
        url = f"{'https' if tls else 'http'}://{a.host}:{3444 if tls else 3081}{path}"
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
        with lock:
            minute["n"] += 1
            minute["lat"].append(dt)
            pr = minute["per_route"].setdefault(name, [0, 0])
            pr[0] += 1
            if err:
                minute["err"] += 1
                pr[1] += 1
                error_count[0] += 1
                if error_count[0] <= 100 or error_count[0] % 100 == 0:
                    error_log.write(f"{time.strftime('%F %T')} {name} {err} ({dt:.0f} ms) [error #{error_count[0]}]\n")

    def p(lat, q):
        return lat[min(len(lat) - 1, int(q * len(lat)))] if lat else 0

    csv = output / "load.csv"
    if not csv.exists():
        csv.write_text("timestamp;requests;errors;p50_ms;p95_ms;p99_ms;max_ms;errors_per_route\n")
    end = time.time() + a.hours * 3600
    interval = 1.0 / a.rate
    next_time = time.time()
    next_minute = time.time() + 60
    print(f"load: {a.rate} req/s to {a.host} for {a.hours} h, output {output}", flush=True)
    with cf.ThreadPoolExecutor(64) as ex:
        while time.time() < end and not stop.exists():
            ex.submit(send_request, random.choices(ROUTES, weights)[0])
            next_time += interval
            wait = next_time - time.time()
            if wait > 0:
                time.sleep(wait)
            elif wait < -5:              # server overloaded: do not try to catch up forever
                next_time = time.time()
            if time.time() >= next_minute:
                next_minute += 60
                with lock:
                    lat = sorted(minute["lat"])
                    n, e, pr = minute["n"], minute["err"], minute["per_route"]
                    minute.update(n=0, err=0, lat=[], per_route={})
                total["n"] += n
                total["err"] += e
                detail = ",".join(f"{k}={v[1]}" for k, v in sorted(pr.items()) if v[1])
                with csv.open("a") as f:
                    f.write(f"{time.strftime('%F %T')};{n};{e};{p(lat, .5):.0f};{p(lat, .95):.0f};"
                            f"{p(lat, .99):.0f};{(lat[-1] if lat else 0):.0f};{detail}\n")
    print(f"done: {total['n']} requests, {total['err']} errors", flush=True)


if __name__ == "__main__":
    main()

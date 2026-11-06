"""Runs the Deno unit tests (tests/unit/*_test.ts) the same way as tests/unit/mod.rs.

Same per-file command as the official runner (deno test --config tests/config/deno.json
--no-lock --unstable-net --unstable-vsock --location=http://127.0.0.1:4545/ --no-prompt
[file-specific options] -A <file>), test_server started beforehand,
fresh DENO_DIR per file. The result of each case is read from the deno test JUnit report.
Usage: python3 unit.py <deno root (git v2.9.8)> <deno> <test_server> <output.jsonl> [parallelism] [comma,separated,prefixes]
"""
import concurrent.futures as cf
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

RACINE = pathlib.Path(sys.argv[1]).resolve()
DENO = sys.argv[2]
SERVEUR = sys.argv[3]
SORTIE = pathlib.Path(sys.argv[4])
PARALLELE = int(sys.argv[5]) if len(sys.argv) > 5 else 4
FILTRE = sys.argv[6] if len(sys.argv) > 6 else ""
DELAI = 600          # seconds per file (longest on x64: kv_test, 50 s)
TRAVAIL = pathlib.Path(tempfile.mkdtemp(prefix="unitdeno-"))


def options(nom):
    o = []
    if nom == "bundle_test":
        o.append("--unstable-bundle")
    if nom == "cron_test":
        o.append("--unstable-cron")
    if nom.startswith("kv_"):
        o.append("--unstable-kv")
    if nom == "webgpu_test":
        o.append("--unstable-webgpu")
    if nom in ("worker_permissions_test", "worker_test", "umask_test"):
        o.append("--unstable-worker-options")
    if nom == "websocket_test":
        o.append("--cert=" + str(RACINE / "tests/testdata/tls/RootCA.pem"))
    if nom == "tls_sni_test":
        o.append("--unsafely-ignore-certificate-errors")
    return o


def executer(f):
    nom = f.stem
    junit = TRAVAIL / (nom + ".xml")
    dd = TRAVAIL / ("dd-" + nom)
    # Per-file TMPDIR, always deleted afterwards: under PASE, deleting the current
    # directory fails (EBUSY), and worker_test left a copy of the binary (288 MB) in /tmp
    # on every run — 102 copies, 29 GB, ASP at 96 % on 2026-11-03.
    tmp = TRAVAIL / ("tmp-" + nom)
    tmp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DENO_DIR=str(dd), TMPDIR=str(tmp), DENO_NO_UPDATE_CHECK="1", NO_COLOR="1",
               NPM_CONFIG_REGISTRY="http://localhost:4260/", JSR_URL="http://localhost:4250/")
    cmd = [DENO, "test", "--config", str(RACINE / "tests/config/deno.json"), "--no-lock",
           "--unstable-net", "--unstable-vsock", "--location=http://127.0.0.1:4545/",
           "--no-prompt"] + options(nom) + ["-A", "--junit-path=" + str(junit), str(f)]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=str(RACINE), env=env, capture_output=True, timeout=DELAI)
        code, sortie = r.returncode, (r.stdout[-3000:] + r.stderr[-3000:]).decode(errors="replace")
    except subprocess.TimeoutExpired as e:
        code, sortie = None, ((e.stdout or b"")[-3000:] + (e.stderr or b"")[-3000:]).decode(errors="replace")
    cas = {}
    if junit.exists():
        try:
            for tc in ET.parse(junit).iter("testcase"):
                etat = "ok"
                if tc.find("failure") is not None or tc.find("error") is not None:
                    el = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
                    etat = "FAILED: " + ((el.get("message") or el.text or "")[:300])
                elif tc.find("skipped") is not None:
                    etat = "ignored"
                cas[tc.get("classname", "") + " > " + tc.get("name", "")] = etat
        except ET.ParseError:
            pass
    shutil.rmtree(dd, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return {"fichier": nom, "code": code, "duree": round(time.time() - t0, 1), "cas": cas,
            "sortie": sortie if code != 0 else ""}


def main():
    prefixes = tuple(FILTRE.split(",")) if FILTRE else ("",)   # comma-separated list of prefixes
    fichiers = sorted(p for p in (RACINE / "tests/unit").glob("*_test.ts") if p.stem.startswith(prefixes))
    srv = subprocess.Popen([SERVEUR], cwd=str(RACINE / "tests/testdata"), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    t0 = time.time()
    prets = 0                                    # 39 servers, each one prints "ready:…"
    while prets < 39 and time.time() - t0 < 180:
        l = srv.stdout.readline()
        if not l:
            break
        prets += l.startswith(b"ready:")
    # drain the server output continuously, otherwise a full pipe blocks it
    import threading
    threading.Thread(target=lambda: [None for _ in iter(srv.stdout.readline, b"")], daemon=True).start()
    print(f"test_server : {prets}/39 prêts en {time.time() - t0:.1f} s ; {len(fichiers)} fichiers, "
          f"parallélisme {PARALLELE}", flush=True)
    debut = time.time()
    try:
        with SORTIE.open("w") as out, cf.ThreadPoolExecutor(PARALLELE) as ex:
            for i, r in enumerate(ex.map(executer, fichiers), 1):
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush()
                ok = sum(1 for v in r["cas"].values() if v == "ok")
                print(f"{i}/{len(fichiers)} {r['fichier']:40} code={r['code']} {ok}/{len(r['cas'])} {r['duree']} s", flush=True)
    finally:
        srv.kill()
        shutil.rmtree(TRAVAIL, ignore_errors=True)
    print("FIN", int(time.time() - debut), "s", flush=True)


if __name__ == "__main__":
    main()

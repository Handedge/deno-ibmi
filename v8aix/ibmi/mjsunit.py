"""Runs the V8 mjsunit suite with the IBM i (PASE) d8, like tools/run-tests.py.

Per-test command (D8TestCase + mjsunit/testcfg.py):
  d8 --test [mjsunit.js] [// Files: files] <test> --random-seed=N --nohard-abort <// Flags:>
Pass: exit code 0 (d8 handles --throws). Results in JSON Lines.
Usage: python3.9 mjsunit.py <v8 root (test/, tools/)> <d8> <output.jsonl> [parallelism] [filter]
"""
import concurrent.futures as cf
import json
import os
import pathlib
import re
import subprocess
import sys
import time

RACINE = pathlib.Path(sys.argv[1])
D8 = sys.argv[2]
SORTIE = pathlib.Path(sys.argv[3])
PARALLELE = int(sys.argv[4]) if len(sys.argv) > 4 else 6
FILTRE = sys.argv[5] if len(sys.argv) > 5 else ""
DELAI = 120                      # s (run-tests: 60 in release, x4 for slow tests)
SUITE = RACINE / "test/mjsunit"

FLAGS = re.compile(r"//\s+Flags:(.*)")
FILES = re.compile(r"//\s+Files:(.*)")
ENV = re.compile(r"//\s+Environment Variables:(.*)")
NO_HARNESS = re.compile(r"^// NO HARNESS$", re.M)
EXCLUS = {"mjsunit.js", "mjsunit_numfuzz.js"}


def tests():
    for p in sorted(SUITE.rglob("*")):
        if p.suffix not in (".js", ".mjs") or p.name in EXCLUS:
            continue
        rel = p.relative_to(SUITE).as_posix()
        if FILTRE and not rel.startswith(FILTRE):
            continue
        # a test's helper files (imported modules...) are not tests:
        # run-tests takes every .js/.mjs, except those excluded by the status file (SKIP)
        yield p, rel


def commande(p):
    src = p.read_text(errors="replace")
    flags = []
    for m in FLAGS.finditer(src):
        flags += m.group(1).split()
    fichiers = []
    for m in FILES.finditer(src):
        fichiers += [str(RACINE / f) for f in m.group(1).split()]
    env = dict(os.environ)
    for m in ENV.finditer(src):
        for paire in m.group(1).split():
            k, _, v = paire.partition("=")
            env[k] = v
    harnais = [] if NO_HARNESS.search(src) else [str(SUITE / "mjsunit.js")]
    cmd = [D8, "--test"] + harnais + fichiers + [str(p), "--random-seed=123", "--nohard-abort"] + flags
    return cmd, env, "--throws" in flags


def executer(p, rel):
    cmd, env, negatif = commande(p)
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=DELAI, env=env, cwd=str(RACINE))
        code = r.returncode
        sortie = (r.stdout[-600:] + r.stderr[-600:]).decode(errors="replace")
        # --throws is handled by d8 itself (exit code 0 if the expected exception was thrown)
        etat = "PASS" if code == 0 else ("CRASH" if code < 0 else "FAIL")
    except subprocess.TimeoutExpired:
        code, sortie, etat = None, "", "TIMEOUT"
    return {"test": rel, "etat": etat, "code": code, "duree": round(time.time() - t0, 2),
            "sortie": sortie if etat != "PASS" else ""}


def main():
    liste = list(tests())
    print(f"{len(liste)} tests, parallélisme {PARALLELE}", flush=True)
    debut = time.time()
    compte = {}
    with SORTIE.open("w") as f, cf.ThreadPoolExecutor(PARALLELE) as ex:
        for i, res in enumerate(ex.map(lambda t: executer(*t), liste), 1):
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            compte[res["etat"]] = compte.get(res["etat"], 0) + 1
            if i % 250 == 0:
                f.flush()
                print(f"{i}/{len(liste)} {compte} {int(time.time() - debut)} s", flush=True)
    print("FIN", compte, f"{int(time.time() - debut)} s", flush=True)


if __name__ == "__main__":
    main()

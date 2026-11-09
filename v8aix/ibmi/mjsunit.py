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

ROOT = pathlib.Path(sys.argv[1])
D8 = sys.argv[2]
OUTPUT = pathlib.Path(sys.argv[3])
PARALLELISM = int(sys.argv[4]) if len(sys.argv) > 4 else 6
FILTER = sys.argv[5] if len(sys.argv) > 5 else ""
TIMEOUT = 120                      # s (run-tests: 60 in release, x4 for slow tests)
SUITE = ROOT / "test/mjsunit"

FLAGS = re.compile(r"//\s+Flags:(.*)")
FILES = re.compile(r"//\s+Files:(.*)")
ENV = re.compile(r"//\s+Environment Variables:(.*)")
NO_HARNESS = re.compile(r"^// NO HARNESS$", re.M)
EXCLUDED = {"mjsunit.js", "mjsunit_numfuzz.js"}


def tests():
    for p in sorted(SUITE.rglob("*")):
        if p.suffix not in (".js", ".mjs") or p.name in EXCLUDED:
            continue
        rel = p.relative_to(SUITE).as_posix()
        if FILTER and not rel.startswith(FILTER):
            continue
        # a test's helper files (imported modules...) are not tests:
        # run-tests takes every .js/.mjs, except those excluded by the status file (SKIP)
        yield p, rel


def command(p):
    src = p.read_text(errors="replace")
    flags = []
    for m in FLAGS.finditer(src):
        flags += m.group(1).split()
    files = []
    for m in FILES.finditer(src):
        files += [str(ROOT / f) for f in m.group(1).split()]
    env = dict(os.environ)
    for m in ENV.finditer(src):
        for pair in m.group(1).split():
            k, _, v = pair.partition("=")
            env[k] = v
    harness = [] if NO_HARNESS.search(src) else [str(SUITE / "mjsunit.js")]
    cmd = [D8, "--test"] + harness + files + [str(p), "--random-seed=123", "--nohard-abort"] + flags
    return cmd, env, "--throws" in flags


def run_test(p, rel):
    cmd, env, negative = command(p)
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, env=env, cwd=str(ROOT))
        code = r.returncode
        output = (r.stdout[-600:] + r.stderr[-600:]).decode(errors="replace")
        # --throws is handled by d8 itself (exit code 0 if the expected exception was thrown)
        status = "PASS" if code == 0 else ("CRASH" if code < 0 else "FAIL")
    except subprocess.TimeoutExpired:
        code, output, status = None, "", "TIMEOUT"
    return {"test": rel, "etat": status, "code": code, "duree": round(time.time() - t0, 2),
            "sortie": output if status != "PASS" else ""}


def main():
    test_list = list(tests())
    print(f"{len(test_list)} tests, parallelism {PARALLELISM}", flush=True)
    start = time.time()
    counts = {}
    with OUTPUT.open("w") as f, cf.ThreadPoolExecutor(PARALLELISM) as ex:
        for i, res in enumerate(ex.map(lambda t: run_test(*t), test_list), 1):
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            counts[res["etat"]] = counts.get(res["etat"], 0) + 1
            if i % 250 == 0:
                f.flush()
                print(f"{i}/{len(test_list)} {counts} {int(time.time() - start)} s", flush=True)
    print("DONE", counts, f"{int(time.time() - start)} s", flush=True)


if __name__ == "__main__":
    main()

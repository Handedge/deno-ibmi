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

ROOT = pathlib.Path(sys.argv[1]).resolve()
DENO = sys.argv[2]
TEST_SERVER = sys.argv[3]
OUTPUT = pathlib.Path(sys.argv[4])
PARALLELISM = int(sys.argv[5]) if len(sys.argv) > 5 else 4
FILTER = sys.argv[6] if len(sys.argv) > 6 else ""
TIMEOUT = 600          # seconds per file (longest on x64: kv_test, 50 s)
WORK_DIR = pathlib.Path(tempfile.mkdtemp(prefix="unitdeno-"))


def options(name):
    o = []
    if name == "bundle_test":
        o.append("--unstable-bundle")
    if name == "cron_test":
        o.append("--unstable-cron")
    if name.startswith("kv_"):
        o.append("--unstable-kv")
    if name == "webgpu_test":
        o.append("--unstable-webgpu")
    if name in ("worker_permissions_test", "worker_test", "umask_test"):
        o.append("--unstable-worker-options")
    if name == "websocket_test":
        o.append("--cert=" + str(ROOT / "tests/testdata/tls/RootCA.pem"))
    if name == "tls_sni_test":
        o.append("--unsafely-ignore-certificate-errors")
    return o


def run_file(f):
    name = f.stem
    junit = WORK_DIR / (name + ".xml")
    dd = WORK_DIR / ("dd-" + name)
    # Per-file TMPDIR, always deleted afterwards: under PASE, deleting the current
    # directory fails (EBUSY), and worker_test left a copy of the binary (288 MB) in /tmp
    # on every run — 102 copies, 29 GB, ASP at 96 % on 2026-11-03.
    tmp = WORK_DIR / ("tmp-" + name)
    tmp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DENO_DIR=str(dd), TMPDIR=str(tmp), DENO_NO_UPDATE_CHECK="1", NO_COLOR="1",
               NPM_CONFIG_REGISTRY="http://localhost:4260/", JSR_URL="http://localhost:4250/")
    cmd = [DENO, "test", "--config", str(ROOT / "tests/config/deno.json"), "--no-lock",
           "--unstable-net", "--unstable-vsock", "--location=http://127.0.0.1:4545/",
           "--no-prompt"] + options(name) + ["-A", "--junit-path=" + str(junit), str(f)]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, timeout=TIMEOUT)
        code, output = r.returncode, (r.stdout[-3000:] + r.stderr[-3000:]).decode(errors="replace")
    except subprocess.TimeoutExpired as e:
        code, output = None, ((e.stdout or b"")[-3000:] + (e.stderr or b"")[-3000:]).decode(errors="replace")
    cases = {}
    if junit.exists():
        try:
            for tc in ET.parse(junit).iter("testcase"):
                status = "ok"
                if tc.find("failure") is not None or tc.find("error") is not None:
                    el = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
                    status = "FAILED: " + ((el.get("message") or el.text or "")[:300])
                elif tc.find("skipped") is not None:
                    status = "ignored"
                cases[tc.get("classname", "") + " > " + tc.get("name", "")] = status
        except ET.ParseError:
            pass
    shutil.rmtree(dd, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return {"fichier": name, "code": code, "duree": round(time.time() - t0, 1), "cas": cases,
            "sortie": output if code != 0 else ""}


def main():
    prefixes = tuple(FILTER.split(",")) if FILTER else ("",)   # comma-separated list of prefixes
    files = sorted(p for p in (ROOT / "tests/unit").glob("*_test.ts") if p.stem.startswith(prefixes))
    srv = subprocess.Popen([TEST_SERVER], cwd=str(ROOT / "tests/testdata"), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    t0 = time.time()
    ready = 0                                    # 39 servers, each one prints "ready:…"
    while ready < 39 and time.time() - t0 < 180:
        l = srv.stdout.readline()
        if not l:
            break
        ready += l.startswith(b"ready:")
    # drain the server output continuously, otherwise a full pipe blocks it
    import threading
    threading.Thread(target=lambda: [None for _ in iter(srv.stdout.readline, b"")], daemon=True).start()
    print(f"test_server: {ready}/39 ready in {time.time() - t0:.1f} s; {len(files)} files, "
          f"parallelism {PARALLELISM}", flush=True)
    start = time.time()
    try:
        with OUTPUT.open("w") as out, cf.ThreadPoolExecutor(PARALLELISM) as ex:
            for i, r in enumerate(ex.map(run_file, files), 1):
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush()
                ok = sum(1 for v in r["cas"].values() if v == "ok")
                print(f"{i}/{len(files)} {r['fichier']:40} code={r['code']} {ok}/{len(r['cas'])} {r['duree']} s", flush=True)
    finally:
        srv.kill()
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    print("DONE", int(time.time() - start), "s", flush=True)


if __name__ == "__main__":
    main()

#!/QOpenSys/usr/bin/sh
# Smoke test of an installed deno RPM (any IBM i profile, ssh or QP2TERM).
#   [KEEP=1] sh test-rpm.sh [port]
# Checks: version, eval, TypeScript, Intl, npm-free node: module, Deno.serve, Db2 through
# /QOpenSys/pkgs/share/deno/db2.ts, deno compile (the Db2 script as a single executable). Prints PASS/FAIL per check; exit code = number of failures.
# KEEP=1: the temporary directory /tmp/deno-rpm-test.<pid> is kept (machines where nothing is deleted).
PORT=${1:-3990}
D=/QOpenSys/pkgs/bin/deno
T=/tmp/deno-rpm-test.$$
mkdir -p $T && cd $T || exit 1
export DENO_DIR=$T/cache
ulimit -d 8388608 2>/dev/null
failures=0
check() {   # check <label> <command...>
  label=$1; shift
  if out=$("$@" 2>&1); then echo "PASS $label: $(echo "$out" | tail -1 | cut -c1-90)"
  else echo "FAIL $label: $(echo "$out" | tail -3 | tr '\n' ' ' | cut -c1-200)"; failures=$((failures + 1)); fi
}
check "version" $D --version
check "eval" $D eval 'console.log(Deno.build.os, Deno.build.arch, 6 * 7)'
check "typescript" sh -c "echo 'const n: number = 41; console.log(\"ts\", n + 1)' > t.ts && $D run t.ts"
check "intl" $D eval 'console.log(new Intl.NumberFormat("en-US").format(1234567.891), new Date(0).toISOString())'
check "node:crypto" $D eval 'import { createHash } from "node:crypto"; console.log(createHash("sha256").update("x").digest("hex").slice(0, 12))'
cat > serve.ts <<EOF
const ac = new AbortController();
Deno.serve({ port: $PORT, hostname: "127.0.0.1", signal: ac.signal, onListen() {} }, () => new Response("hello"));
const r = await fetch("http://127.0.0.1:$PORT/");
console.log("serve", r.status, await r.text());
ac.abort();
EOF
check "serve" $D run --allow-net serve.ts
cat > db2.ts <<'EOF'
import { Db2 } from "/QOpenSys/pkgs/share/deno/db2.ts";
const db = new Db2();
console.log("db2", JSON.stringify(db.query("SELECT CURRENT USER AS U, CURRENT SERVER AS S FROM SYSIBM.SYSDUMMY1")[0]));
db.close();
EOF
check "db2" $D run --allow-ffi db2.ts
# deno compile: single executable, run without deno or XPG_SUS_ENV
check "compile" sh -c "$D compile --quiet --allow-ffi --output app db2.ts && unset XPG_SUS_ENV && ./app"
cd /
[ "${KEEP:-0}" = 1 ] && echo "kept: $T" || rm -rf $T
echo "failures: $failures"
exit $failures

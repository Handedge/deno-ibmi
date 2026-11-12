#!/bin/bash
# Builds Deno for IBM i IN A SINGLE COMMAND, from LINUXBUILD, starting from a fresh clone of Deno.
#
#   bash build/build.sh [--tests quick|full|none] [--rpm] [--rpm-release N]
#     --tests        quick: no unit tests (no package); full: the default
#     --rpm          also build the deno RPM (/QOpenSys/pkgs layout) once the full tests pass
#     --rpm-release  RPM release number (default 1)
#
# Pipeline: prepared tree (prepare-tree.sh) → snapshot generator cross-compiled → linked and
# run on IBM i → Deno cross-compiled with that snapshot → linked on IBM i → tests.
# Output: package /QOpenSys/opt/denoibmi/livraisons/deno-ibmi-<version>-<date> on IBMI (if the full
# tests pass); installed by an administrator with: sh ibmi/deploy.sh <package>.
# Access to IBMI: DENOBUILD profile (no special authorities), key ~/.ssh/id_denobuild restricted to
# the LINUXBUILD address. Blocking threshold for the full tests: ≥ 99.5 % of applicable cases and
# 0 Deno-specific discrepancy (deno-tests/compare-unit.py).
set -euo pipefail
TESTS=full
RPM=0
RPM_RELEASE=1
while [ $# -gt 0 ]; do
  case $1 in
    --tests) TESTS=${2:-full}; shift 2 ;;
    --rpm) RPM=1; shift ;;
    --rpm-release) RPM_RELEASE=${2:?release number}; shift 2 ;;
    *) echo "ERROR: unknown option $1"; sed -n '4,7p' "$0"; exit 1 ;;
  esac
done
REPO=$(cd "$(dirname "$0")/.." && pwd)
R=/QOpenSys/opt/denoibmi
RUST=${RUST_VERSION:-1.99.1}
PROFILE=ibmi-rel
IBMI=${IBMI_SSH:-DENOBUILD@192.0.2.82}   # IBM i profile@host (IBMI_SSH variable)
KEY=$HOME/.ssh/id_denobuild
SSH="ssh -i $KEY -o BatchMode=yes -o ServerAliveInterval=30 $IBMI"
SCP="scp -q -i $KEY -o BatchMode=yes"
OUT=$HOME/construction-deno
mkdir -p "$OUT"
LOG=$OUT/build-$(date +%Y%m%d-%H%M).log
exec > >(tee "$LOG") 2>&1
start=$(date +%s)
step() { echo; echo "== $(date +%T) [$(( $(date +%s) - start ))s] $*"; }

step "0. safeguards: access to IBMI and ASP"
asp=$($SSH '/QOpenSys/pkgs/bin/db2util -o space "select system_asp_used from qsys2.system_status_info"' | tr -d '"' | awk '$1 ~ /^[0-9.]+$/ {print int($1)}')
echo "IBMI ASP: $asp %"
[ -n "$asp" ] && [ "$asp" -lt 75 ] || { echo "ERROR: ASP at $asp %: build refused (threshold 75 %)"; exit 1; }

step "1. build tree (fresh clone, patches)"
bash "$REPO/build/prepare-tree.sh"

step "2. scripts and JS sources copied to IBMI"
tar cf - -C "$REPO" ibmi deno-tests packaging publication/public examples/deno-db2/db2.ts | $SSH 'mkdir -p /QOpenSys/opt/deno-ibmi && cd /QOpenSys/opt/deno-ibmi && tar xf -'
(cd "$R/deno" && find ext runtime cli libs -type f \( -name "*.js" -o -name "*.ts" -o -name "*.mjs" -o -name "*.cjs" -o -name "*.json" \) \
   -not -path "*/tests/*" -not -path "*/testdata/*" -not -path "*/node_modules/*" | tar cf - -T -) \
  | $SSH "cd $R/deno && tar xf -"

source "$REPO/linux/cross/cross-env.sh"
cargo_aix() { (cd "$R/deno" && cargo +"$RUST" build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix --profile $PROFILE -j 28 "$@"); }
link_on_ibmi() {   # link_on_ibmi <binary> <crate of the .lien command>
  local link_cmd
  link_cmd=$(ls -t "$R/deno/target/powerpc64-ibm-aix/$PROFILE/deps/$2"-*.lien | head -1)
  "$REPO/linux/cross/pack-link.sh" "$(readlink -f "$link_cmd")" | $SSH "cat > $R/croise/lien.tar.gz"
  $SSH "/QOpenSys/usr/bin/sh /QOpenSys/opt/deno-ibmi/ibmi/link-sbmjob.sh $1 $PROFILE"
}

step "3. snapshot generator: cross-compiled, then linked on IBM i"
cargo_aix -p generer-snapshot
link_on_ibmi generer_snapshot generer_snapshot

step "4. snapshot produced by the IBM i V8"
$SSH "ulimit -d 8388608; export XPG_SUS_ENV=ON NO_COLOR=1; rm -rf /tmp/rustpoc/snapshot && \
      $R/croise/generer_snapshot /tmp/rustpoc/snapshot > /tmp/rustpoc/snapshot.log 2>&1 && \
      cd /tmp/rustpoc/snapshot && /QOpenSys/usr/bin/tar cf - ." > "$OUT/snapshot.tar"
rm -rf "$R/snapshot-genere" && mkdir -p "$R/snapshot-genere" && tar xf "$OUT/snapshot.tar" -C "$R/snapshot-genere"
ls "$R/snapshot-genere"; [ -s "$R/snapshot-genere/CLI_SNAPSHOT.bin" ] || { echo "ERROR: snapshot missing"; exit 1; }

step "5. Deno: cross-compiled with this snapshot, then linked on IBM i"
DENO_SNAPSHOT_PREBUILT=$R/snapshot-genere cargo_aix -p deno --no-default-features --features v8,deno_core/include_icu_data
link_on_ibmi deno deno
# denort: the runtime that "deno compile" appends the program to (shipped next to deno)
DENO_SNAPSHOT_PREBUILT=$R/snapshot-genere cargo_aix -p denort --features deno_core/include_icu_data
link_on_ibmi denort denort

step "6. quick test"
$SSH "ulimit -d 8388608; export XPG_SUS_ENV=ON DENO_NO_UPDATE_CHECK=1 NO_COLOR=1 DENO_DIR=/tmp/rustpoc/dd-rapide; D=$R/croise/deno; \
      \$D --version | head -1 && \
      \$D eval 'console.log(\"eval\", Deno.build.os, Intl.NumberFormat(\"fr-FR\").format(1234.5), Deno.osUptime() > 0)' && \
      \$D eval 'import { createHash } from \"node:crypto\"; console.log(\"node:crypto\", createHash(\"sha1\").update(\"x\").digest(\"hex\").slice(0, 8))'; \
      rc=\$?; rm -rf /tmp/rustpoc/dd-rapide; exit \$rc"

if [ "$TESTS" = full ]; then
  step "7. full unit tests as DENOTEST (≈ 6 min)"
  RUN_NAME=build-$(date +%H%M)
  # CALL QP2SHELL (not QSH CMD): PASE runs in the job itself, which allows threads (ALWMLTTHD);
  # under QSH, the child job without QIBM_MULTI_THREADED made test_server hang at startup
  $SSH "/QOpenSys/usr/bin/system \"SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/env' 'RUN_NAME=$RUN_NAME' '/QOpenSys/usr/bin/sh' '/QOpenSys/opt/deno-ibmi/deno-tests/unit-denotest.sh')) JOB(TESTSDENO) USER(DENOTEST) INLLIBL(*JOBD) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)\""
  for i in $(seq 1 120); do $SSH "grep -q 'DONE $RUN_NAME' /tmp/rustpoc/$RUN_NAME.log 2>/dev/null" && break; sleep 15; done
  $SSH "cat /tmp/rustpoc/$RUN_NAME.jsonl" > "$OUT/$RUN_NAME.jsonl"
  python3 "$REPO/deno-tests/compare-unit.py" "$OUT/$RUN_NAME.jsonl" "$REPO/deno-tests/results-x64.jsonl" > "$OUT/$RUN_NAME.txt"
  sed -n '/^also passing/p;/^applicable cases/,/^$/p' "$OUT/$RUN_NAME.txt"
  rate=$(sed -n 's/^applicable cases.*= \([0-9.]*\) %.*/\1/p' "$OUT/$RUN_NAME.txt")
  deno_specific=$(sed -n 's/^   of which Deno-specific on IBM i: \([0-9]*\)/\1/p' "$OUT/$RUN_NAME.txt")
  python3 -c "import sys; sys.exit(0 if float('$rate') >= 99.5 and int('$deno_specific') == 0 else 1)" \
    || { echo "ERROR: threshold not met: $rate % of applicable cases, $deno_specific Deno-specific discrepancy(ies)"; exit 1; }
  echo "threshold met: $rate % of applicable cases, 0 Deno-specific discrepancy"

  step "8. release package (installed with ibmi/deploy.sh, by an administrator)"
  commit=$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo "unversioned copy")
  deno_source="${DENO_VERSION:-v2.9.8} ($(git -C "$R/deno" log -1 --format='%h of %cs'))"   # main carries version number 2.9.8
  package_out=$($SSH "/QOpenSys/usr/bin/sh /QOpenSys/opt/deno-ibmi/ibmi/package-release.sh '$commit' '$rate % of applicable cases, 0 Deno-specific discrepancy' '$deno_source'")
  echo "$package_out"
  package=$(echo "$package_out" | sed -n 's|^package ready: .*/||p')

  if [ "$RPM" = 1 ]; then
    step "9. deno RPM (/QOpenSys/pkgs layout, release $RPM_RELEASE)"
    version=$(echo "$package" | cut -d- -f3)
    # third-party licenses of the crates actually linked into this binary
    (cd "$R/deno" && cargo +"$RUST" tree -q -p deno --no-default-features --features v8,deno_core/include_icu_data \
       -e normal,build --target powerpc64-ibm-aix --prefix none --format "{p}|{l}") \
      | python3 "$REPO/packaging/third-party-licenses.py" "$version" \
      | $SSH "cat > /QOpenSys/opt/deno-ibmi/packaging/THIRD_PARTY_LICENSES.md"
    $SSH "/QOpenSys/usr/bin/sh /QOpenSys/opt/deno-ibmi/ibmi/make-rpm.sh '$package' '$RPM_RELEASE' '$commit'"
  fi
fi

step "DONE in $(( ($(date +%s) - start) / 60 )) min: $R/croise/deno on IBMI (log: $LOG)"

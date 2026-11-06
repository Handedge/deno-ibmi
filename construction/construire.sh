#!/bin/bash
# Builds Deno for IBM i IN A SINGLE COMMAND, from LINUXBUILD, starting from a fresh clone of Deno.
#
#   bash construction/construire.sh [--tests rapide|complet|aucun]      (default: complet)
#
# Pipeline: prepared tree (preparer-arbre.sh) → snapshot generator cross-compiled → linked and
# run on IBM i → Deno cross-compiled with that snapshot → linked on IBM i → tests.
# Output: package /QOpenSys/opt/denoibmi/livraisons/deno-ibmi-<version>-<date> on IBMI (if the full
# tests pass); installed by an administrator with: sh ibmi/livrer.sh <package>.
# Access to IBMI: DENOBUILD profile (no special authorities), key ~/.ssh/id_denobuild restricted to
# the LINUXBUILD address. Blocking threshold for the full tests: ≥ 99.5 % of applicable cases and
# 0 Deno-specific discrepancy (tests-deno/comparer-unit.py).
set -euo pipefail
TESTS=complet
[ "${1:-}" = "--tests" ] && TESTS=${2:-complet}
DEPOT=$(cd "$(dirname "$0")/.." && pwd)
R=/QOpenSys/opt/denoibmi
RUST=${RUST_VERSION:-1.99.1}
PROFIL=ibmi-rel
IBMI=${IBMI_SSH:-DENOBUILD@192.0.2.82}   # IBM i profile@host (IBMI_SSH variable)
CLE=$HOME/.ssh/id_denobuild
SSH="ssh -i $CLE -o BatchMode=yes -o ServerAliveInterval=30 $IBMI"
SCP="scp -q -i $CLE -o BatchMode=yes"
OUT=$HOME/construction-deno
mkdir -p "$OUT"
JOURNAL=$OUT/construire-$(date +%Y%m%d-%H%M).log
exec > >(tee "$JOURNAL") 2>&1
debut=$(date +%s)
etape() { echo; echo "== $(date +%T) [$(( $(date +%s) - debut ))s] $*"; }

etape "0. garde-fous : accès à IBMI et ASP"
asp=$($SSH '/QOpenSys/pkgs/bin/db2util -o space "select system_asp_used from qsys2.system_status_info"' | tr -d '"' | awk '$1 ~ /^[0-9.]+$/ {print int($1)}')
echo "ASP de IBMI : $asp %"
[ -n "$asp" ] && [ "$asp" -lt 75 ] || { echo "ASP à $asp % : construction refusée (seuil 75 %)"; exit 1; }

etape "1. arbre de compilation (clone neuf, correctifs)"
bash "$DEPOT/construction/preparer-arbre.sh"

etape "2. dépôt de scripts et sources JS sur IBMI"
tar cf - -C "$DEPOT" ibmi tests-deno | $SSH 'mkdir -p /QOpenSys/opt/deno-ibmi && cd /QOpenSys/opt/deno-ibmi && tar xf -'
(cd "$R/deno" && find ext runtime cli libs -type f \( -name "*.js" -o -name "*.ts" -o -name "*.mjs" -o -name "*.cjs" -o -name "*.json" \) \
   -not -path "*/tests/*" -not -path "*/testdata/*" -not -path "*/node_modules/*" | tar cf - -T -) \
  | $SSH "cd $R/deno && tar xf -"

source "$DEPOT/linux/croise/env-croise.sh"
cargo_aix() { (cd "$R/deno" && cargo +"$RUST" build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix --profile $PROFIL -j 28 "$@"); }
lier() {   # lier <binary> <crate of the .lien command>
  local lien
  lien=$(ls -t "$R/deno/target/powerpc64-ibm-aix/$PROFIL/deps/$2"-*.lien | head -1)
  "$DEPOT/linux/croise/emballer-lien.sh" "$(readlink -f "$lien")" | $SSH "cat > $R/croise/lien.tar.gz"
  $SSH "/QOpenSys/usr/bin/sh /QOpenSys/opt/deno-ibmi/ibmi/lier-sbmjob.sh $1 $PROFIL"
}

etape "3. générateur de snapshot : compilation croisée puis lien sur IBM i"
cargo_aix -p generer-snapshot
lier generer_snapshot generer_snapshot

etape "4. snapshot fabriqué par le V8 d'IBM i"
$SSH "ulimit -d 8388608; export XPG_SUS_ENV=ON NO_COLOR=1; rm -rf /tmp/rustpoc/snapshot && \
      $R/croise/generer_snapshot /tmp/rustpoc/snapshot > /tmp/rustpoc/snapshot.log 2>&1 && \
      cd /tmp/rustpoc/snapshot && /QOpenSys/usr/bin/tar cf - ." > "$OUT/snapshot.tar"
rm -rf "$R/snapshot-genere" && mkdir -p "$R/snapshot-genere" && tar xf "$OUT/snapshot.tar" -C "$R/snapshot-genere"
ls "$R/snapshot-genere"; [ -s "$R/snapshot-genere/CLI_SNAPSHOT.bin" ] || { echo "snapshot absent"; exit 1; }

etape "5. Deno : compilation croisée avec ce snapshot, puis lien sur IBM i"
DENO_SNAPSHOT_PREBUILT=$R/snapshot-genere cargo_aix -p deno --no-default-features --features v8,deno_core/include_icu_data
lier deno deno

etape "6. test rapide"
$SSH "ulimit -d 8388608; export XPG_SUS_ENV=ON DENO_NO_UPDATE_CHECK=1 NO_COLOR=1 DENO_DIR=/tmp/rustpoc/dd-rapide; D=$R/croise/deno; \
      \$D --version | head -1 && \
      \$D eval 'console.log(\"eval\", Deno.build.os, Intl.NumberFormat(\"fr-FR\").format(1234.5), Deno.osUptime() > 0)' && \
      \$D eval 'import { createHash } from \"node:crypto\"; console.log(\"node:crypto\", createHash(\"sha1\").update(\"x\").digest(\"hex\").slice(0, 8))'; \
      rc=\$?; rm -rf /tmp/rustpoc/dd-rapide; exit \$rc"

if [ "$TESTS" = complet ]; then
  etape "7. tests unitaires complets sous DENOTEST (≈ 6 min)"
  NOM=construire-$(date +%H%M)
  # CALL QP2SHELL (not QSH CMD): PASE runs in the job itself, which allows threads (ALWMLTTHD);
  # under QSH, the child job without QIBM_MULTI_THREADED made test_server hang at startup
  $SSH "/QOpenSys/usr/bin/system \"SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/env' 'NOM=$NOM' '/QOpenSys/usr/bin/sh' '/QOpenSys/opt/deno-ibmi/tests-deno/unit-denotest.sh')) JOB(TESTSDENO) USER(DENOTEST) INLLIBL(*JOBD) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)\""
  for i in $(seq 1 120); do $SSH "grep -q 'FIN $NOM' /tmp/rustpoc/$NOM.log 2>/dev/null" && break; sleep 15; done
  $SSH "cat /tmp/rustpoc/$NOM.jsonl" > "$OUT/$NOM.jsonl"
  python3 "$DEPOT/tests-deno/comparer-unit.py" "$OUT/$NOM.jsonl" "$DEPOT/tests-deno/resultats-x64.jsonl" > "$OUT/$NOM.txt"
  sed -n '/^réussis aussi/p;/^cas applicables/,/^$/p' "$OUT/$NOM.txt"
  taux=$(sed -n 's/^cas applicables.*= \([0-9.]*\) %.*/\1/p' "$OUT/$NOM.txt")
  propres=$(sed -n 's/^   dont propres à Deno sur IBM i : \([0-9]*\)/\1/p' "$OUT/$NOM.txt")
  python3 -c "import sys; sys.exit(0 if float('$taux') >= 99.5 and int('$propres') == 0 else 1)" \
    || { echo "SEUIL NON ATTEINT : $taux % applicables, $propres écart(s) propre(s) à Deno"; exit 1; }
  echo "seuil atteint : $taux % des cas applicables, 0 écart propre à Deno"

  etape "8. paquet de livraison (installation : ibmi/livrer.sh, par un administrateur)"
  commit=$(git -C "$DEPOT" rev-parse --short HEAD 2>/dev/null || echo "copie non versionnée")
  source_deno="${VERSION_DENO:-v2.9.8} ($(git -C "$R/deno" log -1 --format='%h du %cs'))"   # main carries version number 2.9.8
  $SSH "/QOpenSys/usr/bin/sh /QOpenSys/opt/deno-ibmi/ibmi/emballer-livraison.sh '$commit' '$taux % des cas applicables, 0 écart propre à Deno' '$source_deno'"
fi

etape "TERMINÉ en $(( ($(date +%s) - debut) / 60 )) min : $R/croise/deno sur IBMI (journal : $JOURNAL)"

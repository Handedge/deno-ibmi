#!/QOpenSys/usr/bin/sh
# Stores the Deno binary that has just passed the tests (croise/deno) in a versioned package,
# ready to deliver: /QOpenSys/opt/denoibmi/livraisons/deno-ibmi-<version>-<date>/
#   deno, libpaseat.a, INFO (version, provenance, test results), SHA256SUMS
# Called by construction/construire.sh (DENOBUILD profile) once the test threshold is met.
# Usage: sh emballer-livraison.sh <deno-ibmi repository commit> "<test results>"
set -e
C=/QOpenSys/opt/denoibmi/croise
L=/QOpenSys/opt/denoibmi/livraisons
GARDER=3                                   # packages kept (≈ 290 MB each, ASP)
V=$($C/deno --version | head -1 | awk '{print $2}')
NOM=deno-ibmi-$V-$(date +%Y%m%d-%H%M)
D=$L/$NOM
mkdir -p $D
cp $C/deno $D/deno
cp /QOpenSys/opt/rust/runtime/libpaseat.a $D/libpaseat.a
cat > $D/INFO <<EOF
paquet        : $NOM
deno          : $($C/deno --version | tr '\n' ' ')
construit le  : $(date '+%Y-%m-%d %H:%M:%S') sur $(hostname)
par           : $(id -un) (construction/construire.sh, LINUXBUILD)
source Deno   : ${3:-v2.9.8}
dépôt         : deno-ibmi ${1:-?}
tests         : ${2:-non lancés}
EOF
cd $D && /QOpenSys/pkgs/bin/sha256sum deno libpaseat.a INFO > SHA256SUMS
# cleanup: keep the $GARDER most recent packages
cd $L && ls -d deno-ibmi-* 2>/dev/null | sort -r | sed "1,${GARDER}d" | while read v; do rm -rf "$v"; echo "ancien paquet supprimé : $v"; done
echo "paquet prêt : $D"
cat $D/INFO

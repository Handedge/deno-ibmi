#!/QOpenSys/usr/bin/sh
# Stores the Deno binary that has just passed the tests (croise/deno) in a versioned package,
# ready to deliver: /QOpenSys/opt/denoibmi/livraisons/deno-ibmi-<version>-<date>/
#   deno, denort, libpaseat.a, INFO (version, provenance, test results), SHA256SUMS
# Called by build/build.sh (DENOBUILD profile) once the test threshold is met.
# Usage: sh package-release.sh <deno-ibmi repository commit> "<test results>"
set -e
C=/QOpenSys/opt/denoibmi/croise
L=/QOpenSys/opt/denoibmi/livraisons
KEEP=3                                   # packages kept (≈ 290 MB each, ASP)
V=$($C/deno --version | head -1 | awk '{print $2}')
PACKAGE=deno-ibmi-$V-$(date +%Y%m%d-%H%M)
D=$L/$PACKAGE
mkdir -p $D
cp $C/deno $D/deno
cp $C/denort $D/denort                   # runtime of "deno compile"
cp /QOpenSys/opt/rust/runtime/libpaseat.a $D/libpaseat.a
cat > $D/INFO <<EOF
package       : $PACKAGE
deno          : $($C/deno --version | tr '\n' ' ')
built         : $(date '+%Y-%m-%d %H:%M:%S') on $(hostname)
by            : $(id -un) (build/build.sh, LINUXBUILD)
deno source   : ${3:-v2.9.8}
repository    : deno-ibmi ${1:-?}
tests         : ${2:-not run}
EOF
cd $D && /QOpenSys/pkgs/bin/sha256sum deno denort libpaseat.a INFO > SHA256SUMS
# cleanup: keep the $KEEP most recent packages
cd $L && ls -d deno-ibmi-* 2>/dev/null | sort -r | sed "1,${KEEP}d" | while read old; do rm -rf "$old"; echo "old package deleted: $old"; done
echo "package ready: $D"
cat $D/INFO

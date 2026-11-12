#!/QOpenSys/usr/bin/sh
# Builds the deno RPM (/QOpenSys/pkgs layout) from a release package that has passed the tests.
# Called by build/build.sh --rpm (DENOBUILD profile), after package-release.sh.
# Usage: sh make-rpm.sh <release package> <rpm release number> <deno-ibmi commit>
#   e.g. sh make-rpm.sh deno-ibmi-2.9.8-20261109-1102 1 9025390
# Output: /QOpenSys/opt/denoibmi/livraisons/rpm/RPMS/ppc64/deno-<version>-<release>.ppc64.rpm
# Requires: rpm-build (yum install rpm-build, once, by an administrator).
set -e
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
L=/QOpenSys/opt/denoibmi/livraisons
REPO=$(cd "$(dirname "$0")/.." && pwd)
P=$L/${1:?release package}
RELEASE=${2:?rpm release number}
COMMIT=${3:-unknown}
TOP=$L/rpm
[ -x "$P/deno" ] || { echo "ERROR: $P/deno not found"; exit 1; }
command -v rpmbuild >/dev/null || { echo "ERROR: rpmbuild not found (yum install rpm-build)"; exit 1; }
VERSION=$(XPG_SUS_ENV=ON "$P/deno" --version | head -1 | awk '{print $2}')

rm -rf $TOP/SOURCES $TOP/BUILD $TOP/BUILDROOT
mkdir -p $TOP/SOURCES $TOP/SPECS $TOP/RPMS $TOP/BUILD
S=$TOP/SOURCES
cp $P/deno $P/denort $P/libpaseat.a $S/
cp /QOpenSys/opt/rust/runtime/libunwind.a $S/          # IBM Open XL C/C++ runtime
cp $REPO/packaging/deno-launcher.sh $REPO/examples/deno-db2/db2.ts $S/
cp $REPO/publication/public/LICENSE $REPO/publication/public/THIRD_PARTY_NOTICES.md $S/
cp $REPO/packaging/THIRD_PARTY_LICENSES.md $S/
cp $REPO/packaging/deno.spec $TOP/SPECS/
# build information, without any machine name
cat > $S/BUILD-INFO <<EOF
deno         : $(XPG_SUS_ENV=ON "$P/deno" --version | tr '\n' ' ')
deno-ibmi    : https://github.com/Handedge/deno-ibmi (commit $COMMIT)
rpm          : deno-$VERSION-$RELEASE.ppc64
built        : $(date '+%Y-%m-%d')
tests        : $(sed -n 's/^tests *: //p' $P/INFO)
EOF

rpmbuild --target ppc64-ibmi7.5 --define "_topdir $TOP" --define "deno_version $VERSION" --define "deno_release $RELEASE" \
         --define "deno_ibmi_commit $COMMIT" -bb $TOP/SPECS/deno.spec
R=$(ls -t $TOP/RPMS/ppc64/deno-$VERSION-$RELEASE*.ppc64.rpm | head -1)
ls -l $R
rpm -qip $R | head -12
echo "rpm ready: $R"

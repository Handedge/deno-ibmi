#!/QOpenSys/usr/bin/sh
# Installs Rust (IBM Open SDK for Rust on AIX, Community Edition) under IBM i PASE.
#
# Usage (in batch; multithreading is required for DNS):
#   SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/sh'
#          '/QOpenSys/opt/deno-ibmi/ibmi/installer-rust.sh' '<runtime Open XL .tar.Z>'))
#          ALWMLTTHD(*YES)
#
# Prerequisites: Internet access (AIX Toolbox, IBM i yum repositories); the IBM
# Open XL C/C++ runtime for AIX (Fix Central, xlc.rte.17.1.4.02...) uploaded to the IFS.
# Result: /QOpenSys/opt/rust/{1.96,current,runtime,cargo,rustenv.sh}
set -e
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
VER=${RUST_VER:-1.96}
BASE=/QOpenSys/opt/rust
DEPOT=$(cd "$(dirname "$0")/.." && pwd)
RTE=$1
TMP=/tmp/rust-install.$$
[ -f "$RTE" ] || { echo "runtime Open XL introuvable : $RTE"; exit 1; }
mkdir -p $BASE/runtime $BASE/cargo $TMP/rpms $TMP/root

echo "== 1. paquets yum"
yum install -y gcc12 gcc12-cplusplus ninja-build cmake git make-gnu libatomic1 \
    coreutils-gnu grep-gnu sed-gnu ca-certificates-mozilla python39 > $TMP/yum.log 2>&1 \
    || { tail -20 $TMP/yum.log; exit 1; }

echo "== 2. RPM Rust $VER (AIX Toolbox, AIX 7.2)"
U=https://public.dhe.ibm.com/aix/freeSoftware/aixtoolbox/RPMS/ppc-7.2/rust
LISTE=$(curl -sf $U/ | grep -o "href=\"[^\"]*$VER[^\"]*\.rpm\"" | sed 's/href=//;s/"//g' \
        | grep -E "^(rust|cargo|rustfmt|clippy)$VER-|^rust$VER-(std-static|community-license)-" | sort -V         | awk '{ cle = $0; sub(/-[0-9]+\.aix.*$/, "", cle); dernier[cle] = $0 } END { for (c in dernier) print dernier[c] }')
# (a single build per package: the most recent one published by IBM)
cd $TMP/rpms
for p in $LISTE; do curl -sSf -O $U/$p; echo "  $p"; done

echo "== 3. extraction (sans la base rpm d'IBM i ; le cpio de PASE ne lit pas ce format)"
for f in $TMP/rpms/*.rpm; do
  rpm2cpio $f > $TMP/p.cpio
  python3.9 - $TMP/p.cpio $TMP/root <<'PY'
import os, sys
src, racine = sys.argv[1], sys.argv[2]
d = open(src, "rb").read(); i = 0
while True:
    h = d[i:i + 110]
    f = [int(h[6 + 8 * k:14 + 8 * k], 16) for k in range(13)]
    mode, fsz, nsz = f[1], f[6], f[11]
    nom = d[i + 110:i + 110 + nsz - 1].decode(); i = (i + 110 + nsz + 3) & ~3
    data = d[i:i + fsz]; i = (i + fsz + 3) & ~3
    if nom == "TRAILER!!!":
        break
    p = os.path.join(racine, nom.lstrip("./")); t = mode & 0o170000
    if t == 0o040000:
        os.makedirs(p, exist_ok=True)
    elif t == 0o120000:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.lexists(p):
            os.symlink(data.decode(), p)
    else:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(data); os.chmod(p, mode & 0o7777)
PY
done
rm -rf $BASE/$VER
cp -Rp $TMP/root/opt/freeware/lib/RustSDK/$VER $BASE/$VER
ln -sfn $BASE/$VER $BASE/current

echo "== 4. runtime IBM Open XL C/C++ (libc++, libc++abi, libunwind)"
mkdir -p $TMP/rte && cd $TMP/rte
uncompress -c "$RTE" | tar xf -
for r in libc++ libc++abi libunwind; do
  python3.9 $DEPOT/outils/bff_extract.py $r.rte $TMP/rte/$r > /dev/null
  cp $TMP/rte/$r/usr/lpp/xlC/lib/*.a $BASE/runtime/
done

echo "== 5. bibliotheques yum au format archive(membre) attendu (hors du -L de rustc)"
mkdir -p $BASE/runtime-outils
for l in libz.so.1 libatomic.so.1; do
  a=${l%%.so*}.a; mkdir -p $TMP/so/$l; cd $TMP/so/$l
  ar -X64 x /QOpenSys/pkgs/lib/$l shr_64.o && mv shr_64.o $l
  rm -f $BASE/runtime-outils/$a; ar -X64 -q $BASE/runtime-outils/$a $l
done

echo "== 6. cargo : imports OpenSSL de yum (une seule instance de libcrypto)"
B=$BASE/$VER/bin
[ -f $B/.cargo.orig.ibm ] || cp -p $B/.cargo.orig $B/.cargo.orig.ibm
cp -p $B/.cargo.orig.ibm $B/.cargo.orig
python3.9 $DEPOT/outils/xcoff_imports.py $B/.cargo.orig \
  libssl.a:libssl.so.3=libssl.so.3:shr_64.o libcrypto.a:libcrypto.so.3=libcrypto.so.3:shr_64.o \
  --libpath $BASE/runtime:/QOpenSys/pkgs/lib:/usr/lib:/lib > /dev/null

echo "== 7. scripts IBM : runtime et bibliotheques yum en tete de LIBPATH"
for f in cargo cargo-clippy cargo-fmt clippy-driver rustc rustdoc rustfmt; do
  [ -f $B/$f ] || continue
  sed "s#^export LIBPATH=/usr/lpp/xlC/lib:#export LIBPATH=$BASE/runtime:/QOpenSys/pkgs/lib:/usr/lpp/xlC/lib:#" $B/$f > $B/$f.new
  mv $B/$f.new $B/$f; chmod 755 $B/$f
done

echo "== 8. certificats (cert.pem d'IBM i parfois vide)"
cat /QOpenSys/var/lib/ca-certificates/openssl/*.pem > $BASE/ca-bundle.pem 2>/dev/null \
  || for c in /QOpenSys/var/lib/ca-certificates/openssl/*; do cat $c; done > $BASE/ca-bundle.pem
echo "  $(grep -c 'BEGIN' $BASE/ca-bundle.pem) certificats"

echo "== 9. environnement et libpaseat"
cp $DEPOT/ibmi/rustenv.sh $BASE/rustenv.sh
sh $DEPOT/ibmi/paseat/construire.sh

echo "== 10. verification"
. $BASE/rustenv.sh
rustc -vV | head -2
cargo -V
cd $TMP && rustc -O $RUSTFLAGS $DEPOT/essais/rmtest.rs -o rmtest && ./rmtest
cd / && rm -rf $TMP
echo "Rust installe dans $BASE"

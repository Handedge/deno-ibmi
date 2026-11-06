#!/QOpenSys/usr/bin/sh
# Prepares the Deno build tree for a native build on IBM i:
#   /QOpenSys/opt/denoibmi/{deno, crates-src, patches, wamr-factice, correctifs.py}
# then applies the patches. Run in a multithreaded batch job (Internet access).
# Prerequisites: Rust installed (installer-rust.sh), repository copied to /QOpenSys/opt/deno-ibmi.
set -e
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
DEPOT=$(cd "$(dirname "$0")/.." && pwd)
R=/QOpenSys/opt/denoibmi
VERSION_DENO=v2.9.8
mkdir -p $R/crates-src $R/patches $R/wamr-factice /tmp/rustpoc

echo "== sources de Deno $VERSION_DENO"
[ -d $R/deno/.git ] || git clone -q --depth 1 --branch $VERSION_DENO https://github.com/denoland/deno.git $R/deno
cp $DEPOT/deno/Cargo.toml.ibmi $R/deno/Cargo.toml
cp $DEPOT/deno/Cargo.lock.ibmi $R/deno/Cargo.lock

echo "== crates a corriger (telechargees depuis crates.io)"
for c in byteorder:1.5.0 v8x:149.4.0-rc.4 aws-lc-sys:0.40.0 aws-lc-sys:0.46.0 nix:0.29.0 nix:0.30.1 \
         libz-sys:1.1.20 libsqlite3-sys:0.38.1 netif:0.1.6 rustix:0.38.34 quinn-udp:0.5.9 \
         libffi-sys:4.1.0 libnghttp2:1.68.0 libuv-sys-lite:1.48.4 dlopen2:0.6.1 memmap2:0.9.5 \
         libsui:0.16.4 rustyline:17.0.0 open:5.1.2; do
  nom=${c%%:*}; ver=${c#*:}
  [ -d $R/crates-src/$nom-$ver ] && continue
  curl -sSfL "https://crates.io/api/v1/crates/$nom/$ver/download" -o /tmp/rustpoc/$nom.crate
  python3.9 -c "import sys,tarfile; tarfile.open(sys.argv[1]).extractall(sys.argv[2])" /tmp/rustpoc/$nom.crate $R/crates-src
  echo "  $nom $ver"
done

echo "== liaisons pre-generees, WAMR factice, correctifs"
cp $DEPOT/liaisons/*.rs $R/patches/
cp $DEPOT/outils/wamr_factice.c $R/wamr-factice/
python3.9 $DEPOT/ibmi/correctifs.py $R/crates-src $R/patches
echo "Pret : sh $DEPOT/ibmi/build-deno.sh"

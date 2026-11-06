#!/QOpenSys/usr/bin/sh
# Repairs .rlib files whose embedded static library is wrong, without a cascade of
# recompilations (modification time preserved):
#  - libz_sys: rustc had embedded libz.so.1 (shared zlib from yum, found through
#    the -L) instead of the zlib-ng objects -> replaced with those objects;
#  - v8 (v8x): embedded stub WAMR object is outdated -> replaced.
# Usage: reparer-rlibs.sh [target/<profile> directory]
set -e
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
T=${1:-/QOpenSys/opt/denoibmi/deno/target/ibmi}
TMP=/tmp/reparer-rlibs.$$; mkdir -p $TMP
ZLIB=$(ls -t $T/build/libz-sys-*/out/lib/libz.a | head -1)
mkdir -p $TMP/zlib && (cd $TMP/zlib && ar -X64 x $ZLIB)
for r in $T/deps/liblibz_sys-*.rlib; do
  cp -p $r $TMP/ref
  ar -X64 t $r | grep -qx libz.so.1 && ar -X64 d $r libz.so.1
  (cd $TMP/zlib && ar -X64 r $r *.o)
  touch -r $TMP/ref $r
  echo "zlib-ng embarque : $r"
done
W=/QOpenSys/opt/denoibmi/wamr-factice/wamr_factice.o
for r in $T/deps/libv8-*.rlib; do
  ar -X64 t $r | grep -qx wamr_factice.o || continue
  cp -p $r $TMP/ref
  (cd $(dirname $W) && ar -X64 r $r wamr_factice.o)
  touch -r $TMP/ref $r
  echo "WAMR factice a jour : $r"
done
cd / && rm -rf $TMP

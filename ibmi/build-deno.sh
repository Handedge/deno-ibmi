exec > /tmp/rustpoc/deno2.log 2>&1
# Native build of Deno on IBM i (PASE). Variables: PROFILE (ibmi-o1 | ibmi-os),
# ENGINE (quickjs | v8), CRATES_SRC (sources of the crates to patch, see prepare-deno.sh)
PROFILE=${PROFILE:-ibmi-o1}
ENGINE=${ENGINE:-quickjs}
CRATES_SRC=${CRATES_SRC:-/QOpenSys/opt/denoibmi/crates-src}
/QOpenSys/usr/bin/system "CHGJOB RUNPTY(20)" > /dev/null 2>&1
. /QOpenSys/opt/rust/rustenv.sh
export CC=gcc-12 CXX=g++-12 CFLAGS="-maix64 -pthread -O2 -D__STDC_LIMIT_MACROS -D__STDC_CONSTANT_MACROS" CXXFLAGS="-maix64 -pthread -O2 -D__STDC_LIMIT_MACROS -D__STDC_CONSTANT_MACROS" AR=ar
# aws-lc: no assembly (the bundled one uses linux-ppc64le ELF syntax)
export LIBSQLITE3_SYS_BINDINGS_FILE=/QOpenSys/opt/denoibmi/patches/sqlite3_bindgen_aix.rs
export AWS_LC_SYS_BINDINGS_FILE=/QOpenSys/opt/denoibmi/patches/awslc046_bindings_aix.rs
export NGHTTP2_BINDINGS_FILE=/QOpenSys/opt/denoibmi/patches/nghttp2_bindings_aix.rs
export LIBUV_SYS_LITE_BINDINGS_FILE=/QOpenSys/opt/denoibmi/patches/libuv_bindings_aix.rs
# job limits: large links (ld) and compilations
ulimit -d unlimited; ulimit -s unlimited; ulimit -m unlimited; ulimit -f unlimited
ulimit -a | head -6
# Linker: PASE has no bind64; a copy of bind (32-bit) in the large memory model
# (ldedit maxdata 2 GB, without DSA, which breaks archive reading), called via ld -bbinder:; system untouched
O=/QOpenSys/opt/rust/outils/bin
mkdir -p $O
if [ ! -f $O/bind.2g ]; then
  rm -f $O/bind; cp /QOpenSys/QIBM/ProdData/OS400/PASE/bin/bind $O/bind && ldedit -bmaxdata:0x80000000 $O/bind && touch $O/bind.2g
fi
dump -X32 -ov $O/bind 2>&1 | grep -i maxdata | head -2
# V8: options placed in the ld wrapper rather than in RUSTFLAGS, so as not to invalidate
# all the compilation already done.
#  -s: no symbol table; with V8 (326 MB of text), the PASE linker crashes
#       while writing the table (0711-759 ERREUR INTERNE save.c line 965), proven
#       by replaying the link (-s alone is enough; not -bgc, -bnoipath, -bcdtors, -bpD, memory)
#  -bbigtoc: safety net in case the Rust part (small model) overflows the TOC; V8 is
#       compiled with -mcmodel=large
BIGTOC=; [ "$ENGINE" = v8 ] && BIGTOC="-s -bbigtoc"
printf '#!/QOpenSys/usr/bin/sh
exec /QOpenSys/usr/bin/ld -bbinder:/QOpenSys/opt/rust/outils/bin/bind %s "$@"
' "$BIGTOC" > $O/ld
chmod 755 $O/ld
export PATH=$O:$PATH
# one section per function (rustc default on AIX) = millions of csects: the 32-bit
# linker saturates; group them (unstable option, allowed by RUSTC_BOOTSTRAP)
export RUSTC_BOOTSTRAP=1
export RUSTFLAGS="$RUSTFLAGS -Z function-sections=no"
echo "RUSTFLAGS=$RUSTFLAGS"
cat $O/ld
export AWS_LC_SYS_NO_ASM=1 AWS_LC_SYS_CMAKE_BUILDER=0
yum install -y grep-gnu > /dev/null 2>&1; command -v grep
# WebAssembly: stub WAMR (WAMR is not ported to AIX)
W=/QOpenSys/opt/denoibmi/wamr-factice
(cd $W && gcc-12 -maix64 -O2 -c wamr_factice.c -o wamr_factice.o && rm -f libvmlib.a && ar -X64 -q libvmlib.a wamr_factice.o) && export WAMR_LIB_DIR=$W
# V8 engine: library built on LINUXBUILD (v8aix/), pre-generated Rust binding,
# Chromium libc++ already in the archive (no system C++ library to link)
if [ "$ENGINE" = v8 ]; then
  export RUSTY_V8_ARCHIVE=/QOpenSys/opt/denoibmi/v8aix/librusty_v8.a
  export RUSTY_V8_SRC_BINDING_PATH=/QOpenSys/opt/denoibmi/v8aix/src_binding_aix.rs
  export CXXSTDLIB=
  ls -l $RUSTY_V8_ARCHIVE $RUSTY_V8_SRC_BINDING_PATH || exit 1
fi
# Embedded ICU data (set_common_data_77 from deno_core): Cargo.toml.ibmi declares
# deno_core without default features; without include_icu_data, Intl throws
# "Internal error. Icu error." under V8 (QuickJS does not use ICU)
FEATURES=$ENGINE; [ "$ENGINE" = v8 ] && FEATURES="v8,deno_core/include_icu_data"
echo "ENGINE=$ENGINE PROFILE=$PROFILE"
cd /QOpenSys/opt/denoibmi/deno
# rustc embeds librusty_v8.a in the .rlib of the v8 crate, and cargo does not rebuild it
# when the archive changes under the same path: clean it if the archive is newer
if [ "$ENGINE" = v8 ]; then
  for r in target/$PROFILE/deps/libv8-*.rlib; do
    [ -f "$r" ] && [ "$RUSTY_V8_ARCHIVE" -nt "$r" ] && { echo "V8 archive newer than $r: cargo clean -p v8"; cargo clean -p v8 --profile $PROFILE; break; }
  done
fi
python3.9 $(cd "$(dirname "$0")" && pwd)/add-profiles.py $(cd "$(dirname "$0")/.." && pwd)/deno/Cargo.toml.ibmi Cargo.toml
mkdir -p /QOpenSys/opt/denoibmi/patches
python3.9 $(cd "$(dirname "$0")" && pwd)/patches.py $CRATES_SRC /QOpenSys/opt/denoibmi/patches
grep -q '^\[patch.crates-io\]' Cargo.toml || printf '
[patch.crates-io]
' >> Cargo.toml
grep -q '^byteorder = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a byteorder = { path = "/QOpenSys/opt/denoibmi/patches/byteorder-1.5.0" }' Cargo.toml
grep -q '^v8x = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a v8x = { path = "/QOpenSys/opt/denoibmi/patches/v8x-149.4.0-rc.4" }' Cargo.toml
grep -q '^aws-lc-sys-046 = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a aws-lc-sys-046 = { package = "aws-lc-sys", path = "/QOpenSys/opt/denoibmi/patches/aws-lc-sys-0.46.0" }' Cargo.toml
[ -d /QOpenSys/opt/denoibmi/patches/aws-lc-sys-0.40.0 ] && { grep -q '^aws-lc-sys-040 = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a aws-lc-sys-040 = { package = "aws-lc-sys", path = "/QOpenSys/opt/denoibmi/patches/aws-lc-sys-0.40.0" }' Cargo.toml; }
grep -q '^libz-sys-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a libz-sys-patch = { package = "libz-sys", path = "/QOpenSys/opt/denoibmi/patches/libz-sys-1.1.20" }' Cargo.toml
grep -q '^libsqlite3-sys-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a libsqlite3-sys-patch = { package = "libsqlite3-sys", path = "/QOpenSys/opt/denoibmi/patches/libsqlite3-sys-0.38.1" }' Cargo.toml
grep -q '^netif-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a netif-patch = { package = "netif", path = "/QOpenSys/opt/denoibmi/patches/netif-0.1.6" }' Cargo.toml
grep -q '^rustix-038 = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a rustix-038 = { package = "rustix", path = "/QOpenSys/opt/denoibmi/patches/rustix-0.38.34" }' Cargo.toml
grep -q '^libnghttp2-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a libnghttp2-patch = { package = "libnghttp2", path = "/QOpenSys/opt/denoibmi/patches/libnghttp2-1.68.0" }' Cargo.toml
grep -q '^quinn-udp-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a quinn-udp-patch = { package = "quinn-udp", path = "/QOpenSys/opt/denoibmi/patches/quinn-udp-0.5.9" }' Cargo.toml
grep -q '^libffi-sys-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a libffi-sys-patch = { package = "libffi-sys", path = "/QOpenSys/opt/denoibmi/patches/libffi-sys-4.1.0" }' Cargo.toml
grep -q '^libuv-sys-lite-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a libuv-sys-lite-patch = { package = "libuv-sys-lite", path = "/QOpenSys/opt/denoibmi/patches/libuv-sys-lite-1.48.4" }' Cargo.toml
grep -q '^dlopen2-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a dlopen2-patch = { package = "dlopen2", path = "/QOpenSys/opt/denoibmi/patches/dlopen2-0.6.1" }' Cargo.toml
grep -q '^memmap2-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a memmap2-patch = { package = "memmap2", path = "/QOpenSys/opt/denoibmi/patches/memmap2-0.9.5" }' Cargo.toml
grep -q '^rustyline-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a rustyline-patch = { package = "rustyline", path = "/QOpenSys/opt/denoibmi/patches/rustyline-17.0.0" }' Cargo.toml
grep -q '^libsui-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a libsui-patch = { package = "libsui", path = "/QOpenSys/opt/denoibmi/patches/libsui-0.16.4" }' Cargo.toml
[ -d /QOpenSys/opt/denoibmi/patches/v8-150.4.0 ] && { grep -q '^v8-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a v8-patch = { package = "v8", path = "/QOpenSys/opt/denoibmi/patches/v8-150.4.0" }' Cargo.toml; }
grep -q '^deno_core_icudata-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a deno_core_icudata-patch = { package = "deno_core_icudata", path = "/QOpenSys/opt/denoibmi/patches/deno_core_icudata-0.77.0" }' Cargo.toml
grep -q '^open-patch = ' Cargo.toml || sed -i '/^\[patch.crates-io\]/a open-patch = { package = "open", path = "/QOpenSys/opt/denoibmi/patches/open-5.1.2" }' Cargo.toml
for v in 0.29.0 0.30.1; do k=nix-$(echo $v | tr -d . | cut -c1-3); [ -d /QOpenSys/opt/denoibmi/patches/nix-$v ] && { grep -q "^$k = " Cargo.toml || sed -i "/^\[patch.crates-io\]/a $k = { package = \"nix\", path = \"/QOpenSys/opt/denoibmi/patches/nix-$v\" }" Cargo.toml; }; done
grep -A8 'patch.crates-io' Cargo.toml
date
# retry if the PASE loader could not start rustc (0509-037, occasional under load)
for attempt in $(seq 1 30); do
  cargo build -p deno --profile $PROFILE --no-default-features --features $FEATURES > /tmp/rustpoc/cargo.out 2>&1
  rc=$?
  grep -vE '^\s+(Downloaded|Compiling|Locking|Adding|Downloading)|generated [0-9]+ warning|jobserver from env|build environment is likely|^\s*\|?\s*$|^\s+= note: the build env|^warning' /tmp/rustpoc/cargo.out | grep -E -B2 -A25 '^error|0509-' | tail -120
  echo "attempt $attempt: rc=$rc"
  [ $rc -eq 0 ] && break
  grep -q '0509-037' /tmp/rustpoc/cargo.out || break
done
date
ls -l target/$PROFILE/deno
echo DONE

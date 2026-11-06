#!/bin/bash
# Generates on Linux (LINUXBUILD) the bindgen bindings for powerpc64-ibm-aix,
# which cannot be generated on IBM i (no libclang). Prerequisites: rustup (minimal profile),
# libclang-18, PASE headers (/QOpenSys/usr/include from the IBM i) in ~/aixinc/include.
# Usage: generer_liaisons.sh <crate> <version> [features]
#   e.g.: generer_liaisons.sh libsqlite3-sys 0.38.1 '"bundled", "session", "unlock_notify", "preupdate_hook"'
#         generer_liaisons.sh aws-lc-sys 0.46.0 '"bindgen", "prebuilt-nasm"'   (+ AWS_LC_SYS_NO_ASM=1)
#         generer_liaisons.sh libnghttp2 1.68.0
#         generer_liaisons.sh libuv-sys-lite 1.48.4
set -e
crate=$1; version=$2; features=${3:-}
export PATH=$HOME/.cargo/bin:$PATH
# stub compiler and ar: the C part for AIX cannot be compiled here
[ -x ~/fakecc.sh ] || { printf '#!/bin/sh\nwhile [ $# -gt 0 ]; do if [ "$1" = "-o" ]; then shift; : > "$1"; fi; shift; done\n' > ~/fakecc.sh; chmod +x ~/fakecc.sh; }
[ -x ~/fakear.sh ] || { printf '#!/bin/sh\nfor a in "$@"; do case "$a" in *.a) : > "$a";; esac; done\n' > ~/fakear.sh; chmod +x ~/fakear.sh; }
dir=~/gen-$crate; mkdir -p $dir/src; cd $dir
cat > Cargo.toml <<T
[package]
name = "gen"
version = "0.1.0"
edition = "2021"
[dependencies]
$crate = { version = "=$version", features = [$features] }
T
echo 'fn main() {}' > src/main.rs
export LIBCLANG_PATH=/usr/lib/x86_64-linux-gnu
export BINDGEN_EXTRA_CLANG_ARGS="-nostdinc -isystem $HOME/aixinc/include"
export CC_powerpc64_ibm_aix=$HOME/fakecc.sh AR_powerpc64_ibm_aix=$HOME/fakear.sh
cargo build --keep-going --target powerpc64-ibm-aix > build.log 2>&1 || true
ls -l target/powerpc64-ibm-aix/debug/build/$crate-*/out/*.rs

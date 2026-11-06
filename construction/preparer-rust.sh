#!/bin/bash
# Prepares the Rust toolchain for the Deno → IBM i cross-compilation, on LINUXBUILD (idempotent).
#
# - PINNED version (not "stable", which a rustup update would move): 1.99.1, the one that produced
#   the 2026-11-06 production build. Deno 2.9.8 asks for 1.95 in its rust-toolchain.toml, but that
#   std does not compile for powerpc64-ibm-aix (st_atime): `cargo +1.99.1` is used everywhere.
# - Patch to rust-src (compiler-builtins): the math intrinsics there use weak linkage
#   (linkage = "weak"); on AIX, the PASE linker then rejects a visible imported symbol
#   (0711-407 .rint…). AIX is excluded, as Windows-gnu and Cygwin already are.
#   7 occurrences in 1.99.1; the script checks the count to detect a different version.
set -euo pipefail
RUST=${RUST_VERSION:-1.99.1}
export PATH=$HOME/.cargo/bin:$PATH

rustup toolchain install "$RUST" --profile minimal --component rust-src >/dev/null
SYSROOT=$(rustc +"$RUST" --print sysroot)
M=$SYSROOT/lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/macros.rs

AVANT='target_os = "cygwin")), linkage = "weak")]'
APRES='target_os = "cygwin", target_os = "aix")), linkage = "weak")]'
deja=$(grep -cF "$APRES" "$M" || true)
reste=$(grep -cF "$AVANT" "$M" || true)
if [ "$reste" -gt 0 ]; then
  [ "$((deja + reste))" -eq 7 ] || { echo "macros.rs : $((deja + reste)) occurrences au lieu de 7, version de Rust à vérifier" >&2; exit 1; }
  sed -i "s/target_os = \"cygwin\")), linkage = \"weak\")\]/target_os = \"cygwin\", target_os = \"aix\")), linkage = \"weak\")]/" "$M"
  # a std already built for AIX would keep the old compiler_builtins: force its recompilation
  find /QOpenSys/opt/denoibmi/deno/target/powerpc64-ibm-aix -maxdepth 3 \
    \( -path "*/.fingerprint/compiler_builtins-*" -o -name "libcompiler_builtins-*" \) -exec rm -rf {} + 2>/dev/null || true
  echo "compiler-builtins retouché ($reste occurrence(s))"
fi
[ "$(grep -cF "$APRES" "$M")" -eq 7 ] || { echo "retouche incomplète" >&2; exit 1; }
rustc +"$RUST" --version

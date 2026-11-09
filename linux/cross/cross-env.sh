# Environment for cross-compiling Deno (Rust) to IBM i PASE, on LINUXBUILD.
# Source it from the repository: source linux/cross/cross-env.sh (build/build.sh does)
# The /QOpenSys/opt/denoibmi/... paths are the same as on IBMI (a real directory on LINUXBUILD
# since 2026-11-06): Cargo.toml and its [patch] entries stay identical.
# The cross-compilation tools (linker, cc-aix, cmake toolchain) are taken FROM THE REPOSITORY, next to
# this file (until 2026-11-06: out-of-repository copies in ~/denox, including an outdated cc-aix).
export CROSS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
IBMI_OBJECTS=$(cd "$CROSS_DIR/../../build/ibmi-objects" && pwd)
export PATH=$HOME/.cargo/bin:$HOME/v8aix/bin:$PATH
export RUSTC_BOOTSTRAP=1                       # -Z build-std (AIX is a tier 3 target)
AIX_TRIPLE=powerpc64-ibm-aix
SYSROOT=$HOME/v8aix/sysroot
CLANG=$HOME/v8aix/clang/bin
export CROSS_TARGET=$AIX_TRIPLE

# Rust for the target only (build scripts remain x86_64)
export CARGO_TARGET_POWERPC64_IBM_AIX_LINKER=$CROSS_DIR/rust-linker.sh
export CARGO_TARGET_POWERPC64_IBM_AIX_RUSTFLAGS="--cap-lints warn -Z function-sections=no -L /QOpenSys/opt/rust/runtime -l paseat -C link-arg=-blibpath:/QOpenSys/opt/rust/runtime:/QOpenSys/pkgs/lib:/usr/lib:/lib"

# C/C++ for the target: Chromium clang + PASE headers (same as V8)
C_FLAGS="--target=powerpc64-ibm-aix7.2 -fintegrated-as -mignore-xcoff-visibility --sysroot=$SYSROOT -mcpu=pwr8 -fno-xl-pragma-pack -D__PASE__ -D_ALL_SOURCE=1 -D_THREAD_SAFE -D__STDC_LIMIT_MACROS -D__STDC_CONSTANT_MACROS -O2"
export CC_powerpc64_ibm_aix="$CROSS_DIR/cc-aix"
export CXX_powerpc64_ibm_aix="$CLANG/clang++"
export AR_powerpc64_ibm_aix="$HOME/v8aix/bin/ar-aix"
export CFLAGS_powerpc64_ibm_aix="$C_FLAGS"
export CXXFLAGS_powerpc64_ibm_aix="$C_FLAGS"

# V8: AIX archive for the target, official prebuilt for the host (patch to the v8 build.rs)
export RUSTY_V8_ARCHIVE_AIX=/QOpenSys/opt/denoibmi/v8aix/librusty_v8.a
export RUSTY_V8_SRC_BINDING_PATH_AIX=/QOpenSys/opt/denoibmi/v8aix/src_binding_aix.rs

# CLI snapshot produced by V8 on IBM i (big-endian), injected through deno_snapshots
export DENO_SNAPSHOT_PREBUILT=/QOpenSys/opt/denoibmi/snapshot-v8
export DENO_SKIP_CROSS_BUILD_CHECK=1

# Pre-generated bindings and crate options (same as build-deno.sh)
P=/QOpenSys/opt/denoibmi/patches
export LIBSQLITE3_SYS_BINDINGS_FILE=$P/sqlite3_bindgen_aix.rs
export AWS_LC_SYS_BINDINGS_FILE=$P/awslc046_bindings_aix.rs
export NGHTTP2_BINDINGS_FILE=$P/nghttp2_bindings_aix.rs
export LIBUV_SYS_LITE_BINDINGS_FILE=$P/libuv_bindings_aix.rs
export AWS_LC_SYS_NO_ASM=1 AWS_LC_SYS_CMAKE_BUILDER=0
export WAMR_LIB_DIR=/QOpenSys/opt/denoibmi/wamr-factice

# cmake (libz-sys / zlib-ng…): AIX system, compiler checks without linking an executable
export CMAKE_TOOLCHAIN_FILE_powerpc64_ibm_aix=$CROSS_DIR/aix.cmake
# objects assembled on IBM i (build/ibmi-objects): libffi.a (autotools + AIX assembler),
# libz.a (zlib-ng compat); cc-aix also takes powerpc64_aix.o (psm) from there
export IBMI_OBJECTS
export LIBFFI_PREBUILT_DIR=$IBMI_OBJECTS
export LIBZ_PREBUILT_DIR=$IBMI_OBJECTS

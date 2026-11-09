#!/bin/bash
# Prepares, from a FRESH clone of Deno, the cross-compilation tree targeting IBM i on
# LINUXBUILD: /QOpenSys/opt/denoibmi/{deno,crates-src,patches,patches-croise,v8aix,wamr-factice}.
# Idempotent. Usage: bash build/prepare-tree.sh   (from a clone of the deno-ibmi repository)
#
# /QOpenSys/opt/denoibmi is a REAL directory on LINUXBUILD (no longer a symlink): paths frozen at
# compile time (JS sources read by the snapshot generator) are then identical on IBM i.
set -euo pipefail
DENO_VERSION=${DENO_VERSION:-v2.9.8}
RUST=${RUST_VERSION:-1.99.1}
R=/QOpenSys/opt/denoibmi
REPO=$(cd "$(dirname "$0")/.." && pwd)
V8=$HOME/v8aix
export PATH=$HOME/.cargo/bin:$PATH

echo "== 1. Rust $RUST, pinned and patched"
bash "$REPO/build/prepare-rust.sh"

echo "== 2. Deno $DENO_VERSION (fresh clone)"
if [ ! -d "$R/deno/.git" ]; then
  git clone -q --depth 1 --branch "$DENO_VERSION" https://github.com/denoland/deno.git "$R/deno"
  git -C "$R/deno" config denoibmi.version "$DENO_VERSION"
fi
# a tree of another version is never overwritten automatically (25 GB, possibly in use)
TREE_VERSION=$(git -C "$R/deno" config denoibmi.version || echo v2.9.8)   # trees older than 2026-11-06: 2.9.8
[ "$TREE_VERSION" = "$DENO_VERSION" ] || { echo "ERROR: the $R/deno tree is $TREE_VERSION, not $DENO_VERSION: move or delete it first"; exit 1; }
git -C "$R/deno" log -1 --format='%h %cs %s'

echo "== 3. ingredients: bindings, V8 for AIX, big-endian ICU, stub WAMR"
mkdir -p "$R/patches" "$R/v8aix" "$R/wamr-factice" "$R/crates-src"
cp "$REPO"/bindings/*.rs "$R/patches/"
cp "$V8/rusty_v8/out/aix/obj/librusty_v8.a" "$V8/src_binding_aix.rs" "$R/v8aix/"   # phase 2: rebuilt by script
cp "$V8/rusty_v8/third_party/icu/common/icudtb.dat" "$R/v8aix/"
"$V8/clang/bin/clang" --target=powerpc64-ibm-aix7.2 -O2 -c "$REPO/tools/wamr_factice.c" -o "$R/wamr-factice/wamr_factice.o"
rm -f "$R/wamr-factice/libvmlib.a"
"$V8/bin/ar-aix" rcs "$R/wamr-factice/libvmlib.a" "$R/wamr-factice/wamr_factice.o"

echo "== 4. crates to patch, downloaded from crates.io"
for c in byteorder:1.5.0 aws-lc-sys:0.40.0 aws-lc-sys:0.46.0 nix:0.29.0 nix:0.30.1 libz-sys:1.1.20 \
         libsqlite3-sys:0.38.1 netif:0.1.6 rustix:0.38.34 quinn-udp:0.5.9 libffi-sys:4.1.0 \
         libnghttp2:1.68.0 libuv-sys-lite:1.48.4 dlopen2:0.6.1 memmap2:0.9.5 libsui:0.16.4 \
         rustyline:17.0.0 open:5.1.2 mio:1.2.4 inventory:0.3.21 signal-hook:0.3.18 notify:8.2.0 \
         deno_core_icudata:0.77.0 v8:150.4.0 v8x:149.4.0-rc.4; do
  name=${c%%:*}; ver=${c#*:}
  [ -d "$R/crates-src/$name-$ver" ] && continue
  curl -sSfL "https://crates.io/api/v1/crates/$name/$ver/download" | tar xz -C "$R/crates-src"
  echo "   $name $ver"
done

echo "== 5. Cargo.toml, Cargo.lock, snapshot generator"
cd "$R/deno"
git checkout -q -- Cargo.toml Cargo.lock cli/snapshot     # start again from the original files (re-runnable)
rm -rf cli/snapshot/generateur
python3 "$REPO/build/configure-cargo.py" "$R/deno" "$REPO/deno/Cargo.toml.ibmi"
if [ "$DENO_VERSION" = v2.9.8 ]; then
  cp "$REPO/build/Cargo.lock.cross" Cargo.lock     # production lock, proven
else
  # Other version: its own upstream lock, plus our deliberate upgrades (AIX fixes released
  # upstream since 2.9.8). Never a downgrade: a crate already newer upstream is kept.
  # list = all upgrades of the production lock relative to the original 2.9.8 lock
  for c in signal-hook-mio:0.2.5 tokio:1.54.1 mio:1.2.4 socket2:0.5.10 socket2:0.6.5 tokio-macros:2.7.2 \
           signal-hook-registry:1.4.8 signal-hook:0.3.18 psm:0.1.32 stacker:0.1.25 rustix:1.1.6 \
           getrandom:0.2.17 getrandom:0.3.4 errno:0.3.14 jobserver:0.1.35; do
    name=${c%%:*}; min=${c#*:}
    for v in $(awk -v n="$name" '$0=="name = \""n"\""{getline; gsub(/"/,"",$3); print $3}' Cargo.lock); do
      major() { case $1 in 0.*) echo "${1%.*}" ;; *) echo "${1%%.*}" ;; esac; }   # 0.1.x: major 0.1
      [ "$(major "$v")" = "$(major "$min")" ] || continue           # other major version: not affected
      [ "$(printf '%s\n%s\n' "$v" "$min" | sort -V | head -1)" = "$min" ] && continue   # already ≥
      cargo +"$RUST" update -q -p "$name@$v" --precise "$min" && echo "   $name $v → $min" \
        || echo "   WARNING: $name $v → $min refused by cargo"
    done
  done
  echo "   watched crates, production 2.9.8 lock → $DENO_VERSION lock:"
  python3 "$REPO/build/compare-crates.py" "$REPO/build/Cargo.lock.cross" Cargo.lock
  echo "   (a patched crate that changes version: update the list of step 4 and patches.py)"
fi
git show HEAD:cli/snapshot/build.rs > /tmp/snapshot-build.rs.origine
python3 "$REPO/build/snapshot-generator/install.py" "$R/deno" /tmp/snapshot-build.rs.origine

echo "== 6. AIX/PASE patches (Deno + crates), then cross-compilation specifics"
python3 "$REPO/ibmi/patches.py" "$R/crates-src" "$R/patches" | grep -v "^missing" || true
python3 "$REPO/linux/cross/prepare-cross.py" "$R" "$R/crates-src"
python3 "$REPO/deno-tests/prepare-test-server.py" "$R/deno" || true   # test_server only
echo "Tree ready: $R"

#!/bin/bash
# Prepares, from a FRESH clone of Deno, the cross-compilation tree targeting IBM i on
# LINUXBUILD: /QOpenSys/opt/denoibmi/{deno,crates-src,patches,patches-croise,v8aix,wamr-factice}.
# Idempotent. Usage: bash construction/preparer-arbre.sh   (from a clone of the deno-ibmi repository)
#
# /QOpenSys/opt/denoibmi is a REAL directory on LINUXBUILD (no longer a symlink): paths frozen at
# compile time (JS sources read by the snapshot generator) are then identical on IBM i.
set -euo pipefail
VERSION_DENO=${VERSION_DENO:-v2.9.8}
RUST=${RUST_VERSION:-1.99.1}
R=/QOpenSys/opt/denoibmi
DEPOT=$(cd "$(dirname "$0")/.." && pwd)
V8=$HOME/v8aix
export PATH=$HOME/.cargo/bin:$PATH

echo "== 1. Rust $RUST figé et retouché"
bash "$DEPOT/construction/preparer-rust.sh"

echo "== 2. Deno $VERSION_DENO (clone neuf)"
if [ ! -d "$R/deno/.git" ]; then
  git clone -q --depth 1 --branch "$VERSION_DENO" https://github.com/denoland/deno.git "$R/deno"
  git -C "$R/deno" config denoibmi.version "$VERSION_DENO"
fi
# a tree of another version is never overwritten automatically (25 GB, possibly in use)
ARBRE=$(git -C "$R/deno" config denoibmi.version || echo v2.9.8)   # trees older than 2026-11-06: 2.9.8
[ "$ARBRE" = "$VERSION_DENO" ] || { echo "L'arbre $R/deno est en $ARBRE, pas en $VERSION_DENO : le déplacer ou le supprimer d'abord"; exit 1; }
git -C "$R/deno" log -1 --format='%h %cs %s'

echo "== 3. ingrédients : liaisons, V8 pour AIX, ICU big-endian, WAMR factice"
mkdir -p "$R/patches" "$R/v8aix" "$R/wamr-factice" "$R/crates-src"
cp "$DEPOT"/liaisons/*.rs "$R/patches/"
cp "$V8/rusty_v8/out/aix/obj/librusty_v8.a" "$V8/src_binding_aix.rs" "$R/v8aix/"   # phase 2: rebuilt by script
cp "$V8/rusty_v8/third_party/icu/common/icudtb.dat" "$R/v8aix/"
"$V8/clang/bin/clang" --target=powerpc64-ibm-aix7.2 -O2 -c "$DEPOT/outils/wamr_factice.c" -o "$R/wamr-factice/wamr_factice.o"
rm -f "$R/wamr-factice/libvmlib.a"
"$V8/bin/ar-aix" rcs "$R/wamr-factice/libvmlib.a" "$R/wamr-factice/wamr_factice.o"

echo "== 4. crates à corriger, téléchargées depuis crates.io"
for c in byteorder:1.5.0 aws-lc-sys:0.40.0 aws-lc-sys:0.46.0 nix:0.29.0 nix:0.30.1 libz-sys:1.1.20 \
         libsqlite3-sys:0.38.1 netif:0.1.6 rustix:0.38.34 quinn-udp:0.5.9 libffi-sys:4.1.0 \
         libnghttp2:1.68.0 libuv-sys-lite:1.48.4 dlopen2:0.6.1 memmap2:0.9.5 libsui:0.16.4 \
         rustyline:17.0.0 open:5.1.2 mio:1.2.4 inventory:0.3.21 signal-hook:0.3.18 notify:8.2.0 \
         deno_core_icudata:0.77.0 v8:150.4.0 v8x:149.4.0-rc.4; do
  nom=${c%%:*}; ver=${c#*:}
  [ -d "$R/crates-src/$nom-$ver" ] && continue
  curl -sSfL "https://crates.io/api/v1/crates/$nom/$ver/download" | tar xz -C "$R/crates-src"
  echo "   $nom $ver"
done

echo "== 5. Cargo.toml, Cargo.lock, générateur de snapshot"
cd "$R/deno"
git checkout -q -- Cargo.toml Cargo.lock cli/snapshot     # start again from the original files (re-runnable)
rm -rf cli/snapshot/generateur
python3 "$DEPOT/construction/configurer-cargo.py" "$R/deno" "$DEPOT/deno/Cargo.toml.ibmi"
if [ "$VERSION_DENO" = v2.9.8 ]; then
  cp "$DEPOT/construction/Cargo.lock.croise" Cargo.lock     # production lock, proven
else
  # Other version: its own upstream lock, plus our deliberate upgrades (AIX fixes released
  # upstream since 2.9.8). Never a downgrade: a crate already newer upstream is kept.
  # list = all upgrades of the production lock relative to the original 2.9.8 lock
  for c in signal-hook-mio:0.2.5 tokio:1.54.1 mio:1.2.4 socket2:0.5.10 socket2:0.6.5 tokio-macros:2.7.2 \
           signal-hook-registry:1.4.8 signal-hook:0.3.18 psm:0.1.32 stacker:0.1.25 rustix:1.1.6 \
           getrandom:0.2.17 getrandom:0.3.4 errno:0.3.14 jobserver:0.1.35; do
    nom=${c%%:*}; min=${c#*:}
    for v in $(awk -v n="$nom" '$0=="name = \""n"\""{getline; gsub(/"/,"",$3); print $3}' Cargo.lock); do
      maj() { case $1 in 0.*) echo "${1%.*}" ;; *) echo "${1%%.*}" ;; esac; }   # 0.1.x: major 0.1
      [ "$(maj "$v")" = "$(maj "$min")" ] || continue           # other major version: not affected
      [ "$(printf '%s\n%s\n' "$v" "$min" | sort -V | head -1)" = "$min" ] && continue   # already ≥
      cargo +"$RUST" update -q -p "$nom@$v" --precise "$min" && echo "   $nom $v → $min" \
        || echo "   AVERTISSEMENT : $nom $v → $min refusé par cargo"
    done
  done
  echo "   crates surveillées, lock 2.9.8 de production → lock de $VERSION_DENO :"
  python3 "$DEPOT/construction/comparer-crates.py" "$DEPOT/construction/Cargo.lock.croise" Cargo.lock
  echo "   (une crate corrigée qui change de version : adapter la liste de l'étape 4 et correctifs.py)"
fi
git show HEAD:cli/snapshot/build.rs > /tmp/snapshot-build.rs.origine
python3 "$DEPOT/construction/generer-snapshot/installer.py" "$R/deno" /tmp/snapshot-build.rs.origine

echo "== 6. correctifs AIX/PASE (Deno + crates), puis spécificités de la compilation croisée"
python3 "$DEPOT/ibmi/correctifs.py" "$R/crates-src" "$R/patches" | grep -v "^absent" || true
python3 "$DEPOT/linux/croise/preparer-croise.py" "$R" "$R/crates-src"
python3 "$DEPOT/tests-deno/preparer-test-server.py" "$R/deno" || true   # test_server only
echo "Arbre prêt : $R"

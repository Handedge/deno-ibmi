#!/bin/bash
# Checks, WITHOUT CHANGING ANYTHING, that everything build/build.sh needs is in place on
# LINUXBUILD and on IBMI. Run it before a build, especially when running a build for the first
# time. For each missing item: the command or the build/README.md section that resolves it.
#   bash build/check-prerequisites.sh
# Exit code: number of failed checks (0 = ready).
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
R=/QOpenSys/opt/denoibmi
RUST=${RUST_VERSION:-1.99.1}
V8=$HOME/v8aix
KEY=$HOME/.ssh/id_denobuild
IBMI=${IBMI_SSH:-DENOBUILD@192.0.2.82}   # IBM i profile@host (IBMI_SSH variable)
SSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=10 $IBMI"
export PATH=$HOME/.cargo/bin:$PATH
failures=0
ok()  { printf '  OK  %s\n' "$1"; }
fail() { printf '  KO  %s\n        → %s\n' "$1" "$2"; failures=$((failures + 1)); }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else fail "$1" "$3"; fi; }

echo "== LINUXBUILD: tools"
for tool in git curl python3 tar gzip ssh scp sort; do check "$tool" "command -v $tool" "install $tool (apt)"; done
check "rustup" "command -v rustup" "install rustup (https://rustup.rs) for the current user"
check "Rust $RUST with rust-src" "rustup +$RUST component list --installed | grep -q rust-src" \
      "bash build/prepare-rust.sh (build.sh also runs it)"
M=$(rustc +"$RUST" --print sysroot 2>/dev/null)/lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/macros.rs
n=$(grep -cF 'target_os = "cygwin", target_os = "aix")), linkage = "weak")]' "$M" 2>/dev/null || echo 0)
[ "$n" = 7 ] && ok "rust-src patched for AIX (compiler-builtins, 7/7)" \
             || fail "rust-src patched for AIX ($n/7)" "bash build/prepare-rust.sh (build.sh also runs it)"

echo "== LINUXBUILD: V8 for AIX and C toolchain (~/v8aix, see v8aix/README.md)"
check "librusty_v8.a for AIX"      "test -s $V8/rusty_v8/out/aix/obj/librusty_v8.a" "rebuild V8: v8aix/README.md (phase 2, manual)"
check "src_binding_aix.rs"          "test -s $V8/src_binding_aix.rs" "v8aix/linux/generate-src-binding.sh"
check "icudtb.dat (ICU big-endian)" "test -s $V8/rusty_v8/third_party/icu/common/icudtb.dat" "v8aix/linux/fetch.sh"
check "Chromium clang"            "test -x $V8/clang/bin/clang" "v8aix/linux/fetch.sh"
check "ar-aix"                      "test -x $V8/bin/ar-aix" "copy v8aix/linux/ar-aix to ~/v8aix/bin"
check "PASE sysroot"                "test -f $V8/sysroot/usr/include/stdio.h || test -f $V8/sysroot/include/stdio.h" \
      "v8aix/linux/prepare-sysroot.sh (headers copied from IBMI)"

echo "== LINUXBUILD: repository and disk space"
check "objects assembled on IBM i"  "test -s $REPO/build/ibmi-objects/libffi.a -a -s $REPO/build/ibmi-objects/libz.a -a -s $REPO/build/ibmi-objects/powerpc64_aix.o" \
      "build/ibmi-objects/README.md"
check "executable scripts"          "test -x $REPO/linux/cross/cc-aix -a -x $REPO/linux/cross/rust-linker.sh -a -x $REPO/linux/cross/pack-link.sh" \
      "chmod +x linux/cross/cc-aix linux/cross/*.sh (copied without file modes)"
check "x64 test reference"          "test -s $REPO/deno-tests/results-x64.jsonl" "deno-tests/README.md (reference run on LINUXBUILD)"
if [ -L "$R" ]; then fail "$R is a real directory" "it is a symlink: replace it with a real directory (sudo mkdir, chown to the user), see build/README.md"
elif [ -d "$R" ] && [ -w "$R" ]; then ok "$R: real directory, writable"
else fail "$R writable" "sudo mkdir -p $R && sudo chown \$(id -un): $R"; fi
free_gb=$(df -BG --output=avail "$(test -d $R && echo $R || echo $HOME)" | tail -1 | tr -dc 0-9)
[ "${free_gb:-0}" -ge 20 ] && ok "disk: $free_gb GB free (≥ 20)" || fail "disk: ${free_gb:-?} GB free" "free some space (a built tree ≈ 7 GB, plus the cargo registry)"

echo "== Access to IBMI (DENOBUILD profile, dedicated key)"
check "key $KEY" "test -s $KEY" "build/README.md, § 7 (DENOBUILD profile)"
if $SSH true 2>/dev/null; then
  ok "passwordless ssh DENOBUILD@IBMI"
  r=$($SSH 'echo "shell=$0"
    for d in /QOpenSys/opt/denoibmi/croise /QOpenSys/opt/denoibmi/livraisons /QOpenSys/opt/deno-ibmi /tmp/rustpoc; do
      [ -d $d ] && [ -w $d ] && echo "writable:$d=1" || echo "writable:$d=0"; done
    for f in /QOpenSys/opt/rust/runtime/libpaseat.a /QOpenSys/opt/rust/outils/bin/bind /QOpenSys/opt/rust/rustenv.sh \
             /QOpenSys/opt/denoibmi/denotests/unit.py /QOpenSys/opt/denoibmi/denotests/target/aix/test_server \
             /QOpenSys/pkgs/bin/db2util /QOpenSys/pkgs/bin/python3.9 /QOpenSys/pkgs/bin/sha256sum; do
      [ -e $f ] && echo "file:$f=1" || echo "file:$f=0"; done
    /QOpenSys/pkgs/bin/db2util -o space "select system_asp_used from qsys2.system_status_info" | tr -d "\"" | awk "\$1 ~ /^[0-9.]+\$/ {print \"asp=\" int(\$1)}"
    /QOpenSys/pkgs/bin/db2util -o space "select count(*) from qsys2.user_info_basic where authorization_name = '"'"'DENOTEST'"'"'" | tr -d "\"" | awk "\$1 ~ /^[0-9]+\$/ {print \"denotest=\" \$1}"' 2>/dev/null)
  case "$r" in *shell=*bsh*) fail "ssh shell of DENOBUILD" "CALL QSYS2.SET_PASE_SHELL_INFO('DENOBUILD', '/QOpenSys/usr/bin/sh')" ;;
               *) ok "ssh shell of DENOBUILD (sh)" ;; esac
  for l in $(echo "$r" | grep -E '^(writable|file):'); do
    name=${l#*:}; name=${name%=*}
    case $l in *=1) ok "${l%%:*} $name" ;;
      writable:*) fail "DENOBUILD can write to $name" "mkdir + chown DENOBUILD (IBM i administrator), see build/README.md" ;;
      *) fail "present on IBMI: $name" "build/README.md, § 7 (IBM i setup)" ;; esac
  done
  asp=$(echo "$r" | sed -n 's/^asp=//p')
  [ -n "$asp" ] && [ "$asp" -lt 75 ] && ok "IBMI ASP at $asp % (< 75)" || fail "IBMI ASP at ${asp:-?} %" "free some space on IBMI (build.sh refuses above 75 %)"
  [ "$(echo "$r" | sed -n 's/^denotest=//p')" = 1 ] && ok "DENOTEST profile (full tests)" \
    || fail "DENOTEST profile" "create DENOTEST (*USER, PASSWORD(*NONE)) and grant *USE on it to DENOBUILD"
else
  fail "passwordless ssh DENOBUILD@IBMI" "build/README.md, § 7 (DENOBUILD profile)"
fi

echo
[ $failures = 0 ] && echo "READY: bash build/build.sh" || echo "$failures item(s) to fix before building"
exit $failures

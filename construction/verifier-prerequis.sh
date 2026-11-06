#!/bin/bash
# Checks, WITHOUT CHANGING ANYTHING, that everything construction/construire.sh needs is in place on
# LINUXBUILD and on IBMI. Run it before a build, especially when running a build for the first
# time. For each missing item: the command or the construction/README.md section that resolves it.
#   bash construction/verifier-prerequis.sh
# Exit code: number of failed checks (0 = ready).
set -u
DEPOT=$(cd "$(dirname "$0")/.." && pwd)
R=/QOpenSys/opt/denoibmi
RUST=${RUST_VERSION:-1.99.1}
V8=$HOME/v8aix
CLE=$HOME/.ssh/id_denobuild
IBMI=${IBMI_SSH:-DENOBUILD@192.0.2.82}   # IBM i profile@host (IBMI_SSH variable)
SSH="ssh -i $CLE -o BatchMode=yes -o ConnectTimeout=10 $IBMI"
export PATH=$HOME/.cargo/bin:$PATH
ko=0
ok()  { printf '  OK  %s\n' "$1"; }
non() { printf '  KO  %s\n        → %s\n' "$1" "$2"; ko=$((ko + 1)); }
verif() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else non "$1" "$3"; fi; }

echo "== LINUXBUILD : outils"
for o in git curl python3 tar gzip ssh scp sort; do verif "$o" "command -v $o" "installer $o (apt)"; done
verif "rustup" "command -v rustup" "installer rustup (https://rustup.rs) pour l'utilisateur courant"
verif "Rust $RUST avec rust-src" "rustup +$RUST component list --installed | grep -q rust-src" \
      "bash construction/preparer-rust.sh (le fait aussi construire.sh)"
M=$(rustc +"$RUST" --print sysroot 2>/dev/null)/lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/macros.rs
n=$(grep -cF 'target_os = "cygwin", target_os = "aix")), linkage = "weak")]' "$M" 2>/dev/null || echo 0)
[ "$n" = 7 ] && ok "rust-src retouché pour AIX (compiler-builtins, 7/7)" \
             || non "rust-src retouché pour AIX ($n/7)" "bash construction/preparer-rust.sh (le fait aussi construire.sh)"

echo "== LINUXBUILD : V8 pour AIX et chaîne C (~/v8aix, voir v8aix/README.md)"
verif "librusty_v8.a pour AIX"      "test -s $V8/rusty_v8/out/aix/obj/librusty_v8.a" "reconstruire V8 : v8aix/README.md (phase 2, manuel)"
verif "src_binding_aix.rs"          "test -s $V8/src_binding_aix.rs" "v8aix/linux/generer-src-binding.sh"
verif "icudtb.dat (ICU big-endian)" "test -s $V8/rusty_v8/third_party/icu/common/icudtb.dat" "v8aix/linux/recuperer.sh"
verif "clang de Chromium"           "test -x $V8/clang/bin/clang" "v8aix/linux/recuperer.sh"
verif "ar-aix"                      "test -x $V8/bin/ar-aix" "copier v8aix/linux/ar-aix dans ~/v8aix/bin"
verif "racine système PASE"         "test -f $V8/sysroot/usr/include/stdio.h || test -f $V8/sysroot/include/stdio.h" \
      "v8aix/linux/preparer-sysroot.sh (en-têtes copiés de IBMI)"

echo "== LINUXBUILD : dépôt et place"
verif "objets assemblés sur IBM i"  "test -s $DEPOT/construction/objets-ibmi/libffi.a -a -s $DEPOT/construction/objets-ibmi/libz.a -a -s $DEPOT/construction/objets-ibmi/powerpc64_aix.o" \
      "construction/objets-ibmi/README.md"
verif "scripts exécutables"         "test -x $DEPOT/linux/croise/cc-aix -a -x $DEPOT/linux/croise/lien-rust.sh -a -x $DEPOT/linux/croise/emballer-lien.sh" \
      "chmod +x linux/croise/cc-aix linux/croise/*.sh (copie sans les modes)"
verif "référence x64 des tests"     "test -s $DEPOT/tests-deno/resultats-x64.jsonl" "tests-deno/README.md (référence lancée sur LINUXBUILD)"
if [ -L "$R" ]; then non "$R est un vrai dossier" "c'est un lien : le remplacer par un vrai dossier (sudo mkdir, chown à l'utilisateur), voir construction/README.md"
elif [ -d "$R" ] && [ -w "$R" ]; then ok "$R : vrai dossier, accessible en écriture"
else non "$R accessible en écriture" "sudo mkdir -p $R && sudo chown \$(id -un): $R"; fi
libre=$(df -BG --output=avail "$(test -d $R && echo $R || echo $HOME)" | tail -1 | tr -dc 0-9)
[ "${libre:-0}" -ge 20 ] && ok "disque : $libre Go libres (≥ 20)" || non "disque : ${libre:-?} Go libres" "libérer de la place (un arbre construit ≈ 7 Go, plus le registre cargo)"

echo "== Accès à IBMI (profil DENOBUILD, clé dédiée)"
verif "clé $CLE" "test -s $CLE" "construction/README.md, § 7 (profil DENOBUILD)"
if $SSH true 2>/dev/null; then
  ok "ssh DENOBUILD@IBMI sans mot de passe"
  r=$($SSH 'echo "shell=$0"
    for d in /QOpenSys/opt/denoibmi/croise /QOpenSys/opt/denoibmi/livraisons /QOpenSys/opt/deno-ibmi /tmp/rustpoc; do
      [ -d $d ] && [ -w $d ] && echo "ecrit:$d=1" || echo "ecrit:$d=0"; done
    for f in /QOpenSys/opt/rust/runtime/libpaseat.a /QOpenSys/opt/rust/outils/bin/bind /QOpenSys/opt/rust/rustenv.sh \
             /QOpenSys/opt/denoibmi/denotests/unit.py /QOpenSys/opt/denoibmi/denotests/target/aix/test_server \
             /QOpenSys/pkgs/bin/db2util /QOpenSys/pkgs/bin/python3.9 /QOpenSys/pkgs/bin/sha256sum; do
      [ -e $f ] && echo "fichier:$f=1" || echo "fichier:$f=0"; done
    /QOpenSys/pkgs/bin/db2util -o space "select system_asp_used from qsys2.system_status_info" | tr -d "\"" | awk "\$1 ~ /^[0-9.]+\$/ {print \"asp=\" int(\$1)}"
    /QOpenSys/pkgs/bin/db2util -o space "select count(*) from qsys2.user_info_basic where authorization_name = '"'"'DENOTEST'"'"'" | tr -d "\"" | awk "\$1 ~ /^[0-9]+\$/ {print \"denotest=\" \$1}"' 2>/dev/null)
  case "$r" in *shell=*bsh*) non "shell ssh de DENOBUILD" "CALL QSYS2.SET_PASE_SHELL_INFO('DENOBUILD', '/QOpenSys/usr/bin/sh')" ;;
               *) ok "shell ssh de DENOBUILD (sh)" ;; esac
  for l in $(echo "$r" | grep -E '^(ecrit|fichier):'); do
    nom=${l#*:}; nom=${nom%=*}
    case $l in *=1) ok "${l%%:*} $nom" ;;
      ecrit:*) non "DENOBUILD peut écrire dans $nom" "mkdir + chown DENOBUILD (administrateur IBM i), voir construction/README.md" ;;
      *) non "présent sur IBMI : $nom" "construction/README.md, § 7 (mise en place sur IBM i)" ;; esac
  done
  asp=$(echo "$r" | sed -n 's/^asp=//p')
  [ -n "$asp" ] && [ "$asp" -lt 75 ] && ok "ASP de IBMI à $asp % (< 75)" || non "ASP de IBMI à ${asp:-?} %" "faire de la place sur IBMI (construire.sh refuse au-delà de 75 %)"
  [ "$(echo "$r" | sed -n 's/^denotest=//p')" = 1 ] && ok "profil DENOTEST (tests complets)" \
    || non "profil DENOTEST" "créer DENOTEST (*USER, PASSWORD(*NONE)) et donner *USE à DENOBUILD sur ce profil"
else
  non "ssh DENOBUILD@IBMI sans mot de passe" "construction/README.md, § 7 (profil DENOBUILD)"
fi

echo
[ $ko = 0 ] && echo "PRÊT : bash construction/construire.sh" || echo "$ko point(s) à régler avant de construire"
exit $ko

#!/bin/bash
# Stub linker for the Rust -> powerpc64-ibm-aix cross-compilation (LINUXBUILD).
# rustc calls it instead of the AIX ld: it records the command (one argument
# per line) and copies the rustc temporary files (symbols.o, list.exp, deleted
# after linking); the real link is replayed on IBM i by replay-link.sh.
# The output produced here is only a placeholder script (cargo requires a file).
set -e
dest=""
prev=""
for a in "$@"; do
  [ "$prev" = "-o" ] && dest="$a"
  prev="$a"
done
[ -n "$dest" ] || { echo "rust-linker: no -o" >&2; exit 1; }
saved_dir="$dest.lien.d"
rm -rf "$saved_dir"; mkdir -p "$saved_dir"
: > "$dest.lien"
for a in "$@"; do
  f="$a"; pref=""
  case "$a" in -bE:*) f="${a#-bE:}"; pref="-bE:";; esac
  case "$f" in
    # rustc temporaries (symbols.o, list.exp) and objects of the linked crate (*.rcgu.o):
    # rustc deletes them after linking
    /tmp/rustc*|*/rustc[A-Za-z0-9]*/*|*.rcgu.o)
      if [ -f "$f" ]; then cp "$f" "$saved_dir/"; a="$pref@GARDE@/$(basename "$f")"; fi;;
  esac
  printf '%s\n' "$a" >> "$dest.lien"
done
printf '#!/bin/sh\necho "link to replay on IBM i: %s.lien" >&2\nexit 1\n' "$dest" > "$dest"
chmod 755 "$dest"

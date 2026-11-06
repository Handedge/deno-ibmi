#!/bin/bash
# Fake linker for AIX executables (cross-compilation on LINUXBUILD): records the
# command (<output>.lien) and a copy of the response file (<output>.entrees; ninja
# deletes the .rsp), so the link can be replayed on IBM i with the PASE ld.
# In place of the executable, writes a script that "replays" the files the tool
# produced on IBM i (rejouer-ibmi.sh), so ninja can carry on.
dest=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && dest="$a"; prev="$a"; done
mkdir -p "$(dirname "$dest")"
printf "%q " "$@" > "$dest.lien"; echo >> "$dest.lien"
for a in "$@"; do case "$a" in @*) cp "${a#@}" "$dest.entrees";; esac; done
printf '#!/bin/sh\n# %s : exécutable AIX, lié et exécuté sur IBM i\nexec "$HOME/v8aix/bin/rejouer-ibmi.sh" "$@"\n' "$dest" > "$dest"
chmod +x "$dest"

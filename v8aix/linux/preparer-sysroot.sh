#!/bin/bash
# AIX sysroot for cross-compilation: PASE headers (~/aixinc/include) exposed through
# symlinks, except those that must be patched for clang:
#  - ctype.h: lacking an extern "C" block, its declarations get C++ linkage when
#    compiled as C++ (gcc adds it via fixincludes, clang does not) -> calls to _Z7toupperi...
set -e
SRC=~/aixinc/include
DST=~/v8aix/sysroot/usr/include
[ -L "$DST" ] && rm "$DST"
mkdir -p "$DST"
for e in "$SRC"/*; do
  n=$(basename "$e")
  [ "$n" = ctype.h ] && continue
  ln -sfn "$e" "$DST/$n"
done
python3 - "$SRC/ctype.h" "$DST/ctype.h" <<'PY'
import sys
t = open(sys.argv[1], encoding="latin-1").read()
debut = "#define __H_CTYPE\n"
fin = "#endif /* __H_CTYPE */"
assert t.count(debut) == 1 and t.rstrip().endswith(fin)
t = t.replace(debut, debut + '#ifdef __cplusplus\nextern "C" {  /* deno-ibmi */\n#endif\n', 1)
i = t.rstrip().rfind(fin)
t = t[:i] + '#ifdef __cplusplus\n}  /* extern "C", deno-ibmi */\n#endif\n' + t[i:]
open(sys.argv[2], "w", encoding="latin-1").write(t)
PY
echo "racine système prête : $(ls "$DST" | wc -l) entrées, ctype.h corrigé"

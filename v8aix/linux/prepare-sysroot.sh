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
start = "#define __H_CTYPE\n"
end = "#endif /* __H_CTYPE */"
assert t.count(start) == 1 and t.rstrip().endswith(end)
t = t.replace(start, start + '#ifdef __cplusplus\nextern "C" {  /* deno-ibmi */\n#endif\n', 1)
i = t.rstrip().rfind(end)
t = t[:i] + '#ifdef __cplusplus\n}  /* extern "C", deno-ibmi */\n#endif\n' + t[i:]
open(sys.argv[2], "w", encoding="latin-1").write(t)
PY
echo "sysroot ready: $(ls "$DST" | wc -l) entries, ctype.h patched"

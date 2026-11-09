#!/QOpenSys/usr/bin/sh
# Assembles on IBM i (gcc-12 + PASE as) the embedded.S produced by mksnapshot
# (V8 builtins, AIX assembler syntax: .csect, .xline...):
# the LLVM integrated assembler does not understand these directives.
exec > /tmp/rustpoc/assemble-embedded.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
ulimit -d unlimited; ulimit -s unlimited
cd /QOpenSys/opt/denoibmi/v8aix/aix
date
time gcc-12 -maix64 -c gen/v8/embedded.S -o embedded.o
echo "rc=$?"; date
ls -l embedded.o
nm -X64 -g embedded.o 2>/dev/null | head -5
echo "symbols: $(nm -X64 -g embedded.o 2>/dev/null | wc -l)"
echo DONE

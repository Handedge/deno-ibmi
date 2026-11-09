#!/QOpenSys/usr/bin/sh
# Builds /QOpenSys/opt/rust/runtime/libpaseat.a (to be linked before libc: RUSTFLAGS -l paseat)
set -e
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
cd "$(dirname "$0")"
# -pthread (_THREAD_SAFE): errno = *_Errno(), thread-local. Without it, the library
# wrote the process-wide GLOBAL errno: an emulated *at() failing on a secondary
# thread left errno = 0 in the calling thread (async recursive Deno.remove:
# "os error 0"). Check: dump -X64 -Tv shr_64.o must import _Errno, not errno.
gcc-12 -maix64 -pthread -D_THREAD_SAFE -O2 -Wall -fPIC -shared -static-libgcc -o shr_64.o paseat.c -Wl,-bE:paseat.exp -lpthread
if dump -X64 -Tv shr_64.o | grep -q " errno$"; then echo "ERROR: global errno imported"; exit 1; fi
rm -f libpaseat.a.new
ar -X64 -q libpaseat.a.new shr_64.o
# atomic replacement: running processes keep the previously loaded version
cp -p /QOpenSys/opt/rust/runtime/libpaseat.a /QOpenSys/opt/rust/runtime/libpaseat.a.avant-thread-safe 2>/dev/null || true
cp libpaseat.a.new /QOpenSys/opt/rust/runtime/libpaseat.a.tmp && mv -f /QOpenSys/opt/rust/runtime/libpaseat.a.tmp /QOpenSys/opt/rust/runtime/libpaseat.a
echo "libpaseat.a built"

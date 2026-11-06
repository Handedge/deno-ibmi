# Rust environment on IBM i (IBM Rust SDK for AIX under PASE) - to be sourced: . /QOpenSys/opt/rust/rustenv.sh
export PATH=/QOpenSys/opt/rust/current/bin:/QOpenSys/pkgs/bin:/QOpenSys/usr/bin:/usr/bin
export CARGO_HOME=/QOpenSys/opt/rust/cargo
export SSL_CERT_FILE=/QOpenSys/opt/rust/ca-bundle.pem
export QIBM_MULTI_THREADED=Y
export OBJECT_MODE=64
# Linking: Open XL runtime (libunwind, libc++) and yum libraries
export RUSTFLAGS="-L /QOpenSys/opt/rust/runtime -l paseat -C link-arg=-blibpath:/QOpenSys/opt/rust/runtime:/QOpenSys/pkgs/lib:/usr/lib:/lib"
# cargo calls the IBM binaries directly (bypassing the ksh script, fragile under load)
export RUSTC=/QOpenSys/opt/rust/current/bin/.rustc.orig
export RUSTDOC=/QOpenSys/opt/rust/current/bin/.rustdoc.orig
# runtime-outils: libz/libatomic from yum in archive(member) format, for rustc and
# cargo only (outside -L: the static link of zlib-ng must not find them)
export LIBPATH=/QOpenSys/opt/rust/runtime:/QOpenSys/opt/rust/runtime-outils:/QOpenSys/pkgs/lib:/QOpenSys/opt/rust/current/lib
export MALLOCMULTIHEAP=1
export AIXTHREAD_STK=4194304
export CARGO_BUILD_JOBS=2


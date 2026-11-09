# Cross-compiling Deno (Rust) for IBM i, on LINUXBUILD

Deno's Rust code is compiled on LINUXBUILD (28 cores) for `powerpc64-ibm-aix`; only the link step
is done on IBM i, with the PASE `ld`. Validated on 2026-11-02: binary identical in
behavior to the native one (fib(30) 51 ms, Intl, serve, HTTPS fetch).

| Step | Duration | Where |
|---|---|---|
| Full compilation (446 crates, `build-std`) | 5 to 6 min | LINUXBUILD |
| Link package (≈ 530 MB gzip) via the PC | ≈ 3 min | LINUXBUILD → PC → IBMI |
| Link | ≈ 1 min 30 s | IBMI |

Compared with 12 min to several hours natively on IBMI (2 processors).

## Building

**Since 2026-11-06, everything is chained by `build/build.sh`: see
[`build/README.md`](../../build/README.md).** The tools in this directory
(`cross-env.sh`, `cc-aix`, `rust-linker.sh`, `aix.cmake`, `pack-link.sh`, `prepare-cross.py`) are
used directly from the repository; the old copies in `~/denox` are no longer used.

By hand (debugging):
```
source linux/cross/cross-env.sh            # from the repository
cd /QOpenSys/opt/denoibmi/deno
cargo +1.99.1 build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix \
  --profile ibmi-rel -p deno --no-default-features --features v8,deno_core/include_icu_data -j 28
```
(`source` is run from the repository.) The link is replayed on IBM i (`ibmi/link-sbmjob.sh`, as an
SBMJOB: launched over ssh, it would die when the session closes) → `/QOpenSys/opt/denoibmi/croise/deno`.

## Pitfalls resolved

| Symptom | Cause | Workaround |
|---|---|---|
| `std` does not compile (`st_atime`) | Rust 1.95 from `rust-toolchain.toml` | `cargo +stable` (1.99) |
| snapshot impossible (x86 little-endian V8) | `deno_snapshots` runs V8 at build time | IBM i snapshot copied in (`DENO_SNAPSHOT_PREBUILT`), without build-dependencies |
| host V8 | `RUSTY_V8_ARCHIVE` applies to both host and target | `v8`'s build.rs: AIX archive if the target is AIX, official one otherwise |
| cmake: "System is unknown", link test | cmake-rs forces `CMAKE_SYSTEM_NAME=aix` | IBM i `libz.a` (`LIBZ_PREBUILT_DIR`) |
| AIX `.s` files passed to GNU as | clang does not assemble XCOFF | `cc-aix`: empty object if nothing remains after preprocessing, otherwise the IBM i object |
| libffi (autotools + `aix.S`) | — | IBM i `libffi.a` (`LIBFFI_PREBUILT_DIR`) |
| `nix`: `#![deny(unused)]` | stricter lint in 1.99, host side | `warn` |
| `0711-407 .rint` visibility on an import | `compiler_builtins`: math functions with weak linkage | no `weak` on AIX (rust-src); `-mignore-xcoff-visibility` for C |
| `*.rcgu.o` not found when replaying | rustc deletes them after linking | `rust-linker.sh` keeps them |
| `-Wl,--export-dynamic-symbol-list` | `deno_napi` seen from the Linux host | removed when replaying |
| "Debug" binary: assertions and overflow checks enabled | the `ibmi*` profiles inherit from `dev` | **`ibmi-rel`** profile (inherits from `release`, no LTO, `opt-level = "s"`, `panic = "unwind"`): 294 MB, startup −15%, HTTP −15 to −22% (2026-11-03) |
| `0711-759 save.c 965` at `-O1` (384 MB text) | limit of the PASE `ld` (natively: 338 MB passes) | `ibmi-os` profile (`opt-level = "s"`) → 347 MB |

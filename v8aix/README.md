# V8 for IBM i (PASE): cross-compilation from LINUXBUILD

Goal: replace QuickJS with V8 in Deno on IBM i. Deno 2.9.8 locks the
`v8` crate 150.4.0 (rusty_v8), i.e. **V8 15.0.245.2**. V8 keeps its AIX support
(platform code, AIX assembly writer for the builtins); Node.js
on IBM i proves it (V8 13.6, gcc, big-endian, without pointer compression).

## Principle

- **Cross**-compilation on LINUXBUILD (Linux x86_64, 28 cores) with Chromium's clang
  (LLVM 23) and `--target=powerpc64-ibm-aix7.2`: 64-bit XCOFF objects.
- System headers: those of PASE (`~/aixinc/include`, seen as the sysroot
  `~/v8aix/sysroot/usr/include`); Chromium's libc++ compiled together with V8.
- AIX archives (big archive format) through `llvm-ar --format=bigarchive` (`linux/ar-aix`).
- V8 generators (torque, bytecode list, regexp special cases): built
  for the Linux host targeting ppc64 (`clang_x64_v8_ppc64` toolchain).
- Executables for AIX (`mksnapshot`, `d8`): **linked and run on IBM i**;
  `linux/lien-aix.sh` records the link command (`<sortie>.lien`, where `<sortie>` is the output).
- Endianness: `V8_OS_AIX` => `V8_TARGET_BIG_ENDIAN` (v8config.h).

Feasibility trials (2026-10-30): C++ (virtual functions, `thread_local`, containers)
compiled on LINUXBUILD, linked with IBM's libc++ and run under PASE; AIX assembly
produced by LLVM accepted by the PASE `as`; `gn gen` for AIX.

## Reproducing

```sh
~/v8aix/recuperer.sh                    # rusty_v8 v150.4.0 + submodules
python3 tools/clang/scripts/update.py --output-dir ~/v8aix/clang
python3 tools/ninja_gn_binaries.py --dir ~/v8aix/outils
python3 tools/rust_toolchain.py         # only so that the configuration can be read
python3 ~/v8aix/correctifs_v8.py ~/v8aix/rusty_v8
cp args.gn ~/v8aix/rusty_v8/out/aix/ && gn gen out/aix && ~/v8aix/compiler.sh
```

(`recuperer.sh` fetches rusty_v8 v150.4.0 and its submodules; `rust_toolchain.py` is only needed so that
the configuration can be read.)

## Provisional choices (to be restored)

| Setting | Why | Next |
|---|---|---|
| `v8_enable_temporal_support = false`, `enable_rust = false` | Temporal is written in Rust, and Chromium's rustc has no std for AIX | compile temporal_capi with our AIX Rust toolchain |
| `icu_use_data_file = true` | embedding the ICU data goes through the system assembler | provide **big-endian** ICU data (icupkg) to Deno |
| no pointer compression and no sandbox | like Node's V8 on IBM i | to be reassessed |

## Source patches (`correctifs_v8.py`)

- **`#pragma pack` (XL semantics)**: on AIX, clang applies `-fxl-pragma-pack` by default (rules of IBM's
  XL compiler). A `pack(push)`/`pack(4)` nested in a class is not popped as with gcc:
  35 alignment `static_assert`s failed. Fix: **`-fno-xl-pragma-pack`**, the option chosen by Node.js
  for its migration from AIX to clang (PR nodejs/node#62656, Node 26+). The former macro workaround in
  `object-macros.h` is redundant (to be removed at the next full build).

- `push_registers_asm.cc` (cppgc): the AIX inline assembly (`.csect`, `.globl x, hidden`)
  is not read by LLVM; C++ version using `__builtin_unwind_init()`.
- `immediate-crash.h`: `.vbyte` unknown to LLVM, replaced by the instruction `tw 12,2,2`.
- `gcc_toolchain.gni`: the AIX rules (`ar -X64`...) tested the target OS for
  all toolchains; they now test each toolchain's own OS.
- `snapshot_toolchain.gni`, `BUILD.gn` (torque), `-mcpu=pwr9`: separation between
  generators (host) and mksnapshot (AIX).

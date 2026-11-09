# Objects built on IBM i (AIX assembler or autotools), used by the cross-compilation

| File | Crate | Origin |
|---|---|---|
| `libffi.a` | libffi-sys 4.1.0 | native Deno build on IBMI (2026-11-02, autotools + `aix.S`) |
| `libz.a` | libz-sys 1.1.20 (zlib-ng compat) | same (zlib-ng's cmake) |
| `powerpc64_aix.o` | psm (stack) | same (`powerpc64_aix.s` assembled by gcc-12) |

Taken from `target/ibmi-o1/build/*/out` of the native build (tree deleted on 2026-11-04); used through
`LIBFFI_PREBUILT_DIR`, `LIBZ_PREBUILT_DIR` and `cc-aix`. To be redone by a script on IBM i if one of these
crates changes version (phase 2/3 of the build work).

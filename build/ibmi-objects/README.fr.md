# Objets fabriqués sur IBM i (assembleur AIX ou autotools), utilisés par la compilation croisée

| Fichier | Crate | Origine |
|---|---|---|
| `libffi.a` | libffi-sys 4.1.0 | construction native de Deno sur IBMI (02/11/2026, autotools + `aix.S`) |
| `libz.a` | libz-sys 1.1.20 (zlib-ng compat) | idem (cmake de zlib-ng) |
| `powerpc64_aix.o` | psm (pile) | idem (`powerpc64_aix.s` assemblé par gcc-12) |

Repris de `target/ibmi-o1/build/*/out` de la construction native (arbre supprimé le 04/11) ; utilisés via
`LIBFFI_PREBUILT_DIR`, `LIBZ_PREBUILT_DIR` et `cc-aix`. À refaire par script sur IBM i si l'une de ces
crates change de version (phase 2/3 du chantier de construction).

# V8 pour IBM i (PASE) : compilation croisée depuis LINUXBUILD

Objectif : remplacer QuickJS par V8 dans Deno sur IBM i. Deno 2.9.8 verrouille la
crate `v8` 150.4.0 (rusty_v8), soit **V8 15.0.245.2**. V8 garde le support d'AIX
(code de plateforme, écrivain d'assembleur AIX pour les fonctions intégrées) ; Node.js
sur IBM i le prouve (V8 13.6, gcc, big-endian, sans compression de pointeurs).

## Principe

- Compilation **croisée** sur LINUXBUILD (Linux x86_64, 28 cœurs) par le clang de
  Chromium (LLVM 23) avec `--target=powerpc64-ibm-aix7.2` : objets XCOFF 64 bits.
- En-têtes système : ceux de PASE (`~/aixinc/include`, vus comme sysroot
  `~/v8aix/sysroot/usr/include`) ; libc++ de Chromium compilée avec V8.
- Archives AIX (big archive) par `llvm-ar --format=bigarchive` (`linux/ar-aix`).
- Générateurs de V8 (torque, liste des bytecodes, cas spéciaux regexp) : construits
  pour l'hôte Linux en visant ppc64 (chaîne `clang_x64_v8_ppc64`).
- Exécutables pour AIX (`mksnapshot`, `d8`) : **liés et exécutés sur IBM i** ;
  `linux/lien-aix.sh` enregistre la commande de lien (`<sortie>.lien`).
- Endianness : `V8_OS_AIX` => `V8_TARGET_BIG_ENDIAN` (v8config.h).

Essais de faisabilité (30/10/2026) : C++ (virtuelles, `thread_local`, conteneurs)
compilé sur LINUXBUILD, lié avec le libc++ d'IBM et exécuté sous PASE ; assembleur AIX
produit par LLVM accepté par l'`as` de PASE ; `gn gen` pour AIX.

## Reproduire

```sh
~/v8aix/recuperer.sh                    # rusty_v8 v150.4.0 + sous-modules
python3 tools/clang/scripts/update.py --output-dir ~/v8aix/clang
python3 tools/ninja_gn_binaries.py --dir ~/v8aix/outils
python3 tools/rust_toolchain.py         # seulement pour que la configuration se lise
python3 ~/v8aix/correctifs_v8.py ~/v8aix/rusty_v8
cp args.gn ~/v8aix/rusty_v8/out/aix/ && gn gen out/aix && ~/v8aix/compiler.sh
```

## Choix provisoires (à rétablir)

| Réglage | Pourquoi | Suite |
|---|---|---|
| `v8_enable_temporal_support = false`, `enable_rust = false` | Temporal est en Rust, le rustc de Chromium n'a pas de std pour AIX | compiler temporal_capi avec notre chaîne Rust AIX |
| `icu_use_data_file = true` | l'intégration des données ICU passe par l'assembleur système | fournir des données ICU **big-endian** (icupkg) à Deno |
| pas de compression de pointeurs ni de sandbox | comme le V8 de Node sur IBM i | à réévaluer |

## Correctifs de sources (`correctifs_v8.py`)

- **`#pragma pack` (sémantique XL)** : sur AIX, clang applique par défaut `-fxl-pragma-pack` (règles du
  compilateur XL d'IBM). Un `pack(push)`/`pack(4)` emboîté dans une classe ne se dépile pas comme avec gcc :
  35 `static_assert` d'alignement échouaient. Correction : **`-fno-xl-pragma-pack`**, l'option retenue par Node.js
  pour sa migration d'AIX vers clang (PR nodejs/node#62656, Node 26+). L'ancien contournement de macro dans
  `object-macros.h` est redondant (à retirer à la prochaine compilation complète).

- `push_registers_asm.cc` (cppgc) : l'assembleur en ligne AIX (`.csect`, `.globl x, hidden`)
  n'est pas lu par LLVM ; version C++ par `__builtin_unwind_init()`.
- `immediate-crash.h` : `.vbyte` inconnu d'LLVM, remplacé par l'instruction `tw 12,2,2`.
- `gcc_toolchain.gni` : les règles AIX (`ar -X64`...) testaient l'OS de la cible pour
  toutes les chaînes ; elles testent désormais l'OS de chaque chaîne.
- `snapshot_toolchain.gni`, `BUILD.gn` (torque), `-mcpu=pwr9` : séparation entre
  générateurs (hôte) et mksnapshot (AIX).

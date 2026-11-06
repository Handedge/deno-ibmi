# Compilation croisée de Deno (Rust) vers IBM i, sur LINUXBUILD

Le Rust de Deno se compile sur LINUXBUILD (28 cœurs) pour `powerpc64-ibm-aix` ; seul le lien
se fait sur IBM i, avec le `ld` de PASE. Validé le 02/11/2026 : binaire identique en
comportement au natif (fib(30) 51 ms, Intl, serve, fetch HTTPS).

| Étape | Durée | Où |
|---|---|---|
| Compilation complète (446 crates, `build-std`) | 5 à 6 min | LINUXBUILD |
| Paquet du lien (≈ 530 Mo gzip) via le PC | ≈ 3 min | LINUXBUILD → PC → IBMI |
| Lien | ≈ 1 min 30 | IBMI |

Contre 12 min à plusieurs heures en natif sur IBMI (2 processeurs).

## Construire

**Depuis le 06/11/2026, tout est enchaîné par `construction/construire.sh` : voir
`construction/README.md`.** Les outils de ce dossier (`env-croise.sh`, `cc-aix`, `lien-rust.sh`,
`aix.cmake`, `emballer-lien.sh`, `preparer-croise.py`) sont utilisés directement depuis le dépôt ; les
anciennes copies de `~/denox` ne servent plus.

À la main (mise au point) :
```
source linux/croise/env-croise.sh            # depuis le dépôt
cd /QOpenSys/opt/denoibmi/deno
cargo +1.99.1 build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix \
  --profile ibmi-rel -p deno --no-default-features --features v8,deno_core/include_icu_data -j 28
```
Le lien se rejoue sur IBM i (`ibmi/lier-sbmjob.sh`, en SBMJOB : lancé par ssh, il meurt à la fermeture
de la session) → `/QOpenSys/opt/denoibmi/croise/deno`.

## Pièges levés

| Symptôme | Cause | Parade |
|---|---|---|
| `std` ne compile pas (`st_atime`) | Rust 1.95 de `rust-toolchain.toml` | `cargo +stable` (1.99) |
| snapshot impossible (V8 x86 little-endian) | `deno_snapshots` exécute V8 à la construction | snapshot d'IBM i recopié (`DENO_SNAPSHOT_PREBUILT`), sans build-dependencies |
| V8 de l'hôte | `RUSTY_V8_ARCHIVE` vaut pour hôte et cible | build.rs de `v8` : archive AIX si la cible est AIX, officielle sinon |
| cmake : « System is unknown », test de lien | cmake-rs impose `CMAKE_SYSTEM_NAME=aix` | `libz.a` d'IBM i (`LIBZ_PREBUILT_DIR`) |
| `.s` AIX passés à l'as GNU | clang n'assemble pas l'XCOFF | `cc-aix` : objet vide si rien après préprocesseur, sinon objet d'IBM i |
| libffi (autotools + `aix.S`) | — | `libffi.a` d'IBM i (`LIBFFI_PREBUILT_DIR`) |
| `nix` : `#![deny(unused)]` | lint plus strict de 1.99, côté hôte | `warn` |
| `0711-407 .rint` visibilité sur un import | `compiler_builtins` : math en liaison faible | pas de `weak` sur AIX (rust-src) ; `-mignore-xcoff-visibility` pour le C |
| `*.rcgu.o` introuvables au rejeu | rustc les efface après le lien | `lien-rust.sh` les garde |
| `-Wl,--export-dynamic-symbol-list` | `deno_napi` vu de l'hôte Linux | retiré au rejeu |
| Binaire « debug » : assertions et contrôles de débordement actifs | les profils `ibmi*` héritent de `dev` | profil **`ibmi-rel`** (hérite de `release`, sans LTO, `opt-level = "s"`, `panic = "unwind"`) : 294 Mo, démarrage −15 %, HTTP −15 à −22 % (03/11) |
| `0711-759 save.c 965` en `-O1` (texte 384 Mo) | limite du `ld` de PASE (natif : 338 Mo passe) | profil `ibmi-os` (`opt-level = "s"`) → 347 Mo |

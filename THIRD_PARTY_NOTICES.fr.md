# Mentions des composants tiers

La licence MIT du fichier `LICENSE` couvre les scripts, les correctifs et le code écrits pour ce projet.
Le dépôt contient aussi des fichiers dérivés de projets tiers, ou construits à partir d'eux. Ils restent
sous leur propre licence :

| Chemin | Origine | Licence |
|---|---|---|
| `build/ibmi-objects/libffi.a` | [libffi](https://github.com/libffi/libffi), construite sur IBM i (crate `libffi-sys` 4.1.0) | MIT |
| `build/ibmi-objects/libz.a` | [zlib-ng](https://github.com/zlib-ng/zlib-ng) en mode compatible zlib, construite sur IBM i (crate `libz-sys` 1.1.20) | zlib |
| `build/ibmi-objects/powerpc64_aix.o` | `src/arch/powerpc64_aix.s` de la crate [psm](https://github.com/rust-lang/stacker), assemblé sur IBM i | MIT OU Apache-2.0 |
| `bindings/sqlite3_bindgen_aix.rs` | liaisons générées par bindgen depuis les en-têtes de [SQLite](https://sqlite.org) | Domaine public |
| `bindings/awslc046_bindings_aix.rs` | liaisons générées depuis les en-têtes d'[AWS-LC](https://github.com/aws/aws-lc) (crate `aws-lc-sys`) | ISC ET (Apache-2.0 OU ISC) |
| `bindings/nghttp2_bindings_aix.rs` | liaisons générées depuis les en-têtes de [nghttp2](https://github.com/nghttp2/nghttp2) | MIT |
| `bindings/libuv_bindings_aix.rs` | liaisons générées depuis les en-têtes de [libuv](https://github.com/libuv/libuv) | MIT |
| `v8aix/src_binding_aix.rs` | liaisons générées depuis les en-têtes de [V8](https://v8.dev) / [rusty_v8](https://github.com/denoland/rusty_v8) | BSD-3-Clause / MIT |
| correctifs de `ibmi/patches.py`, `v8aix/patches_v8.py`, `linux/cross/prepare-cross.py` | modifications de [Deno](https://github.com/denoland/deno) (MIT), de rusty_v8 (MIT), de V8 (BSD-3-Clause) et de crates de crates.io (chacune sous sa licence, surtout MIT et/ou Apache-2.0) | licence du projet modifié |

Aucun binaire IBM n'est distribué dans ce dépôt. L'IBM Open SDK for Rust on AIX et le runtime IBM Open
XL C/C++ utilisés sur IBM i s'obtiennent auprès d'IBM, aux conditions d'IBM.

« Deno » est une marque de Deno Land Inc. Ce projet n'est ni affilié, ni parrainé, ni approuvé par
Deno Land Inc. ou IBM. IBM i, AIX et Power sont des marques d'International Business Machines
Corporation.

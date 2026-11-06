# Deno snapshot generator for IBM i (2026-11-06)

The CLI snapshot (`CLI_SNAPSHOT.bin` + residual sources) freezes Deno's JavaScript: it changes
**with every Deno version**. It must be produced by the IBM i V8 (big-endian), not by LINUXBUILD's.
Until 2026-11-05, only the native tree on IBMI could do it (several hours, 30 GB, deleted on
2026-11-04). The generator below redoes it in **4 seconds** on IBMI.

## Principle

`installer.py` **derives** a standalone program from Deno's original `cli/snapshot/build.rs` (same
code, output directory as an argument) and adds it to the workspace (`cli/snapshot/generateur`, crate
`generer-snapshot`). It is cross-compiled like Deno, linked on IBM i and run on IBM i, and its outputs
become the `DENO_SNAPSHOT_PREBUILT` of the Deno build.

## Procedure

**Automated since 2026-11-06 (steps 1, 3 and 4 of `construction/construire.sh`).** Details, for
debugging (paths from before phase 1: the tree is now `/QOpenSys/opt/denoibmi`):

1. LINUXBUILD: `python3 installer.py ~/denox/arbre/deno <build.rs d'origine de cli/snapshot>`
   (`<build.rs d'origine de cli/snapshot>` = the original `build.rs` of `cli/snapshot`; the `build.rs`
   of the cross tree is replaced by `preparer-croise.py`: take the one from a clean git clone).
2. LINUXBUILD: `cargo +stable build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix
   --profile ibmi-rel -p generer-snapshot -j 28` (2 min 20 s).
3. Package `deps/generer_snapshot-*.lien` (`emballer-lien.sh`), drop it into
   `/QOpenSys/opt/denoibmi/croise/lien.tar.gz`, link in an SBMJOB with
   `PROFIL=ibmi-rel BINAIRE=generer_snapshot` (`rejouer-lien.sh`) → `croise/generer_snapshot` (198 MB).
4. IBMI: **synchronize the JS/TS sources** of the cross tree into `/QOpenSys/opt/denoibmi/deno`
   (`ext`, `runtime`, `cli`, `libs`: `*.js *.ts *.mjs *.cjs *.json`, 717 files, 20 MB). Snapshot
   creation rereads these sources from disk: they must be the ones that will be compiled.
5. IBMI: `ulimit -d 8388608; XPG_SUS_ENV=ON croise/generer_snapshot <dossier>` (4 s;
   `<dossier>` = output directory).
6. Bring `<dossier>` back into `~/denox/arbre/snapshot-genere` and compile Deno with
   `DENO_SNAPSHOT_PREBUILT=/QOpenSys/opt/denoibmi/snapshot-genere`.

## Pitfall: hard-coded paths

Sources are referenced by absolute paths frozen at compile time
(`concat!(env!("CARGO_MANIFEST_DIR"), …)`), and Linux always returns the **physical** path of the
current directory: cargo sees `/home/build/denox/arbre/deno/…` even when launched from the
symlink `/QOpenSys/opt/denoibmi`. On IBMI, the symlink `/home/build/denox/arbre → /QOpenSys/opt/denoibmi`
made these paths exist (created on 2026-11-06). **Solved by phase 1**: `/QOpenSys/opt/denoibmi` is a
real directory on LINUXBUILD, the frozen paths are identical on both sides, and the symlink has been removed.

## Validation (2026-11-06)

- `EXTENSION_RESIDUAL_SOURCES.rs` identical byte for byte to the 2026-11-02 reference; the 335 residual
  sources identical one by one.
- `CLI_SNAPSHOT.bin`: 2.1 MB versus 3.1 MB (reference produced by a debug profile, with
  assertions): a binary comparison is meaningless, the proof is functional.
- Deno recompiled with this snapshot: full unit test run (run 10, under DENOTEST)
  **identical to run 9**: 99.87% of the applicable cases, 0 Deno-specific gap.

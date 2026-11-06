# Rebuilding Deno for IBM i

This guide lets someone who never took part in the project **rebuild Deno for IBM i, test it and put it
into service**, without relying on word-of-mouth knowledge. Everything starts from the `deno-ibmi`
repository.

Result: a `deno-ibmi-<version>-<date>` package on IBMI (`deno` binary for IBM i PASE, `libpaseat.a`,
INFO sheet, SHA-256 checksums), **tested** (≥ 99.5% of Deno's applicable official unit tests,
0 Deno-specific gap), ready to install.

## In short

```bash
# on LINUXBUILD (build account), in the deno-ibmi repository
bash construction/verifier-prerequis.sh        # changes nothing; must end with "PRÊT" (ready)
bash construction/construire.sh                # ≈ 18 min from a fresh clone; Deno 2.9.8 by default
```
```sh
# on IBMI, by an IBM i ADMINISTRATOR (human decision), ssh session or QP2TERM
sh /QOpenSys/opt/deno-ibmi/ibmi/livrer.sh --verifier deno-ibmi-2.9.8-YYYYMMDD-HHMM   # check only
sh /QOpenSys/opt/deno-ibmi/ibmi/livrer.sh deno-ibmi-2.9.8-YYYYMMDD-HHMM              # put into service
sh /QOpenSys/opt/deno-ibmi/ibmi/livrer.sh --retour                                   # roll back
```

Script messages are still in French (`PRÊT` = ready, `SEUIL NON ATTEINT` = threshold not met).

The build is **automatic**; **putting it into service is not**: that remains an administrator's
decision.

## Who does what

| Machine / profile | Role |
|---|---|
| **LINUXBUILD** (Ubuntu, 28 cores, build account) | cross-compiles everything (`powerpc64-ibm-aix`): Rust, V8, Deno; drives the build |
| **IBMI** (IBM i 7.5, `192.0.2.82`) | linking (the AIX linker does not exist on Linux), snapshot production by the IBM i V8, tests, delivery |
| **DENOBUILD** profile (IBMI) | used by LINUXBUILD over ssh; no special authorities, no password; key `~/.ssh/id_denobuild` accepted **only from LINUXBUILD's address** |
| **DENOTEST** profile (IBMI) | runs the unit tests (ordinary user, like the x64 reference) |
| **DENOAPP** profile (IBMI) | runs the production services (subsystem `DENOIBMI/DENOWS`) |
| IBM i administrator (e.g. QSECOFR) | installs a package (`livrer.sh`) |

Why IBM i is involved during the build: linking XCOFF binaries requires the AIX `ld` of PASE, and
Deno's startup snapshot must be produced by a **big-endian** V8, hence on IBM i.

## 1. Before you start

`bash construction/verifier-prerequis.sh` checks everything and, for each missing item, says what to
do. It asks for no password and modifies nothing. What it checks:

- **LINUXBUILD**: rustup, Rust 1.99.1 with `rust-src` **patched for AIX** (`preparer-rust.sh` does it,
  `construire.sh` reruns it every time); V8 compiled for AIX in `~/v8aix` (see § 6);
  `/QOpenSys/opt/denoibmi` is a **real directory** (not a symlink) and writable; ≥ 20 GB free;
  x64 test reference; objects assembled on IBM i (`construction/objets-ibmi`).
- **IBMI**: passwordless ssh access as DENOBUILD, `sh` shell, writable directories, Rust runtime and
  `libpaseat.a`, test suite and `test_server`, ASP < 75%, DENOTEST profile.

The repository on LINUXBUILD must keep the scripts' **executable modes** (a `git clone` does; so does a
copy through `git archive` or `tar`; a copy via the Windows workstation does not: in that case run
`chmod +x construction/*.sh linux/croise/*.sh linux/croise/cc-aix`).

## 2. Build

```bash
bash construction/construire.sh                     # full tests (default)
bash construction/construire.sh --tests rapide      # no unit tests: no package is produced
VERSION_DENO=v2.10.0 bash construction/construire.sh   # another Deno version (see § 4)
```

(Respectively: full tests, the default; `--tests rapide` skips the unit tests, so no package is
produced; `VERSION_DENO` selects another Deno version, see § 4.)

Log: `~/construction-deno/construire-AAAAMMJJ-HHMM.log` (everything that is displayed). Running it
detached is recommended (the ssh session can drop without consequence):
`setsid nohup bash construction/construire.sh > ~/construction-deno/lancement.log 2>&1 < /dev/null &`

| Step | What happens | Duration (fresh clone) |
|---|---|---|
| 0. safeguards | IBMI reachable, ASP < 75% (otherwise stop) | 2 s |
| 1. tree | Rust pinned; Deno cloned into `/QOpenSys/opt/denoibmi/deno`; crates to be patched downloaded; IBM i Cargo.toml and Cargo.lock; **all AIX/PASE patches** (`ibmi/correctifs.py`) | 1 min |
| 2. upload to IBMI | repository scripts (`/QOpenSys/opt/deno-ibmi`) and Deno's JS sources | 5 s |
| 3. snapshot generator | compiled on LINUXBUILD, **linked on IBMI** (SBMJOB `LIEN`) | 4 min |
| 4. snapshot | produced on IBMI by the IBM i V8, brought back | 10 s |
| 5. Deno | compiled on LINUXBUILD with this snapshot, **linked on IBMI** | 8 min |
| 6. quick test | `--version`, `eval`, `fr-FR` formatting, `node:crypto` | 2 s |
| 7. full tests | official unit tests under DENOTEST (SBMJOB `TESTSDENO`), compared with the x64 reference; **blocking threshold** ≥ 99.5% of applicable cases and 0 Deno-specific gap | 6 min |
| 8. package | `/QOpenSys/opt/denoibmi/livraisons/deno-ibmi-<version>-<date>/`; the 3 most recent are kept | 5 s |

A rebuild on an already compiled tree only recompiles what changed (a few minutes).

The binary from step 5 is also left in `/QOpenSys/opt/denoibmi/croise/deno`: it is **not** in
service (the services use `/QOpenSys/opt/denoibmi/bin/deno`).

## 3. Putting it into service (IBM i administrator)

`ibmi/livrer.sh` (on IBMI: `/QOpenSys/opt/deno-ibmi/ibmi/livrer.sh`):

1. verifies the package's SHA-256 checksums and runs the binary (`--version`, `eval`);
2. keeps the version in service (`bin/ACTUELLE` → `bin/PRECEDENTE`), installs the new one atomically,
   replaces `libpaseat.a` only if it differs (dated backup copy);
3. cleanly stops the API (SIGTERM), DENOWS and the health monitor, waits for the subsystem to be fully
   stopped, restarts it (`STRSBS DENOIBMI/DENOWS`: the 3 autostart jobs DENOWS, DENOVEILLE, DENOAPI);
4. checks that `http://127.0.0.1:3081/bonjour`, `https://127.0.0.1:3444/bonjour` and
   `https://127.0.0.1:3091/api/sante` answer 200 within 60 s;
5. otherwise **rolls back by itself** to the previous version.

Service interruption: ≈ 30 s. `--retour` rolls back to the previous version at any time.

## 4. Upgrading Deno

1. **Patch review** on a clone of the new version (without touching the tree in service):
   ```bash
   git clone --depth 1 --branch v2.X.Y https://github.com/denoland/deno /tmp/deno-neuf
   mkdir -p /tmp/bilan && CORRECTIFS_BILAN=1 DENO_ARBRE=/tmp/deno-neuf \
     python3 ibmi/correctifs.py /QOpenSys/opt/denoibmi/crates-src /tmp/bilan
   ```
   The last line gives the number of patches that no longer apply; adapt them in
   `ibmi/correctifs.py` (they must remain valid for the old version as well).
2. **V8 version**: `grep '^v8 = ' /tmp/deno-neuf/Cargo.toml`. If it is no longer `150.4.0`, V8 must be
   rebuilt for AIX (§ 6) before anything else.
3. **Crates**: `preparer-arbre.sh` starts from the new version's Cargo.lock and applies our version
   bumps to it (never downgrading); it then lists the patched crates whose version changes compared
   with production (`comparer-crates.py`). If a patched crate changes: add the new version to the list
   in step 4 of `preparer-arbre.sh` and adapt `correctifs.py` / `deno/Cargo.toml.ibmi`.
4. **Tree**: `construire.sh` refuses a tree of another version. Move the old one aside
   (`mv /QOpenSys/opt/denoibmi/deno /QOpenSys/opt/denoibmi/deno-2.9.8`), then
   `VERSION_DENO=v2.X.Y bash construction/construire.sh`.

Trial run on 2026-11-06 on Deno's `main` (commit e7b39ebd): 1 patch adapted, 18 min, 99.87%.

**Known limitation**: the unit tests run on IBMI (`/QOpenSys/opt/denoibmi/denotests`, with its
`test_server`) and the x64 reference (`tests-deno/resultats-x64.jsonl`) are those of **2.9.8**. To
validate a new version with its own tests, redo them as described in
[`tests-deno/README.md`](../tests-deno/README.md).

## 5. Troubleshooting

| Symptom | Cause | Remedy |
|---|---|---|
| `ASP à NN % : construction refusée` | safeguard (75%) | free up space on IBMI (`/tmp/rustpoc`, old packages) |
| `Permission denied` on `emballer-lien.sh` or `cc-aix` | repository copied without executable modes | `chmod +x` (§ 1) |
| `L'arbre … est en X, pas en Y` | tree of another version | § 4, item 4 |
| `error[E0609]: no field sa_union` (signal-hook-registry) or another compilation error in a crate | crate version without AIX support | bump the crate (list in `preparer-arbre.sh`) or add a patch |
| `macros.rs : N occurrences au lieu de 7` | other Rust version | keep `RUST_VERSION=1.99.1` or adapt `preparer-rust.sh` |
| `lien de deno : rc=1` | link refused on IBMI | `/tmp/rustpoc/rejouer-lien.log` and `/QOpenSys/opt/denoibmi/croise/lien.txt` (on IBMI) |
| `0711-407 … .rint` at link time | `rust-src` not patched | `bash construction/preparer-rust.sh` |
| step 7 never ends, test_server stuck | tests submitted through `QSH CMD` (job without threads) | always `CALL QP2SHELL` (which is what the script does) |
| `export: … not an identifier` over ssh | profile's shell is `bsh` | `CALL QSYS2.SET_PASE_SHELL_INFO('DENOBUILD', '/QOpenSys/usr/bin/sh')` |
| `SEUIL NON ATTEINT` | real regression or flaky test | read `~/construction-deno/construire-HHMM.txt` (gaps listed); rerun once before concluding |
| `livrer.sh`: `STRSBS` refused with CPF1010 | subsystem not yet stopped | fixed (wait loop); the automatic rollback protects |

## 6. What is not automated (and when to touch it)

| Item | Where | When to redo it | How |
|---|---|---|---|
| **V8 for AIX** (`librusty_v8.a`, `src_binding_aix.rs`, `icudtb.dat`) | LINUXBUILD `~/v8aix` | V8 version change (`v8` crate) | [`v8aix/README.md`](../v8aix/README.md); manual round trip to IBM i (mksnapshot) |
| Objects assembled on IBM i (`libffi.a`, `libz.a`, `powerpc64_aix.o`) | `construction/objets-ibmi` | version change of libffi-sys, libz-sys or psm | [`construction/objets-ibmi/README.md`](objets-ibmi/README.md) |
| bindgen bindings (sqlite, aws-lc, nghttp2, libuv) | `liaisons/` | version change of these crates | `linux/generer_liaisons.sh` |
| Test suite and `test_server` on IBMI, x64 reference | `/QOpenSys/opt/denoibmi/denotests`, `tests-deno/` | new Deno version to validate with its own tests | [`tests-deno/README.md`](../tests-deno/README.md) |
| Setting up IBMI (once) | IBMI | new machine | § 7 |

## 7. Setting up a new IBM i machine (once)

Done on IBMI on 2026-11-05/06; only to be redone for another machine.

- Rust under PASE (`/QOpenSys/opt/rust`, Open XL runtime, thread-safe `libpaseat.a`): the repository's
  [main README](../README.md) ("Installing Rust under PASE") and `ibmi/paseat/construire.sh`.
- **DENOBUILD** profile: `USRCLS(*USER) SPCAUT(*NONE) PASSWORD(*NONE)`, `sh` shell
  (`QSYS2.SET_PASE_SHELL_INFO`), `~/.ssh/authorized_keys` containing LINUXBUILD's public key prefixed with
  `from="<adresse de LINUXBUILD>",no-port-forwarding,no-agent-forwarding,no-X11-forwarding`
  (`<adresse de LINUXBUILD>` = LINUXBUILD's address). Owner of
  `/QOpenSys/opt/denoibmi/{croise,deno,livraisons}` and `/QOpenSys/opt/deno-ibmi`; `*USE` on the
  DENOTEST profile (to submit the tests under that profile).
- **DENOTEST** profile: `*USER`, `*NONE`, group `DENOTSTG`, `*RWX` on `/QOpenSys/opt/denoibmi/denotests`.
- Services: [`essais/deno-ws/sous-systeme.md`](../essais/deno-ws/sous-systeme.md) (DENOWS subsystem,
  DENOAPP profile, start at IPL).

## Rules to follow on IBMI

- Never run a test or a service with `ulimit -d unlimited` (only the link step does): a runaway process
  once filled the ASP (incident of 2026-11-03). Stop safeguard at 80% during the tests.
- No `dbx64` attached to a running Deno.
- At most 4 test processes in parallel.
- No Deno service exposed beyond the internal network.

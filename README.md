# deno-ibmi: Rust and Deno on IBM i

**deno-ibmi** runs **Deno** 2.9.8 (the JavaScript/TypeScript runtime written in Rust, on the V8 engine)
on **IBM i 7.5**, inside PASE, and uses it to serve web services. To our knowledge, this is a first.

- **Deno 2.9.8 on V8**, cross-compiled on a Linux host and linked on IBM i, running in production-like
  use under PASE: a dedicated subsystem hosting a web service, a health monitor and a CRUD API over
  Db2 for i, started at IPL.
- **Deno's official unit tests: 99.87% of the applicable cases pass, with 0 Deno-specific gap**
  (compared case by case with an official x64 Deno 2.9.8; cases that do not apply to IBM i are excluded,
  each with a documented reason).
- **48-hour endurance test: 1.7 million requests, 0 errors** (mix of HTTP, HTTPS and Db2 routes).
- **Reproducible build in one command** from a fresh clone (about 18 minutes), tests and delivery
  package included.

What is new here is **Rust and Deno under PASE**. V8 itself already supports big-endian PowerPC and AIX,
thanks to the work IBM has done for Node.js on AIX and IBM i; this project builds on that support.

Author: **Sylvain AKTEPE**. This is a personal, unofficial project; see the [Disclaimer](#disclaimer).

> **Rebuilding Deno for IBM i: [`construction/README.md`](construction/README.md)** (one command on
> LINUXBUILD, tests and delivery package included; deployment with `ibmi/livrer.sh`).

## Status (2026-11-06)

- **Deno 2.9.8 on the V8 engine** (cross-compiled on LINUXBUILD, linked on IBM i) in service on IBMI
  since 2026-11-06: subsystem `DENOIBMI/DENOWS` (web service, health monitor, Db2 CRUD API), started at IPL.
- Deno's official unit tests: **99.87% of the applicable cases, 0 Deno-specific gap**; endurance
  test over 48 h: 1.7 million requests, 0 errors.
- Reproducible build in one command from a fresh clone (18 min), also tried on Deno's `main` branch
  (next version) with the same score.

Working machine: IBMI (Power S922, IBM i 7.5, 2 cores, 64 GB).

## Repository layout

| Directory | Contents |
|---|---|
| `construction/` | one-command build, prerequisite check, delivery ([guide](construction/README.md)) |
| `ibmi/rustenv.sh` | Rust environment under PASE (to be sourced) |
| `ibmi/paseat/` | **libpaseat**: PASE compatibility layer (see below) |
| `ibmi/correctifs.py` | replays all patches (crates and Deno sources) |
| `ibmi/build-deno.sh` | Deno build (submitted as a batch job) |
| `ibmi/livrer.sh` | installs a delivery package on IBM i (administrator) |
| `liaisons/` | pre-generated bindgen bindings for `powerpc64-ibm-aix` |
| `linux/generer_liaisons.sh` | generation of these bindings on Linux |
| `linux/croise/` | cross-compilation tools ([notes](linux/croise/README.md)) |
| `v8aix/` | V8 for IBM i, cross-compiled ([notes](v8aix/README.md)) |
| `tests-deno/` | Deno's official unit tests on IBM i vs. x64 reference ([notes](tests-deno/README.md)) |
| `outils/` | installp image (BFF) extractor, XCOFF import rewriting, WAMR stub |
| `poste/` | Windows workstation helpers (sending and fetching files via Mapepire) |
| `essais/` | Rust web service, Deno web service (`essais/deno-ws`), PASE diagnostics |

## Installing Rust under PASE (summary)

1. AIX 7.2 RPMs of the **IBM Open SDK for Rust on AIX** (AIX Toolbox, `RPMS/ppc-7.2/rust/`, free Community Edition) extracted into `/QOpenSys/opt/rust/1.96`, without going through the IBM i rpm database.
2. **IBM Open XL C/C++ 17.1.4.2 runtime** (Fix Central): `libc++`, `libc++abi`, `libunwind`, `libcompiler_rt` extracted from the installp images by `outils/bff_extract.py`, copied into `/QOpenSys/opt/rust/runtime` (never into `/QOpenSys/usr/lib`).
3. `libz` and `libatomic` from yum repackaged in the expected format (`archive.a(lib.so.N)`).
4. `.cargo.orig`: import table rewritten (`outils/xcoff_imports.py`) to use the OpenSSL from yum (avoids two instances of libcrypto).
5. Certificates: bundle built from `/QOpenSys/var/lib/ca-certificates/openssl` (the `cert.pem` on IBMI was empty).
6. `libpaseat`: `ibmi/paseat/construire.sh`.

Always start jobs with `SBMJOB CMD(CALL PGM(QP2SHELL) ...) ALWMLTTHD(*YES)`: under QSH, DNS resolution fails (`getaddrinfo() thread failed to start`).

## libpaseat: what PASE does differently from AIX

| Observed under PASE (IBM i 7.5) | Effect | Fix |
|---|---|---|
| `openat`, `fstatat`, `unlinkat`…: EINVAL whenever the directory is not `AT_FDCWD` | `std::fs::remove_dir_all` broken | emulated through the absolute path |
| `open(O_DIRECTORY)` succeeds on a regular file | wrong directory traversal | ENOTDIR restored |
| `fcntl(F_DUPFD_CLOEXEC)`: EINVAL | `try_clone`, tokio's signal driver | emulated with `F_DUPFD` + `FD_CLOEXEC` |

libpaseat is linked before libc (`RUSTFLAGS -l paseat`): the AIX linker then binds these symbols to it.

## Porting Deno: nature of the patches

- **`libc` crate incomplete for AIX**: `getifaddrs`, `dladdr`, `SOCK_CLOEXEC`, `in6_pktinfo`, `caddr_t` and `socklen_t` types… (nix, netif, quinn-udp, dlopen2, memmap2, rustix, rustyline, libsui).
- **AIX ABI**: `f64` aligned on 4 bytes (byteorder), libffi constants (`FFI_AIX`, 24-byte trampoline).
- **AIX headers**: `<sys/timer.h>` defines `func_data` (QuickJS), no `tm_gmtoff`, `SIZE_MAX` hidden (zlib-ng).
- **No libclang on IBM i**: bindings generated on Linux (`linux/`), injected back through `*_BINDINGS_FILE` variables.
- **Assembler**: `linux-ppc64le` (ELF) sources unusable; aws-lc in portable C (`AWS_LC_SYS_NO_ASM=1`).
- **Deno itself**: AIX branches (errno, signals, umask, system information, DNS, fs, napi) and **a big-endian bug** (`buffer.rs`, never compiled on such a target before).
- **WebAssembly**: WAMR assumes a little-endian machine (native memory accesses) and knows neither AIX nor PowerPC; replaced by a stub library pending wasmi.

## HTTPS

Two options, as with Node.js:

- **Native**: `Deno.serve({ port: 3444, cert, key })` (rustls, TLS 1.3, `TLS_AES_256_GCM_SHA384`, TLS 1.1 refused). Certificate created by `essais/deno-ws/apache/creer-certificat.sh` in `/QOpenSys/opt/denoibmi/tls`: local authority "deno-ibmi CA locale" (10 years) and certificate `CN=ibmi` with SAN `ibmi`, `localhost`, `192.0.2.82`, `127.0.0.1` (2 years). Key readable by `DENOAPP` only. On the client side, trust `ca.crt` (Windows curl: `--ssl-no-revoke`, the private authority has no revocation list).
- **Apache** (instance `DENOWS`, `essais/deno-ws/apache/httpd.conf`, same model as NODEWS): TLS on `*:3443` through the DCM application ID `QIBM_HTTP_SERVER_DENOWS`, forwarding to `127.0.0.1:3081`. `httpd.conf` must be tagged CCSID 1208 (`CHGATR ... ATR(*CCSID) VALUE(1208)`), otherwise Apache reads it as EBCDIC. The certificate is assigned in DCM (no scriptable way); without a certificate, the instance's jobs abort (HTP8351): do not leave it started.

## Db2 for i from Deno

`essais/deno-db2/db2.ts`: a TypeScript module with no native code, which calls the PASE SQL CLI (`libdb400.a(shr_64.o)`) through `Deno.dlopen`, as idb-connector, IBM's Node.js driver, does in C++ (CLI in UTF-8 through `SQLOverrideCCSID400(1208)`, server mode, columns read as characters then converted).

```ts
import { Db2 } from "./db2.ts";
const db = new Db2();                      // *LOCAL, profil du travail ; options : utilisateur, motDePasse, bibliotheque, nommageSysteme
const lignes = db.query("SELECT * FROM QSYS2.SYSTABLES WHERE TABLE_SCHEMA = ?", ["QSYS2"]);
db.execute("UPDATE ... WHERE ID = ?", [42]);   // { lignes, lignesTouchees }
```

(`new Db2()` connects to `*LOCAL` with the job's profile; options: `utilisateur` (user), `motDePasse`
(password), `bibliotheque` (library), `nommageSysteme` (system naming). `execute` returns
`{ lignes, lignesTouchees }`: rows and affected row count.)

Non-blocking version and connection pool (SQL execution runs in a Deno thread, the event loop keeps serving):

```ts
import { Db2Pool } from "./db2.ts";
const pool = new Db2Pool(4);               // 4 connexions, 4 travaux QSQSRVR
const lignes = await pool.query("SELECT ... WHERE X = ?", [x]);
await pool.avec(async (db) => { await db.executeAsync("UPDATE ..."); db.commit(); });  // transaction
```

(`new Db2Pool(4)` opens 4 connections, i.e. 4 QSQSRVR jobs; `pool.avec(...)` runs a transaction on one
connection.)

Measured on IBMI: 4 one-second queries (DLYJOB) in parallel in 1.04 s; 50 concurrent queries, all correct, in 29 ms.

Run with `--allow-ffi`. Types: integers, DOUBLE and DECIMAL up to 15 digits as numbers; BIGINT beyond 2^53 and large DECIMAL as strings; CHAR without trailing blanks; ISO dates and times; BLOB/BINARY as `Uint8Array`. `query`/`execute` are synchronous, `queryAsync`/`executeAsync` and `Db2Pool` are non-blocking.

## Running the Deno web service

Under a dedicated profile with no special authorities (`DENOAPP`: `*USER`, `PASSWORD(*NONE)`, `LMTCPB(*YES)`). The binary, `serveur.ts`, `ws.sh` and `db2.ts` are `*PUBLIC *RX` (the service cannot modify its own code, checked by `essais/deno-ws/verifier-droits.sh`); only `ws/logs` and `ws/cache` belong to `DENOAPP`.

```
SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/sh' '/QOpenSys/opt/denoibmi/ws/ws.sh'))
       JOB(DENOWS) USER(DENOAPP) INLLIBL(*JOBD) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)
```

`INLLIBL(*JOBD)`: otherwise the submitter's library list is copied (CPF1266 if the profile is not authorized to it).

`ws.sh` (in `essais/deno-ws`) sets `DENO_NO_UPDATE_CHECK=1`: without it, the update check of `deno run` (outgoing HTTPS fetch) makes the process abort.

In service, the web service runs in its own subsystem started at IPL: see
[`essais/deno-ws/sous-systeme.md`](essais/deno-ws/sous-systeme.md).

## Known limitations

- **WAMR is not available**: WAMR (used by Deno for a few internal WebAssembly helpers) assumes a
  little-endian machine and knows neither AIX nor PowerPC; it is replaced by a stub library (`outils/`).
  The standard `WebAssembly` API is provided by V8 and works (`WebAssembly.instantiate`, verified).
- **`deno compile` is unusable**: XCOFF binaries have no embedded section for the payload.
- **Tests excluded as not applicable on IBM i**: a small set of official unit tests is excluded from the
  "applicable" score, each with its documented reason in
  [`tests-deno/comparer-unit.py`](tests-deno/comparer-unit.py): no GPU (WebGPU, canvas), no esbuild binary
  for AIX, IFS timestamps with one-second resolution, no `/dev/fd` in PASE, IBM i ephemeral port range,
  vsock (Linux only), AIX `flock` semantics (fcntl locks), etc. The remaining 3 gaps of the reference run
  are due to the test bench, not to Deno (PASE curl built without HTTP/2; a 4 GB ArrayBuffer under the
  8 GB `ulimit -d` safety cap).
- **Building requires both an IBM i and a Linux host**: the Rust and V8 code is cross-compiled on Linux,
  but XCOFF binaries must be linked with the AIX `ld` of PASE, and Deno's startup snapshot must be produced
  by a big-endian V8, hence on IBM i.
- **`Deno.resolveDns` fails**: PASE has no `/etc/resolv.conf` (ordinary name resolution, as used by
  `fetch` and `Deno.connect`, works).
- **`Deno.loadavg()` returns `0,0,0`**: not provided by PASE.
- **`Deno.networkInterfaces()`**: interfaces are named after their IP address and have no MAC address
  (PASE `SIOCGIFCONF`).

Verified working on the V8 build (2026-11-06): `WebAssembly`, `Deno.Command`, `node:crypto`,
`Deno.osUptime()`, `Deno.systemMemoryInfo()`, natural process exit after asynchronous Db2 calls.

## Disclaimer

This is a personal, unofficial project, provided as is, without any warranty or support. It is not
affiliated with, endorsed by or supported by Deno Land Inc. or IBM. "Deno" is a trademark of
Deno Land Inc.; IBM i, AIX and Power are trademarks of IBM.

## License

MIT (see [LICENSE](LICENSE)).

## Author

Sylvain AKTEPE.

## History

Milestones of the first port, on the QuickJS engine (2026-10-29), kept for the record:

| Milestone | Status |
|---|---|
| rustc / cargo 1.96 under PASE (IBM's AIX Rust SDK, Community Edition) | done |
| Rust program (threads, panic, IFS) | done |
| Rust axum + tokio web service served by IBM i | done (HTTP 200, 40 ms) |
| All Deno 2.9.8 crates (QuickJS engine) compile | done |
| Linking of the `deno` binary | done (profile `ibmi-o1`, 493 MB) |
| `deno --version`, `deno eval`, `deno run` of a `.ts` | done (10/29, 5:52 pm) |
| `Deno.serve()` on IBM i, called from a workstation | done (10/29, 6:23 pm: HTTP 200, ~40 ms, 200/200) |
| Outgoing HTTPS `fetch()`, certificate verified | done (10/30) |
| `Deno.serve()` with an asynchronous handler (timer, file, fetch) | done (10/30, mio patch) |
| Db2 for i access (`essais/deno-db2/db2.ts`, FFI over the `libdb400` CLI) | done (10/30: 0.5 ms per prepared statement, UTF-8, LOB, SQLSTATE errors) |
| Deno web service reading Db2, called from a workstation | done (10/30, routes `/db2/*`) |
| Native Deno HTTPS (rustls, TLS 1.3) on 3444 | done (10/30, local deno-ibmi authority) |
| HTTPS through Apache (DENOWS instance, reverse proxy 3443) | configured; waiting for the certificate in DCM |
| WebAssembly (wasmi instead of WAMR) | to do |
| V8 engine | to do |

The V8 engine has since replaced QuickJS: see [Status](#status-2026-11-06).

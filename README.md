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

> ⚠️ **A fun project, first and foremost.** This is an experiment done for the pleasure of seeing it work,
> not a product. It comes **with no warranty, no support and no liability of any kind**: you use it
> entirely at your own risk, and the author accepts no responsibility for any damage, data loss,
> outage or other consequence. Do not run it on a production system without reviewing and testing it
> yourself. Third-party rights (trademarks, licenses, IBM software) are listed in the
> [Disclaimer](#disclaimer) and in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

> **Rebuilding Deno for IBM i: [`build/README.md`](build/README.md)** (one command on
> LINUXBUILD, tests and delivery package included; deployment with `ibmi/deploy.sh`).

## Install with yum

Deno is available as a signed RPM from a third-party yum repository, the same way as the IBM i open-source
packages. Requirements: **IBM i 7.5 or later**, POWER8 or later, the IBM yum environment
(`/QOpenSys/pkgs/bin` in the `PATH`). As an administrator, in ssh or QP2TERM:

```
curl -o /QOpenSys/etc/yum/repos.d/deno-ibmi.repo https://yum.job-i.fr/deno-ibmi/deno-ibmi.repo
yum install deno
```

On the first installation, yum asks you to accept the signing key
(`RPM-GPG-KEY-deno-ibmi`, Sylvain AKTEPE, fingerprint `8182 36E7 94FB B0BF D6DE  D98C 003F 3EDC D33E 3056`).
Then:

```
deno --version
deno eval "console.log(Deno.build.os, Deno.build.arch)"     # aix powerpc64
```

| Installed | Path |
|---|---|
| `deno` command | `/QOpenSys/pkgs/bin/deno` (launcher, sets `XPG_SUS_ENV=ON` and `DENO_NO_UPDATE_CHECK=1` by default) |
| binary and runtime libraries | `/QOpenSys/pkgs/lib/deno/` (`deno`, `denort` for `deno compile`, `libpaseat.a`, IBM `libunwind.a`) |
| Db2 for i module | `/QOpenSys/pkgs/share/deno/db2.ts` (`import { Db2 } from "/QOpenSys/pkgs/share/deno/db2.ts"`, run with `--allow-ffi`) |
| licenses | `/QOpenSys/pkgs/share/licenses/deno/` |

Update with `yum upgrade deno`, remove with `yum remove deno`. IBM i 7.3 is not supported (its PASE libc lacks
functions the binary needs) and 7.4 is not tested; rpm refuses the package below 7.5.

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
| `build/` | one-command build, prerequisite check, delivery ([guide](build/README.md)) |
| `ibmi/rustenv.sh` | Rust environment under PASE (to be sourced) |
| `ibmi/paseat/` | **libpaseat**: PASE compatibility layer (see below) |
| `ibmi/patches.py` | replays all patches (crates and Deno sources) |
| `ibmi/build-deno.sh` | Deno build (submitted as a batch job) |
| `ibmi/deploy.sh` | installs a delivery package on IBM i (administrator) |
| `bindings/` | pre-generated bindgen bindings for `powerpc64-ibm-aix` |
| `linux/generate_bindings.sh` | generation of these bindings on Linux |
| `linux/cross/` | cross-compilation tools ([notes](linux/cross/README.md)) |
| `v8aix/` | V8 for IBM i, cross-compiled ([notes](v8aix/README.md)) |
| `deno-tests/` | Deno's official unit tests on IBM i vs. x64 reference ([notes](deno-tests/README.md)) |
| `tools/` | installp image (BFF) extractor, XCOFF import rewriting, WAMR stub |
| `workstation/` | Windows workstation helpers (sending and fetching files via Mapepire) |
| `examples/` | Rust web service, Deno web service (`examples/deno-ws`), PASE diagnostics |

## Installing Rust under PASE (summary)

1. AIX 7.2 RPMs of the **IBM Open SDK for Rust on AIX** (AIX Toolbox, `RPMS/ppc-7.2/rust/`, free Community Edition) extracted into `/QOpenSys/opt/rust/1.96`, without going through the IBM i rpm database.
2. **IBM Open XL C/C++ 17.1.4.2 runtime** (Fix Central): `libc++`, `libc++abi`, `libunwind`, `libcompiler_rt` extracted from the installp images by `tools/bff_extract.py`, copied into `/QOpenSys/opt/rust/runtime` (never into `/QOpenSys/usr/lib`).
3. `libz` and `libatomic` from yum repackaged in the expected format (`archive.a(lib.so.N)`).
4. `.cargo.orig`: import table rewritten (`tools/xcoff_imports.py`) to use the OpenSSL from yum (avoids two instances of libcrypto).
5. Certificates: bundle built from `/QOpenSys/var/lib/ca-certificates/openssl` (the `cert.pem` on IBMI was empty).
6. `libpaseat`: `ibmi/paseat/build.sh`.

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

- **Native**: `Deno.serve({ port: 3444, cert, key })` (rustls, TLS 1.3, `TLS_AES_256_GCM_SHA384`, TLS 1.1 refused). Certificate created by `examples/deno-ws/apache/create-certificate.sh` in `/QOpenSys/opt/denoibmi/tls`: local authority "deno-ibmi CA locale" (10 years) and certificate `CN=ibmi` with SAN `ibmi`, `localhost`, `192.0.2.82`, `127.0.0.1` (2 years). Key readable by `DENOAPP` only. On the client side, trust `ca.crt` (Windows curl: `--ssl-no-revoke`, the private authority has no revocation list).
- **Apache** (instance `DENOWS`, `examples/deno-ws/apache/httpd.conf`, same model as NODEWS): TLS on `*:3443` through the DCM application ID `QIBM_HTTP_SERVER_DENOWS`, forwarding to `127.0.0.1:3081`. `httpd.conf` must be tagged CCSID 1208 (`CHGATR ... ATR(*CCSID) VALUE(1208)`), otherwise Apache reads it as EBCDIC. The certificate is assigned in DCM (no scriptable way); without a certificate, the instance's jobs abort (HTP8351): do not leave it started.

## Db2 for i from Deno

`examples/deno-db2/db2.ts`: a TypeScript module with no native code, which calls the PASE SQL CLI (`libdb400.a(shr_64.o)`) through `Deno.dlopen`, as idb-connector, IBM's Node.js driver, does in C++ (CLI in UTF-8 through `SQLOverrideCCSID400(1208)`, server mode, columns read as characters then converted).

```ts
import { Db2 } from "./db2.ts";
const db = new Db2();                      // *LOCAL, job profile; options: user, password, library, systemNaming
const rows = db.query("SELECT * FROM QSYS2.SYSTABLES WHERE TABLE_SCHEMA = ?", ["QSYS2"]);
db.execute("UPDATE ... WHERE ID = ?", [42]);   // { rows, rowsAffected }
```

(`new Db2()` connects to `*LOCAL` with the job's profile; options: `user`, `password`, `library`
(default schema), `systemNaming` (*SYS naming), `database`, `autocommit`. `execute` returns
`{ rows, rowsAffected }`: rows and affected row count.)

Non-blocking version and connection pool (SQL execution runs in a Deno thread, the event loop keeps serving):

```ts
import { Db2Pool } from "./db2.ts";
const pool = new Db2Pool(4);               // 4 connections, 4 QSQSRVR jobs
const rows = await pool.query("SELECT ... WHERE X = ?", [x]);
await pool.withConnection(async (db) => { await db.executeAsync("UPDATE ..."); db.commit(); });  // transaction
```

(`new Db2Pool(4)` opens 4 connections, i.e. 4 QSQSRVR jobs; `pool.withConnection(...)` runs a transaction on one
connection; `pool.stats` gives `{ size, open, idle, waiting }`.)

Measured on IBMI: 4 one-second queries (DLYJOB) in parallel in 1.04 s; 50 concurrent queries, all correct, in 29 ms.

**Pooled connections and job state.** Each connection runs in server mode, i.e. in its own QSQSRVR job, under
the profile it was opened with (the job's profile when no user is given). That job is reused by the next
request, so anything a request changes in it (library list, current schema, QTEMP objects such as declared
global temporary tables, uncommitted work) would be inherited by the next borrower. The `reset` option of
`Db2Pool` decides what happens when a connection goes back to the pool:

| `reset` | Effect |
|---|---|
| `"restore"` (default) | roll back uncommitted work, restore the initial current schema, SQL path (`CURRENT PATH`) and library list, clear QTEMP; on failure the connection is discarded |
| `"discard"` | close the connection; the next request gets a fresh one |
| `"none"` | nothing is reset: only for fully qualified names and no statement that changes the job state |

`"restore"` covers only what is listed above. **Global variable values** (`SET MYLIB.MYVAR = ...`),
**job-level environment variables** (`ADDENVVAR ... LEVEL(*JOB)`) and **job attributes changed with
`CHGJOB`** (`DATFMT`, etc.) have no simple reset and are still seen by the next request: if requests do
any of that, use `"discard"`.

The reset runs after the result has been returned, so it does not add latency to the request.
`examples/deno-db2/test-pool-isolation.ts` reproduces the leak with `"none"` (added library, `SET SCHEMA`,
`SET PATH`, QTEMP table, global variable, environment variable, `CHGJOB DATFMT` all still there on the
next request), shows that `"restore"` removes the first four but not the last three, and that
`"discard"` removes them all (verified on IBM i 7.5, 2026-11-10).

**Unqualified names with system naming.** Once a default schema is set, either with `SET SCHEMA` or with the
`library` option (connection attribute `SQL_ATTR_DBC_DEFAULT_LIB`), unqualified table names resolve in that
schema and **no longer through `*LIBL`**, even if another library holding the same table comes first in the
library list, or the default schema's library is not in the list at all. "Default schema" and
"system naming + CHGLIBL" are therefore two alternatives, not options to combine. Simplest rule for pooled
connections: use fully qualified names.

Run with `--allow-ffi`. Types: integers, DOUBLE and DECIMAL up to 15 digits as numbers; BIGINT beyond 2^53 and large DECIMAL as strings; CHAR without trailing blanks; ISO dates and times; BLOB/BINARY as `Uint8Array`. `query`/`execute` are synchronous, `queryAsync`/`executeAsync` and `Db2Pool` are non-blocking.

## Running the Deno web service

Under a dedicated profile with no special authorities (`DENOAPP`: `*USER`, `PASSWORD(*NONE)`, `LMTCPB(*YES)`). The binary, `serveur.ts`, `ws.sh` and `db2.ts` are `*PUBLIC *RX` (the service cannot modify its own code, checked by `examples/deno-ws/check-authorities.sh`); only `ws/logs` and `ws/cache` belong to `DENOAPP`.

```
SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/sh' '/QOpenSys/opt/denoibmi/ws/ws.sh'))
       JOB(DENOWS) USER(DENOAPP) INLLIBL(*JOBD) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)
```

`INLLIBL(*JOBD)`: otherwise the submitter's library list is copied (CPF1266 if the profile is not authorized to it).

`ws.sh` (in `examples/deno-ws`) sets `DENO_NO_UPDATE_CHECK=1`: without it, the update check of `deno run` (outgoing HTTPS fetch) makes the process abort.

In service, the web service runs in its own subsystem started at IPL: see
[`examples/deno-ws/subsystem.md`](examples/deno-ws/subsystem.md).

## Single executables: `deno compile`

`deno compile` turns a program (TypeScript, local modules, npm packages, `db2.ts`) into one IBM i
executable that runs without Deno installed:

```
deno compile --allow-net --allow-ffi --output /home/ME/app app.ts
SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/home/ME/app' 'arg1')) ALWMLTTHD(*YES)
```

The runtime it starts from (`denort`, ≈ 214 MB) is shipped by the RPM in `/QOpenSys/pkgs/lib/deno`,
next to `deno`; there is nothing to download. The program is appended after the end of the XCOFF file,
which the AIX loader ignores, and read back at startup. The executable sets `XPG_SUS_ENV=ON` by itself
(it re-executes once, like `deno`). Verified on IBM i 7.5 (2026-11-12): Db2 through FFI, an npm package,
`Deno.serve` and `fetch`, started from the `PATH`, from a relative path and through `SBMJOB`; startup in
0.3 s. Only IBM i targets: `--target` for another system would need the `denort` of that system.

## Known limitations

- **WAMR is not available**: WAMR (used by Deno for a few internal WebAssembly helpers) assumes a
  little-endian machine and knows neither AIX nor PowerPC; it is replaced by a stub library (`tools/`).
  The standard `WebAssembly` API is provided by V8 and works (`WebAssembly.instantiate`, verified).
- **Tests excluded as not applicable on IBM i**: a small set of official unit tests is excluded from the
  "applicable" score, each with its documented reason in
  [`deno-tests/compare-unit.py`](deno-tests/compare-unit.py): no GPU (WebGPU, canvas), no esbuild binary
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

**No liability.** This is a personal, unofficial hobby project, provided "as is", without warranty of
any kind, express or implied, and without support. The author accepts **no responsibility** for any
use of this code or of the binaries built with it, nor for any direct or indirect damage (data loss,
system outage, security incident, ASP full, etc.). You are solely responsible for what you run on your
machines. See also the [LICENSE](LICENSE) (MIT), whose warranty and liability disclaimer applies in full.

**Not affiliated.** This project is not affiliated with, sponsored, endorsed or supported by
Deno Land Inc., IBM or any other company.

**What is subject to third-party rights:**

- **Trademarks**: "Deno" and the Deno logo are trademarks of Deno Land Inc. IBM, IBM i, AIX, Power,
  Db2 and PASE are trademarks of International Business Machines Corporation. Other names may be
  trademarks of their respective owners. They are used here only to describe what the project works
  with.
- **Patched open-source code**: the patches modify Deno (MIT), rusty_v8 (MIT), V8 (BSD-3-Clause) and
  many Rust crates (mostly MIT and/or Apache-2.0). The patched code remains under its original
  license and copyright.
- **Files built from third-party sources** (libffi, zlib-ng, psm objects, bindgen bindings of SQLite,
  AWS-LC, nghttp2, libuv and V8 headers): each one stays under its own license, listed in
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **IBM software**: the IBM Open SDK for Rust on AIX, the IBM Open XL C/C++ compiler and runtime, the
  PASE SQL CLI (`libdb400`) and IBM i itself must be obtained from IBM and used under IBM's license
  terms. The only IBM file redistributed is in the RPM: `libunwind.a`, unmodified, from the IBM XL C/C++
  for AIX 17.1.3 Runtime Environment, whose License Information lists it among the Redistributables;
  IBM provides it "AS IS", without warranty or support (details in
  [`packaging/THIRD_PARTY_LICENSES.md`](packaging/THIRD_PARTY_LICENSES.md)).
- **Binaries**: this repository contains no Deno or V8 binary, only the means to build one. The RPM of
  the yum repository contains a binary built with it; it includes third-party code under the licenses
  listed in [`packaging/THIRD_PARTY_LICENSES.md`](packaging/THIRD_PARTY_LICENSES.md) (installed in
  `/QOpenSys/pkgs/share/licenses/deno/`), and comes under the same "no warranty, no liability" terms as
  the rest of the project.

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
| Db2 for i access (`examples/deno-db2/db2.ts`, FFI over the `libdb400` CLI) | done (10/30: 0.5 ms per prepared statement, UTF-8, LOB, SQLSTATE errors) |
| Deno web service reading Db2, called from a workstation | done (10/30, routes `/db2/*`) |
| Native Deno HTTPS (rustls, TLS 1.3) on 3444 | done (10/30, local deno-ibmi authority) |
| HTTPS through Apache (DENOWS instance, reverse proxy 3443) | configured; waiting for the certificate in DCM |
| WebAssembly (wasmi instead of WAMR) | to do |
| V8 engine | to do |

The V8 engine has since replaced QuickJS: see [Status](#status-2026-11-06).

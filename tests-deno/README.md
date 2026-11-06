# Deno's official tests on IBM i

Deno 2.9.8 unit tests (`tests/unit/*_test.ts`, 104 files), run the way
`tests/unit/mod.rs` runs them, on IBM i and on an official x64 Deno 2.9.8 (reference). An
IBM i-specific gap is a case that passes on x64 and fails on IBM i.

## Preparation (LINUXBUILD)
```
git clone --depth 1 --branch v2.9.8 https://github.com/denoland/deno ~/denogit
cd ~/denogit && git submodule update --init --depth 1 tests/util/std
# x64 reference Deno: release v2.9.8 deno-x86_64-unknown-linux-gnu.zip unpacked in ~/denoref
python3 preparer-test-server.py /QOpenSys/opt/denoibmi/deno
source ~/deno-ibmi/linux/croise/env-croise.sh && cd /QOpenSys/opt/denoibmi/deno
cargo +1.99.1 build -p test_server --release                       # x64
cargo +1.99.1 build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix \
  --profile ibmi-rel -p test_server                                # IBM i (link replayed)
```
(The x64 reference Deno is the v2.9.8 release `deno-x86_64-unknown-linux-gnu.zip`, unpacked in
`~/denoref`. The first `test_server` build is for x64, the second for IBM i, whose link is replayed.)

On IBM i: `BINAIRE=test_server PROFIL=ibmi-rel` for `ibmi/rejouer-lien.sh` (as an SBMJOB).
Test tree: `~/denogit` without `.git`, `target`, `tests/{wpt,node_compat,bench,specs}`
→ `/QOpenSys/opt/denoibmi/denotests`, with `test_server` in `target/aix/` (the server derives
the repository root from its own path: `<root>/target/<x>/test_server`).

## Running
```
python3 unit.py <root> <deno> <test_server> <output.jsonl> [parallelism] [filter]
python3 comparer-unit.py ibmi.jsonl x64.jsonl
```
(`unit.py` arguments: root, deno binary, test_server binary, output `.jsonl`, optional parallelism and
filter.) The test_server only listens on 127.0.0.1 and ::1.

`comparer-unit.py` computes two indicators: the share of x64-passing cases that also pass on IBM i, and
the share of **applicable** cases. Cases that the test itself skips on this OS, the GPU and esbuild
files, and IBM i / PASE-specific cases (each listed with its verified reason in the script) are
excluded from the applicable cases; remaining gaps due to the test bench rather than to Deno are counted
but reported separately.

## Ordinary test profile (2026-11-05)

The x64 reference runs under an ordinary user: on IBM i, the tests therefore run under
`DENOTEST` (USRCLS *USER, SPCAUT *NONE, PASSWORD *NONE), member of group `DENOTSTG` (GID 104), which has
`*RWX` on `/QOpenSys/opt/denoibmi/denotests` (CHGAUT SUBTREE(*ALL)). Under an *ALLOBJ profile (
equivalent to root), `chown*PermissionDenied` and `getGid` failed. Launch:

    SBMJOB CMD(QSH CMD('NOM=passe9 /QOpenSys/usr/bin/sh /tmp/rustpoc/unit-denotest.sh'))
           JOB(PASSE9) USER(DENOTEST) INLLIBL(*JOBD) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)

IBMI's TCP/IP host name was set on 2026-11-05 (`CHGTCPDMN HOSTNAME('IBMI') DMNNAME('example.com')`;
it was UNKNOWN, and `Deno.hostname()` returned "").

Run 9: 97.08% raw, **99.87% of the applicable cases** (3 gaps: PASE curl without HTTP/2,
a 4 GB ArrayBuffer under the 8 GB `ulimit -d` cap).

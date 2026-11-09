"""Compares Deno unit test results on IBM i against the x64 reference (same version, same runner).

A test case is an IBM i-specific discrepancy only if it passes on x64 and fails on IBM i. A file
that produces no test case (crash, timeout) counts all x64 cases of that file as failed.
Usage: python3 compare-unit.py <ibmi.jsonl> <x64.jsonl>
"""
import collections
import json
import sys


import re

# Some test case names contain a date generated at run time ("set and get invalid key
# [ 2026-11-03T09:19:52.… ]"): it is masked so that x64 and IBM i cases can be matched.
DATE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z")


def read_results(f):
    results = {}
    for r in map(json.loads, filter(str.strip, open(f, encoding="utf-8"))):
        r["cas"] = {DATE.sub("<date>", k): v for k, v in r["cas"].items()}
        results[r["fichier"]] = r
    return results


ibmi, x64 = read_results(sys.argv[1]), read_results(sys.argv[2])
ref_ok = ibmi_ok = ignored = 0
discrepancies = collections.defaultdict(list)
for file, x64_result in sorted(x64.items()):
    ibmi_result = ibmi.get(file, {"cas": {}, "code": "absent", "sortie": ""})
    for test_case, x64_status in x64_result["cas"].items():
        if x64_status == "ignored":
            ignored += 1
            continue
        if x64_status != "ok":
            continue                      # already fails on x64: reference environment
        ref_ok += 1
        ibmi_status = ibmi_result["cas"].get(test_case, "missing (file exit code=%s)" % ibmi_result["code"])
        if ibmi_status == "ok":
            ibmi_ok += 1
        else:
            discrepancies[file].append((test_case, ibmi_status))
print(f"x64 passing cases: {ref_ok} (+{ignored} ignored by the tests)")
print(f"also passing on IBM i: {ibmi_ok} = {100 * ibmi_ok / ref_ok:.2f} %")
print(f"discrepancies: {ref_ok - ibmi_ok} in {len(discrepancies)} files")

# Second metric: cases APPLICABLE to IBM i. The following are removed, and listed by name:
# - cases that the test itself declares not applicable on this OS ("ignored" on IBM i:
#   ignore: Deno.build.os !== "linux", vsock, abstract sockets, /proc…);
# - the GPU (IBM i has none, wgpu does not know AIX) and esbuild (no AIX binary).
OFF_PLATFORM_FILES = {"webgpu_test", "canvas_test", "bundle_test"}
# Discrepancies caused by IBM i / PASE itself, verified one by one (reason alongside):
OFF_PLATFORM_CASES = {
    "display GPUTexture": "GPU",
    "utimeSyncFileDateSuccess": "IFS: timestamps to the second (checked in C, utimensat)",
    "utimeFileDateSuccess": "IFS: timestamps to the second (checked in C, utimensat)",
    "utimeSyncLargeNumberSuccess": "IFS: date > 2^32 s rejected, EINVAL (checked in C)",
    "readDirDevFd": "PASE has no /dev/fd",
    "readDirDevFdSync": "PASE has no /dev/fd",
    "netUdpListenEphemeralClose": "IBM i ephemeral port range (the test expects the Linux one)",
    "netTcpListenEphemeralClose": "IBM i ephemeral port range (random port from 1024)",
    "createHttpClientWithVsockProxy": "vsock: Linux only",
    "buildInfo": "the OS list of the test does not contain aix",
    "nonExistentCwd": "PASE refuses rmdir of a process current directory (EBUSY)",
    "\"Blob\" colorSpaceConversion: \"none\"": "the test reads the u16 values as little-endian (same pixel)",
    "imageBitmapFromBlobColorspaceConversion": "step above",
    # AIX flock = fcntl locks: owned by the process (2 descriptors of the same process do not
    # exclude each other) and no exclusive lock on a file opened read-only (EBADF), verified
    "fsFileLockFileSync": "AIX flock: exclusive lock refused on a read-only file (EBADF)",
    "fsFileLockFileAsync": "AIX flock: exclusive lock refused on a read-only file (EBADF)",
    "fsFileTryLockSync": "AIX flock: lock owned by the process, not by the descriptor",
    "fsFileTryLockAsync": "AIX flock: lock owned by the process, not by the descriptor",
    "fsFileTryLockSharedSync": "AIX flock: lock owned by the process, not by the descriptor",
}
# Discrepancies still COUNTED, but caused by the test bench, not by Deno (fixable by configuration):
TEST_BENCH_CASES = {
    "hostnameDir": "TCP/IP host name of IBMI not configured (CFGTCP 12: UNKNOWN)",
    "hostnameWithoutOtherNetworkUsages": "TCP/IP host name of IBMI not configured",
    "getGid": "tests run as an *ALLOBJ profile, without a group (gid 0); x64: ordinary user",
    "chownSyncPermissionDenied": "tests run as an *ALLOBJ profile (*ALLOBJ, root equivalent)",
    "chownPermissionDenied": "tests run as an *ALLOBJ profile (*ALLOBJ, root equivalent)",
    "httpServeCurlH2C": "PASE curl built without HTTP/2",
    "httpsServeCurlH2C": "PASE curl built without HTTP/2",
    "inspectLargeArrayBuffer": "4 GB ArrayBuffer: ulimit -d cap of 8 GB (ASP safeguard)",
    "tlsHandshakeWithTcpCorruptionImmediately": "flaky (2 passes out of 5, with and without the patches)",
}
off_platform_detail = [(f, test_case, e) for f, l in discrepancies.items() for test_case, e in l
               if e == "ignored" or f in OFF_PLATFORM_FILES
               or test_case.split(" > ")[-1] in OFF_PLATFORM_CASES]
off_platform = len(off_platform_detail)
applicable = ref_ok - off_platform
print(f"off-platform (ignored by the test on AIX, GPU, esbuild): {off_platform}")
for f, test_case, e in off_platform_detail:
    name = test_case.split(" > ")[-1]
    if e != "ignored" and f not in OFF_PLATFORM_FILES:
        print(f"   - {f} > {name[:50]}: {OFF_PLATFORM_CASES[name]}")
print(f"applicable cases on IBM i: {applicable}, passed: {ibmi_ok} = {100 * ibmi_ok / applicable:.2f} %"
      f" ({applicable - ibmi_ok} discrepancies)")
remaining = [(f, test_case.split(" > ")[-1]) for f, l in discrepancies.items() for test_case, e in l
            if (f, test_case, e) not in off_platform_detail]
env = [(f, n) for f, n in remaining if n in TEST_BENCH_CASES]
print(f"   of which test bench environment: {len(env)}")
for f, n in env:
    print(f"   - {f} > {n[:50]}: {TEST_BENCH_CASES[n]}")
print(f"   of which Deno-specific on IBM i: {len(remaining) - len(env)}")
for f, n in remaining:
    if n not in TEST_BENCH_CASES:
        print(f"   - {f} > {n[:60]}")
for file, l in sorted(discrepancies.items(), key=lambda x: -len(x[1])):
    print(f"\n## {file}: {len(l)} discrepancy(ies), IBM i exit code = {ibmi.get(file, {}).get('code')}")
    for test_case, e in l[:8]:
        print(f"   {test_case[:70]:70} {e[:110]!r}")
    if len(l) > 8:
        print(f"   … and {len(l) - 8} more")

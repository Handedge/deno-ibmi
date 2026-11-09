"""Compares the versions of patched crates (and of a few sensitive crates) between two Cargo.lock files.

Used to prepare a Deno version upgrade: a patched crate whose version changes requires updating
patches.py, configure-cargo.py and the crate list in prepare-tree.sh.
Usage: python3 compare-crates.py <current Cargo.lock> <Cargo.lock of the new version>
"""
import re
import sys

WATCHED_CRATES = ["inventory", "mio", "signal-hook", "notify", "v8", "deno_core_icudata", "open", "libsui",
               "rustyline", "memmap2", "dlopen2", "libuv-sys-lite", "libffi-sys", "quinn-udp", "libnghttp2",
               "rustix", "netif", "libsqlite3-sys", "libz-sys", "nix", "aws-lc-sys", "byteorder", "tokio", "v8x"]


def read_versions(path):
    versions = {}
    for block in open(path, encoding="utf-8").read().split("[[package]]"):
        n = re.search(r'^name = "(.+)"', block, re.M)
        v = re.search(r'^version = "(.+)"', block, re.M)
        if n and v:
            versions.setdefault(n.group(1), set()).add(v.group(1))
    return versions


a, b = read_versions(sys.argv[1]), read_versions(sys.argv[2])
changed = 0
for c in WATCHED_CRATES:
    x, y = ",".join(sorted(a.get(c, []))), ",".join(sorted(b.get(c, [])))
    marker = "" if x == y else "  ← CHANGED"
    changed += x != y
    print(f"   {c:20} {x:26} → {y:26}{marker}")
print(f"{changed} watched crate(s) change version")

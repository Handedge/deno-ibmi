"""Compares the versions of patched crates (and of a few sensitive crates) between two Cargo.lock files.

Used to prepare a Deno version upgrade: a patched crate whose version changes requires updating
correctifs.py, configurer-cargo.py and the crate list in preparer-arbre.sh.
Usage: python3 comparer-crates.py <current Cargo.lock> <Cargo.lock of the new version>
"""
import re
import sys

SURVEILLEES = ["inventory", "mio", "signal-hook", "notify", "v8", "deno_core_icudata", "open", "libsui",
               "rustyline", "memmap2", "dlopen2", "libuv-sys-lite", "libffi-sys", "quinn-udp", "libnghttp2",
               "rustix", "netif", "libsqlite3-sys", "libz-sys", "nix", "aws-lc-sys", "byteorder", "tokio", "v8x"]


def lire(chemin):
    versions = {}
    for bloc in open(chemin, encoding="utf-8").read().split("[[package]]"):
        n = re.search(r'^name = "(.+)"', bloc, re.M)
        v = re.search(r'^version = "(.+)"', bloc, re.M)
        if n and v:
            versions.setdefault(n.group(1), set()).add(v.group(1))
    return versions


a, b = lire(sys.argv[1]), lire(sys.argv[2])
changees = 0
for c in SURVEILLEES:
    x, y = ",".join(sorted(a.get(c, []))), ",".join(sorted(b.get(c, [])))
    marque = "" if x == y else "  ← CHANGE"
    changees += x != y
    print(f"   {c:20} {x:26} → {y:26}{marque}")
print(f"{changees} crate(s) surveillée(s) changent de version")

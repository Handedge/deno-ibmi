"""Compare mjsunit on IBM i with a Linux x64 reference built with the same options.

A test is a port-specific discrepancy only if it passes on x64 and fails on IBM i (the
V8 status file does not cover our release, no-sandbox configuration, hence this
reference). Pass: exit code 0 (d8 handles --throws).
Usage: python3 compare-mjsunit.py <ibmi.jsonl> <x64.jsonl>
"""
import collections
import json
import re
import sys


def read_results(f):
    out = {}
    for l in open(f):
        if l.strip():
            r = json.loads(l)
            r["ok"] = r["code"] == 0
            out[r["test"]] = r
    return out


ibmi, x64 = read_results(sys.argv[1]), read_results(sys.argv[2])
common = sorted(set(ibmi) & set(x64))
c = collections.Counter()
ibmi_only = []
for t in common:
    a, b = ibmi[t]["ok"], x64[t]["ok"]
    c[("IBM i OK" if a else "IBM i KO", "x64 OK" if b else "x64 KO")] += 1
    if b and not a:
        ibmi_only.append(ibmi[t])
n = len(common)
print(f"{n} tests in common")
for k, v in sorted(c.items()):
    print(f"  {k[0]:9} / {k[1]:7}: {v}")
ref_ok = sum(1 for t in common if x64[t]["ok"])
print(f"IBM i passes {ref_ok - len(ibmi_only)} of the {ref_ok} tests that x64 passes: "
      f"{100 * (ref_ok - len(ibmi_only)) / ref_ok:.2f} %")
print(f"IBM i-specific discrepancies: {len(ibmi_only)}")


def signature(r):
    s = r["sortie"]
    m = (re.search(r"(Received signal \d+ \w+)", s) or re.search(r"(Check failed:[^\n]{0,80})", s)
         or re.search(r"(Failure[^\n]{0,90})", s) or re.search(r"(\w*Error: [^\n]{0,90})", s))
    return m.group(1) if m else s.strip()[-100:].replace("\n", " | ")


for r in ibmi_only:
    print(f"  {r['etat']:7} {r['test']:60} {signature(r)}")

"""Compare mjsunit on IBM i with a Linux x64 reference built with the same options.

A test is a port-specific discrepancy only if it passes on x64 and fails on IBM i (the
V8 status file does not cover our release, no-sandbox configuration, hence this
reference). Pass: exit code 0 (d8 handles --throws).
Usage: python3 comparer-mjsunit.py <ibmi.jsonl> <x64.jsonl>
"""
import collections
import json
import re
import sys


def lire(f):
    out = {}
    for l in open(f):
        if l.strip():
            r = json.loads(l)
            r["ok"] = r["code"] == 0
            out[r["test"]] = r
    return out


ibmi, x64 = lire(sys.argv[1]), lire(sys.argv[2])
communs = sorted(set(ibmi) & set(x64))
c = collections.Counter()
propres = []
for t in communs:
    a, b = ibmi[t]["ok"], x64[t]["ok"]
    c[("IBM i OK" if a else "IBM i KO", "x64 OK" if b else "x64 KO")] += 1
    if b and not a:
        propres.append(ibmi[t])
n = len(communs)
print(f"{n} tests communs")
for k, v in sorted(c.items()):
    print(f"  {k[0]:9} / {k[1]:7} : {v}")
ref_ok = sum(1 for t in communs if x64[t]["ok"])
print(f"IBM i réussit {ref_ok - len(propres)} des {ref_ok} tests que réussit x64 : "
      f"{100 * (ref_ok - len(propres)) / ref_ok:.2f} %")
print(f"écarts propres à IBM i : {len(propres)}")


def signature(r):
    s = r["sortie"]
    m = (re.search(r"(Received signal \d+ \w+)", s) or re.search(r"(Check failed:[^\n]{0,80})", s)
         or re.search(r"(Failure[^\n]{0,90})", s) or re.search(r"(\w*Error: [^\n]{0,90})", s))
    return m.group(1) if m else s.strip()[-100:].replace("\n", " | ")


for r in propres:
    print(f"  {r['etat']:7} {r['test']:60} {signature(r)}")

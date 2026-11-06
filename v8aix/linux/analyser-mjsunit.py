"""Check IBM i mjsunit results (mjsunit.py, JSON Lines) against the V8 status file.

Status variables: v8_build_config.json from our build (out/aix) + those that
tools/testrunner/base_runner.py adds, for IBM i: system=aix, byteorder=big,
mode=release, variant=default. Uses V8's own statusfile module.
Usage: python3 analyser-mjsunit.py <v8 root> <out/aix> <results.jsonl>
"""
import collections
import json
import pathlib
import sys

V8 = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
RES = pathlib.Path(sys.argv[3])
sys.path.insert(0, str(V8 / "tools"))
from testrunner.local import statusfile  # noqa: E402

variables = json.loads((OUT / "v8_build_config.json").read_text())
variables.update({
    "all_arm64_features": False, "byteorder": "big", "num_fuzzer": False,
    "deopt_fuzzer": False, "device_type": None, "endurance_fuzzer": False,
    "gc_fuzzer": False, "gc_stress": False, "isolates": False, "interrupt_fuzzer": False,
    "mode": "release", "no_harness": False, "no_simd_hardware": False, "novfp3": False,
    "optimize_for_size": False, "simulator_run": False, "system": "aix",
    "variant": "default",
})
regles, prefixes = statusfile.ReadStatusFile(
    (V8 / "test/mjsunit/mjsunit.status").read_text(), variables)


def attendus(test):
    """Expected outcomes: rules with no variant ("") and for the default variant, plus prefixes."""
    nom = test.rsplit(".", 1)[0]
    out = set()
    for v in ("", "default"):
        out |= set(regles[v].get(nom, ()))
        for p, r in prefixes[v].items():
            if nom.startswith(p):
                out |= set(r)
    return out


res = [json.loads(l) for l in RES.read_text().splitlines() if l.strip()]
bilan = collections.Counter()
inattendus = []
for r in res:
    att = attendus(r["test"])
    if statusfile.SKIP in att:
        bilan["sauté (statut V8)"] += 1
        continue
    if r["etat"] == "PASS":
        bilan["réussi"] += 1
    elif statusfile.FAIL in att or statusfile.FAIL_OK in att or "FAIL" in att:
        bilan["échec attendu (statut V8)"] += 1
    elif r["etat"] == "TIMEOUT" and (statusfile.SLOW in att or statusfile.TIMEOUT in att):
        bilan["lent attendu"] += 1
    else:
        bilan["ÉCHEC INATTENDU"] += 1
        inattendus.append(r)

total = sum(bilan.values())
executes = total - bilan["sauté (statut V8)"]
print(f"{len(res)} fichiers, {executes} tests exécutés")
for k, v in bilan.most_common():
    print(f"  {k:28} {v:6}")
ok = bilan["réussi"] + bilan["échec attendu (statut V8)"] + bilan["lent attendu"]
print(f"conformité (conforme au statut V8) : {100 * ok / executes:.2f} %")
print(f"taux de réussite brut : {100 * bilan['réussi'] / executes:.2f} %")
par_etat = collections.Counter(r["etat"] for r in inattendus)
print("échecs inattendus par nature :", dict(par_etat))
dossiers = collections.Counter(r["test"].split("/")[0] if "/" in r["test"] else "(racine)" for r in inattendus)
print("par dossier :", dossiers.most_common(15))
with open(RES.with_suffix(".inattendus.txt"), "w") as f:
    for r in sorted(inattendus, key=lambda r: r["test"]):
        f.write(f"{r['etat']:8} {r['test']}  code={r['code']}\n    {r['sortie'][-400:]!r}\n")
print("détail :", RES.with_suffix(".inattendus.txt"))

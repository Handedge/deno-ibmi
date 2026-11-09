"""Check IBM i mjsunit results (mjsunit.py, JSON Lines) against the V8 status file.

Status variables: v8_build_config.json from our build (out/aix) + those that
tools/testrunner/base_runner.py adds, for IBM i: system=aix, byteorder=big,
mode=release, variant=default. Uses V8's own statusfile module.
Usage: python3 analyze-mjsunit.py <v8 root> <out/aix> <results.jsonl>
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
rules, prefixes = statusfile.ReadStatusFile(
    (V8 / "test/mjsunit/mjsunit.status").read_text(), variables)


def expected_outcomes(test):
    """Expected outcomes: rules with no variant ("") and for the default variant, plus prefixes."""
    name = test.rsplit(".", 1)[0]
    out = set()
    for v in ("", "default"):
        out |= set(rules[v].get(name, ()))
        for p, r in prefixes[v].items():
            if name.startswith(p):
                out |= set(r)
    return out


res = [json.loads(l) for l in RES.read_text().splitlines() if l.strip()]
summary = collections.Counter()
unexpected = []
for r in res:
    exp = expected_outcomes(r["test"])
    if statusfile.SKIP in exp:
        summary["skipped (V8 status)"] += 1
        continue
    if r["etat"] == "PASS":
        summary["passed"] += 1
    elif statusfile.FAIL in exp or statusfile.FAIL_OK in exp or "FAIL" in exp:
        summary["expected failure (V8 status)"] += 1
    elif r["etat"] == "TIMEOUT" and (statusfile.SLOW in exp or statusfile.TIMEOUT in exp):
        summary["expected slow"] += 1
    else:
        summary["UNEXPECTED FAILURE"] += 1
        unexpected.append(r)

total = sum(summary.values())
executed = total - summary["skipped (V8 status)"]
print(f"{len(res)} files, {executed} tests run")
for k, v in summary.most_common():
    print(f"  {k:28} {v:6}")
ok = summary["passed"] + summary["expected failure (V8 status)"] + summary["expected slow"]
print(f"conformance (matches the V8 status): {100 * ok / executed:.2f} %")
print(f"raw pass rate: {100 * summary['passed'] / executed:.2f} %")
by_status = collections.Counter(r["etat"] for r in unexpected)
print("unexpected failures by kind:", dict(by_status))
directories = collections.Counter(r["test"].split("/")[0] if "/" in r["test"] else "(root)" for r in unexpected)
print("by directory:", directories.most_common(15))
with open(RES.with_suffix(".unexpected.txt"), "w") as f:
    for r in sorted(unexpected, key=lambda r: r["test"]):
        f.write(f"{r['etat']:8} {r['test']}  code={r['code']}\n    {r['sortie'][-400:]!r}\n")
print("details:", RES.with_suffix(".unexpected.txt"))

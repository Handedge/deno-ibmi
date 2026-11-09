# Bisection over the inputs of a crashing AIX link command (ld 0711-759):
# relinks subsets of objects/archives with -berok (missing symbols
# tolerated) to tell whether the crash comes from the size or from a specific input.
# Usage: python3.9 bisect_link.py <command file> <work directory> [binder]
import os
import shlex
import subprocess
import sys

command_file, work_dir = sys.argv[1], sys.argv[2]
binder = sys.argv[3] if len(sys.argv) > 3 else "/QOpenSys/opt/rust/outils/bin/bind"
tokens = shlex.split(open(command_file).read())
env = dict(os.environ)
while "=" in tokens[0] and not tokens[0].startswith("-"):
    k, v = tokens.pop(0).split("=", 1)
    env[k] = v
tokens.pop(0)  # "ld"

# inputs = .o/.rlib/.a files (except crt), everything else = options
inputs, options = [], []
i = 0
while i < len(tokens):
    j = tokens[i]
    if j == "-o":
        i += 2
        continue
    if not j.startswith("-") and (j.endswith(".o") or j.endswith(".rlib") or j.endswith(".a")) and "crt" not in j:
        inputs.append(j)
    else:
        options.append(j)
    i += 1
print(len(inputs), "inputs,", len(options), "options", flush=True)


def link(subset, label):
    cmd = ["/QOpenSys/usr/bin/ld", "-bbinder:" + binder, "-berok"] + options + subset + ["-o", os.path.join(work_dir, "dicho-" + label)]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
    crashed = "0711-759" in (r.stdout + r.stderr)
    print("%-12s %4d inputs -> rc=%d %s" % (label, len(subset), r.returncode, "CRASH" if crashed else "ok"), flush=True)
    return crashed


if not link(inputs, "tout"):
    print("the full link with -berok does not crash")
    sys.exit(0)
left, right = inputs[: len(inputs) // 2], inputs[len(inputs) // 2:]
left_crashes, right_crashes = link(left, "gauche"), link(right, "droite")
if not left_crashes and not right_crashes:
    print("CONCLUSION: each half links on its own -> size limit")
    sys.exit(0)
# one half crashes on its own: shrink it to isolate the faulty input
current = left if left_crashes else right
n = 0
while len(current) > 1:
    n += 1
    a, b = current[: len(current) // 2], current[len(current) // 2:]
    if link(a, "a%d" % n):
        current = a
    elif link(b, "b%d" % n):
        current = b
    else:
        print("CONCLUSION: crash caused by a combination of", len(current), "inputs:")
        for e in current:
            print("  ", e)
        sys.exit(0)
print("CONCLUSION: faulty input:", current[0])

# Bisection over the inputs of a crashing AIX link command (ld 0711-759):
# relinks subsets of objects/archives with -berok (missing symbols
# tolerated) to tell whether the crash comes from the size or from a specific input.
# Usage: python3.9 dichotomie_lien.py <command file> <work directory> [binder]
import os
import shlex
import subprocess
import sys

fichier, travail = sys.argv[1], sys.argv[2]
binder = sys.argv[3] if len(sys.argv) > 3 else "/QOpenSys/opt/rust/outils/bin/bind"
jetons = shlex.split(open(fichier).read())
env = dict(os.environ)
while "=" in jetons[0] and not jetons[0].startswith("-"):
    k, v = jetons.pop(0).split("=", 1)
    env[k] = v
jetons.pop(0)  # "ld"

# inputs = .o/.rlib/.a files (except crt), everything else = options
entrees, options = [], []
i = 0
while i < len(jetons):
    j = jetons[i]
    if j == "-o":
        i += 2
        continue
    if not j.startswith("-") and (j.endswith(".o") or j.endswith(".rlib") or j.endswith(".a")) and "crt" not in j:
        entrees.append(j)
    else:
        options.append(j)
    i += 1
print(len(entrees), "entrees,", len(options), "options", flush=True)


def lier(sous, nom):
    cmd = ["/QOpenSys/usr/bin/ld", "-bbinder:" + binder, "-berok"] + options + sous + ["-o", os.path.join(travail, "dicho-" + nom)]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
    plante = "0711-759" in (r.stdout + r.stderr)
    print("%-12s %4d entrees -> rc=%d %s" % (nom, len(sous), r.returncode, "PLANTE" if plante else "ok"), flush=True)
    return plante


if not lier(entrees, "tout"):
    print("le lien complet avec -berok ne plante pas")
    sys.exit(0)
gauche, droite = entrees[: len(entrees) // 2], entrees[len(entrees) // 2:]
pg, pd = lier(gauche, "gauche"), lier(droite, "droite")
if not pg and not pd:
    print("CONCLUSION : chaque moitie passe seule -> limite de taille")
    sys.exit(0)
# one half crashes on its own: shrink it to isolate the faulty input
courant = gauche if pg else droite
n = 0
while len(courant) > 1:
    n += 1
    a, b = courant[: len(courant) // 2], courant[len(courant) // 2:]
    if lier(a, "a%d" % n):
        courant = a
    elif lier(b, "b%d" % n):
        courant = b
    else:
        print("CONCLUSION : plantage par combinaison dans", len(courant), "entrees :")
        for e in courant:
            print("  ", e)
        sys.exit(0)
print("CONCLUSION : entree fautive :", courant[0])

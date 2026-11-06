# Adds the missing IBM i profiles (taken from deno/Cargo.toml.ibmi) to the Deno Cargo.toml
import re, sys
depot, cible = sys.argv[1], sys.argv[2]
ref = open(depot, encoding="utf-8").read()
c = open(cible, encoding="utf-8").read()
for nom, bloc in re.findall(r"(?ms)^(\[profile\.ibmi[^\]]*\])\n(.*?)(?=^\[|\Z)", ref):
    if nom not in c:
        c = c.replace("[patch.crates-io]", nom + "\n" + bloc + "[patch.crates-io]", 1)
        print("profil ajoute :", nom)
open(cible, "w", encoding="utf-8", newline="\n").write(c)

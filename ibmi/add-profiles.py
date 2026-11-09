# Adds the missing IBM i profiles (taken from deno/Cargo.toml.ibmi) to the Deno Cargo.toml
import re, sys
reference_toml, target = sys.argv[1], sys.argv[2]
ref = open(reference_toml, encoding="utf-8").read()
c = open(target, encoding="utf-8").read()
for name, block in re.findall(r"(?ms)^(\[profile\.ibmi[^\]]*\])\n(.*?)(?=^\[|\Z)", ref):
    if name not in c:
        c = c.replace("[patch.crates-io]", name + "\n" + block + "[patch.crates-io]", 1)
        print("profile added:", name)
open(target, "w", encoding="utf-8", newline="\n").write(c)

"""Installs the Deno snapshot generator for IBM i into a Deno tree.

Why: at build time, cli/snapshot/build.rs runs V8 to freeze the Deno JavaScript
(CLI_SNAPSHOT.bin, EXTENSION_RESIDUAL_SOURCES.rs, residual_sources/). When cross-compiling,
that build.rs would run on LINUXBUILD (x86, little-endian): the snapshot would be wrong for the
big-endian V8 of IBM i. It is therefore turned into a STANDALONE PROGRAM, cross-compiled like Deno,
linked and run on IBM i; its outputs are then used as DENO_SNAPSHOT_PREBUILT.

The generator is DERIVED from the original build.rs (not copied): for each Deno version, it
automatically picks up the snapshot logic of that version.

Usage: python3 installer.py <deno tree> <original build.rs of cli/snapshot>
Effects (idempotent): creates <tree>/cli/snapshot/generateur/{Cargo.toml,src/main.rs} and adds the
"cli/snapshot/generateur" member to the workspace in <tree>/Cargo.toml.
Build: cargo build ... -p generer-snapshot; run on IBM i:
    generer-snapshot <output directory>
"""
import pathlib
import sys

arbre = pathlib.Path(sys.argv[1])
origine = pathlib.Path(sys.argv[2]).read_text()
cible = arbre / "cli" / "snapshot" / "generateur"
(cible / "src").mkdir(parents=True, exist_ok=True)

# 1. main.rs: the original build.rs, with a main that takes the output directory as argument
ENTETE_MAIN = "fn main() {\n"
assert origine.count(ENTETE_MAIN) == 1, "build.rs : fn main() introuvable ou multiple"
MAIN = """fn main() {
  // deno-ibmi : générateur autonome. Le dossier de sortie remplace OUT_DIR, la cible est fixée :
  // le code ci-dessous est celui du build.rs d'origine de cli/snapshot.
  let sortie = std::env::args()
    .nth(1)
    .expect("usage : generer-snapshot <dossier de sortie>");
  std::fs::create_dir_all(&sortie).unwrap();
  let sortie = std::fs::canonicalize(&sortie).unwrap();
  // SAFETY: appelé au tout début, avant tout autre fil.
  unsafe {
    std::env::set_var("OUT_DIR", &sortie);
    std::env::set_var("TARGET", "powerpc64-ibm-aix");
  }
"""
source = origine.replace(ENTETE_MAIN, MAIN, 1)
# shared.rs (TS_VERSION) sits next to the original build.rs
MOD = '#[cfg(not(feature = "disable"))]\nmod shared;\n'
assert source.count(MOD) == 1, "build.rs : déclaration de mod shared introuvable"
source = source.replace(MOD, '#[path = "../../shared.rs"]\nmod shared;\n', 1)
source = "// @généré par construction/generer-snapshot/installer.py depuis cli/snapshot/build.rs\n" + source
(cible / "src" / "main.rs").write_text(source)

# 2. Cargo.toml: same engine options as the deno binary (V8, embedded ICU data)
(cible / "Cargo.toml").write_text("""# @généré par construction/generer-snapshot/installer.py
[package]
name = "generer-snapshot"
version = "0.0.0"
edition.workspace = true
publish = false
description = "deno-ibmi : fabrique le snapshot du CLI de Deno sur IBM i (V8 big-endian)"

[[bin]]
name = "generer-snapshot"
path = "src/main.rs"

[dependencies]
deno_runtime = { workspace = true, features = ["snapshot"] }
deno_core = { workspace = true, features = ["v8", "include_icu_data"] }
""")

# 3. workspace member
cargo = arbre / "Cargo.toml"
t = cargo.read_text()
if '"cli/snapshot/generateur"' not in t:
    ancre = '  "cli/snapshot",\n'
    assert ancre in t, "Cargo.toml : membre cli/snapshot introuvable"
    t = t.replace(ancre, ancre + '  "cli/snapshot/generateur",\n', 1)
    cargo.write_text(t)
print("générateur installé dans", cible)

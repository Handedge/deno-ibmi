"""Prepares the LINUXBUILD Deno tree for cross-compilation to IBM i. Idempotent.

1. deno_snapshots: no snapshot is produced at build time any more (that would require running
   a big-endian V8); the snapshot produced on IBM i (DENO_SNAPSHOT_PREBUILT) is copied instead.
2. v8 (crates.io): patched copy whose build.rs uses the AIX archive for the powerpc64-ibm-aix
   target and the official archive for the x86_64 host (build scripts).
Usage: python3 preparer-croise.py /QOpenSys/opt/denoibmi <cargo registry src>
"""
import pathlib
import re
import shutil
import sys

R = pathlib.Path(sys.argv[1])
REG = pathlib.Path(sys.argv[2])
DENO = R / "deno"

# --- 1. deno_snapshots -------------------------------------------------------------
s = DENO / "cli/snapshot"
c = (s / "Cargo.toml").read_text()
if "[build-dependencies]" in c:
    # the section runs up to the next section (a line starting with "["), or to the end
    garde, dedans = [], False
    for ligne in c.splitlines(keepends=True):
        if ligne.startswith("["):
            dedans = ligne.strip() == "[build-dependencies]"
        if not dedans:
            garde.append(ligne)
    c = "".join(garde)
    (s / "Cargo.toml").write_text(c)
    print("corrige : deno_snapshots/Cargo.toml (sans build-dependencies)")
CONSTRUCTION = '''// deno-ibmi (compilation croisée) : le snapshot est fabriqué par V8 sur IBM i
// (big-endian) ; on recopie ses sorties depuis DENO_SNAPSHOT_PREBUILT.
fn copier(de: &std::path::Path, vers: &std::path::Path) {
  std::fs::create_dir_all(vers).unwrap();
  for e in std::fs::read_dir(de).unwrap() {
    let e = e.unwrap();
    let cible = vers.join(e.file_name());
    if e.file_type().unwrap().is_dir() {
      copier(&e.path(), &cible);
    } else {
      std::fs::copy(e.path(), cible).unwrap();
    }
  }
}

fn main() {
  println!("cargo:rerun-if-env-changed=DENO_SNAPSHOT_PREBUILT");
  let de = std::env::var("DENO_SNAPSHOT_PREBUILT")
    .expect("DENO_SNAPSHOT_PREBUILT : dossier du snapshot fabriqué sur IBM i");
  let o = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
  copier(std::path::Path::new(&de), &o);
  // les sources résiduelles sont référencées par concat!(env!("OUT_DIR"), ...) : rien à recaler
}
'''
if "deno-ibmi (compilation croisée)" not in (s / "build.rs").read_text():
    (s / "build.rs").write_text(CONSTRUCTION)
    print("corrige : deno_snapshots/build.rs (snapshot d'IBM i)")

# --- 2. v8: archive chosen by target -------------------------------------------------
src = REG / "v8-150.4.0"
dst = R / "patches-croise/v8-150.4.0"
if not dst.exists():
    shutil.copytree(src, dst)
b = dst / "build.rs"
t = b.read_text()
MARQUE = "// deno-ibmi : archive selon la cible"
if MARQUE not in t:
    debut = t.index("fn main() {") + len("fn main() {")
    ajout = f'''
  {MARQUE}
  if env::var("TARGET").map(|c| c.contains("aix")).unwrap_or(false) {{
    for (aix, var) in [("RUSTY_V8_ARCHIVE_AIX", "RUSTY_V8_ARCHIVE"),
                       ("RUSTY_V8_SRC_BINDING_PATH_AIX", "RUSTY_V8_SRC_BINDING_PATH")] {{
      if let Ok(v) = env::var(aix) {{ unsafe {{ env::set_var(var, v) }}; }}
    }}
    unsafe {{ env::set_var("CXXSTDLIB", "") }};
  }}
  println!("cargo:rerun-if-env-changed=RUSTY_V8_ARCHIVE_AIX");
'''
    b.write_text(t[:debut] + ajout + t[debut:])
    print("corrige :", b)
# Flags passed by value to the C++ API (an enum on the V8 side): with #[repr(C)], a struct
# holding one u32 is left-aligned in the register on big-endian POWER, so V8 reads 0
# (PropertyFilter → ALL_PROPERTIES: console.log printed every key twice). Use repr(transparent).
for nom in ("property_filter.rs", "property_attribute.rs", "property_handler_flags.rs"):
    f = dst / "src" / nom
    t = f.read_text()
    if "#[repr(C)]" in t:
        f.write_text(t.replace("#[repr(C)]", "#[repr(transparent)]  // deno-ibmi : ABI big-endian", 1))
        print("corrige :", f)
# Dynamic import callbacks: V8 expects a MaybeLocal<Promise> returned by value. The AIX ABI
# returns every aggregate through a hidden pointer (like Windows x64), whereas the "unix"
# variant of rusty_v8 returns a raw pointer in a register: arguments shifted by one slot,
# so every import() crashed V8 ("null prototype chain root", PushStackTraceAndDie).
# On AIX the Windows variant is used (return pointer as first argument).
f = dst / "src" / "isolate.rs"
t = f.read_text()
if "deno-ibmi : MaybeLocal" not in t:
    UNIX = '#[cfg(target_family = "unix")]'
    WIN = '#[cfg(all(\n  target_family = "windows",\n  any(target_arch = "x86_64", target_arch = "aarch64")\n))]'
    WIN_IND = WIN.replace("\n", "\n    ").replace("#[cfg", "    #[cfg", 1)
    NOUV = ('#[cfg(any(target_os = "aix", all(target_family = "windows", '
            'any(target_arch = "x86_64", target_arch = "aarch64"))))]')
    assert t.count(UNIX) == 4 and t.count(WIN) == 2 and t.count(WIN_IND) == 2, "isolate.rs a changé"
    t = t.replace(UNIX, '#[cfg(all(target_family = "unix", not(target_os = "aix")))]')
    t = t.replace(WIN_IND, "    " + NOUV)
    t = t.replace(WIN, NOUV + "  // deno-ibmi : MaybeLocal par pointeur caché (ABI AIX)")
    f.write_text(t)
    print("corrige :", f)

# --- 3. libffi-sys: libffi.a built on IBM i ------------------------------------------
# libffi is configured with autotools and contains AIX assembly (aix.S): link the
# library produced by the native build on IBMI (LIBFFI_PREBUILT_DIR).
f = R / "patches/libffi-sys-4.1.0/build/build.rs"
t = f.read_text()
if "LIBFFI_PREBUILT_DIR" not in t:
    t = t.replace("fn main() {\n", '''fn main() {
    // deno-ibmi (compilation croisée) : libffi.a toute faite, construite sur IBM i
    println!("cargo:rerun-if-env-changed=LIBFFI_PREBUILT_DIR");
    if let Ok(d) = env::var("LIBFFI_PREBUILT_DIR") {
        println!("cargo:rustc-link-search=native={d}");
        println!("cargo:rustc-link-lib=static=ffi");
        return;
    }
''', 1)
    f.write_text(t)
    print("corrige :", f)

# --- 4. libz-sys: libz.a (zlib-ng compat) built on IBM i ------------------------------
# cmake-rs forces CMAKE_SYSTEM_NAME=aix (unknown to cmake) and a link check that cannot work
# here; for the AIX target only, link the libz.a from the native build.
f = R / "patches/libz-sys-1.1.20/build.rs"
t = f.read_text()
if "LIBZ_PREBUILT_DIR" not in t:
    t = t.replace("fn main() {\n", '''fn main() {
    // deno-ibmi (compilation croisée) : libz.a toute faite, construite sur IBM i
    println!("cargo:rerun-if-env-changed=LIBZ_PREBUILT_DIR");
    if env::var("TARGET").map(|c| c.contains("aix")).unwrap_or(false) {
        if let Ok(d) = env::var("LIBZ_PREBUILT_DIR") {
            println!("cargo:rustc-link-search=native={d}");
            println!("cargo:rustc-link-lib=static=z");
            println!("cargo:root={d}");
            return;
        }
    }
''', 1)
    f.write_text(t)
    print("corrige :", f)

# --- 5. nix: #![deny(unused)] -------------------------------------------------------
# Rust 1.99 sees dead code in the patched nix crates; since they are also built for the host
# (build scripts), they do not get the target --cap-lints: downgrade to warn.
for f in (R / "patches").glob("nix-*/src/lib.rs"):
    t = f.read_text()
    if "#![deny(unused)]" in t:
        f.write_text(t.replace("#![deny(unused)]", "#![warn(unused)]  // deno-ibmi : Rust 1.99"))
        print("corrige :", f)

# --- 6. compiler_builtins (rust-src of the stable toolchain, for -Z build-std) --------
# The math functions (rint…) use weak linkage there except on Windows/Cygwin: on AIX, the
# linker then picks the rint imported from libm, and the hidden compiler_builtins reference
# is rejected (0711-407 "Visibility is not allowed on a reference to an imported
# symbol"). No weak linkage on AIX: the static definition wins.
import subprocess
racine = subprocess.run([str(pathlib.Path.home() / ".cargo/bin/rustc"), "+stable", "--print", "sysroot"],
                        capture_output=True, text=True).stdout.strip()
m = pathlib.Path(racine) / "lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/macros.rs"
t = m.read_text()
ancien = 'not(any(all(windows, target_env = "gnu"), target_os = "cygwin")), linkage = "weak"'
nouveau = 'not(any(all(windows, target_env = "gnu"), target_os = "cygwin", target_os = "aix")), linkage = "weak"'
if ancien in t:
    m.write_text(t.replace(ancien, nouveau))
    print("corrige :", m, "(pas de liaison faible sur AIX)")

# --- [patch.crates-io] ---------------------------------------------------------------
ct = DENO / "Cargo.toml"
t = ct.read_text()
if "v8-croise = " not in t:
    t = t.replace("[patch.crates-io]\n",
                  f'[patch.crates-io]\nv8-croise = {{ package = "v8", path = "{dst}" }}\n', 1)
    ct.write_text(t)
    print("corrige : Cargo.toml ([patch] v8)")

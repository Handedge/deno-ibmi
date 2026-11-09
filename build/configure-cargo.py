"""Configures the Cargo.toml of a FRESH Deno tree for cross-compilation to IBM i (idempotent).

Replaces the successive manual or sed-based additions (build-deno.sh, add-profiles.py) that
had produced the Cargo.toml of the LINUXBUILD cross-compilation tree (captured on 2026-11-06).

Usage: python3 configure-cargo.py <deno tree> <Cargo.toml.ibmi from the repository (profiles)>
Does not handle: aws-lc-sys 0.40 → 0.46 (done by patches.py), the cli/snapshot/generateur member
(done by snapshot-generator/install.py).
"""
import re
import sys
import pathlib

tree = pathlib.Path(sys.argv[1])
reference = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
cargo = tree / "Cargo.toml"
c = cargo.read_text(encoding="utf-8")
P = "/QOpenSys/opt/denoibmi/patches"

# 1. deno_core: no V8-specific libc++ on the Rust side (librusty_v8.a for AIX already embeds it)
c = c.replace(
    'default-features = false, features = ["reactor-tokio", "v8_use_custom_libcxx"] }',
    'default-features = false, features = ["reactor-tokio"] }')

# 2. IBM i profiles (taken from deno/Cargo.toml.ibmi: ibmi, ibmi-lto, ibmi-o1, ibmi-os, ibmi-rel…)
profiles = re.findall(r"(?ms)^(\[profile\.ibmi[^\]]*\])\n(.*?)(?=^\[|\Z)", reference)
assert any(name == "[profile.ibmi-rel]" for name, _ in profiles), "ibmi-rel profile missing from the reference"
additions = ""
for name, block in profiles:
    if name not in c:
        additions += "\n" + name + "\n" + block.rstrip() + "\n"
if additions:
    c = c.rstrip() + "\n" + additions

# 3. patched crates: [patch.crates-io] (order and names from the production cross-compilation tree)
PATCHES = [
    ("inventory-patch", "inventory", "inventory-0.3.21"),
    ("mio-patch", "mio", "mio-1.2.4"),
    ("signal-hook-patch", "signal-hook", "signal-hook-0.3.18"),
    ("notify-patch", "notify", "notify-8.2.0"),
    ("v8-croise", "v8", "../patches-croise/v8-150.4.0"),
    ("deno_core_icudata-patch", "deno_core_icudata", "deno_core_icudata-0.77.0"),
    ("open-patch", "open", "open-5.1.2"),
    ("libsui-patch", "libsui", "libsui-0.16.4"),
    ("rustyline-patch", "rustyline", "rustyline-17.0.0"),
    ("memmap2-patch", "memmap2", "memmap2-0.9.5"),
    ("dlopen2-patch", "dlopen2", "dlopen2-0.6.1"),
    ("libuv-sys-lite-patch", "libuv-sys-lite", "libuv-sys-lite-1.48.4"),
    ("libffi-sys-patch", "libffi-sys", "libffi-sys-4.1.0"),
    ("quinn-udp-patch", "quinn-udp", "quinn-udp-0.5.9"),
    ("libnghttp2-patch", "libnghttp2", "libnghttp2-1.68.0"),
    ("rustix-038", "rustix", "rustix-0.38.34"),
    ("netif-patch", "netif", "netif-0.1.6"),
    ("libsqlite3-sys-patch", "libsqlite3-sys", "libsqlite3-sys-0.38.1"),
    ("libz-sys-patch", "libz-sys", "libz-sys-1.1.20"),
    ("nix-030", "nix", "nix-0.30.1"),
    ("nix-029", "nix", "nix-0.29.0"),
    ("aws-lc-sys-046", "aws-lc-sys", "aws-lc-sys-0.46.0"),
    ("aws-lc-sys-040", "aws-lc-sys", "aws-lc-sys-0.40.0"),
    ("v8x", None, "v8x-149.4.0-rc.4"),          # QuickJS facade (fallback engine)
    ("byteorder", None, "byteorder-1.5.0"),
]
if "[patch.crates-io]" not in c:
    c = c.rstrip() + "\n\n[patch.crates-io]\n"
for key, package, directory in PATCHES:
    if re.search(rf"^{re.escape(key)} = ", c, re.M):
        continue
    path = f"{P}/{directory}" if not directory.startswith("../") else str(pathlib.PurePosixPath(P).parent / directory[3:])
    pkg = f'package = "{package}", ' if package else ""
    c = c.rstrip() + f'\n{key} = {{ {pkg}path = "{path}" }}\n'

cargo.write_text(c, encoding="utf-8")
print("Cargo.toml configured:", len(profiles), "profiles,", len(PATCHES), "patched crates")

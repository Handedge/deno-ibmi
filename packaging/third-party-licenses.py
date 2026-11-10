"""Writes THIRD_PARTY_LICENSES.md for the deno RPM: native components shipped in the package, then
every Rust crate linked into the deno binary for powerpc64-ibm-aix (name, version, license).

Usage (in the Deno tree, on the build machine):
  cargo +1.99.1 tree -q -p deno --no-default-features --features v8,deno_core/include_icu_data \
      -e normal,build --target powerpc64-ibm-aix --prefix none --format "{p}|{l}" \
    | python3 third-party-licenses.py <deno version> > THIRD_PARTY_LICENSES.md
"""
import sys

NATIVE = [
    ("Deno", "https://github.com/denoland/deno", "MIT", "the runtime itself (Rust and JavaScript sources)"),
    ("V8 15.0.245.2", "https://v8.dev", "BSD-3-Clause", "JavaScript engine, through rusty_v8 150.4.0"),
    ("Chromium libc++ / libc++abi", "https://libcxx.llvm.org", "Apache-2.0 WITH LLVM-exception", "C++ library built with V8"),
    ("ICU data (big-endian)", "https://icu.unicode.org", "Unicode-3.0", "Intl data, embedded"),
    ("simdutf", "https://github.com/simdutf/simdutf", "Apache-2.0 OR MIT", "built with rusty_v8"),
    ("AWS-LC", "https://github.com/aws/aws-lc", "ISC AND (Apache-2.0 OR ISC)", "cryptography (crate aws-lc-sys)"),
    ("zlib-ng", "https://github.com/zlib-ng/zlib-ng", "Zlib", "compression (crate libz-sys)"),
    ("libffi", "https://github.com/libffi/libffi", "MIT", "FFI (crate libffi-sys)"),
    ("SQLite", "https://sqlite.org", "blessing (public domain)", "crate libsqlite3-sys"),
    ("nghttp2", "https://github.com/nghttp2/nghttp2", "MIT", "HTTP/2 (crate libnghttp2)"),
    ("libuv", "https://github.com/libuv/libuv", "MIT", "crate libuv-sys-lite"),
    ("libpaseat", "https://github.com/Handedge/deno-ibmi", "MIT", "/QOpenSys/pkgs/lib/deno/libpaseat.a, *at() functions for PASE (this project)"),
    ("IBM XL C/C++ for AIX 17.1.3 Runtime Environment: libunwind", "https://www.ibm.com/products/open-xl-cpp-aix-compiler-power",
     "IBM License Information (Redistributable)", "/QOpenSys/pkgs/lib/deno/libunwind.a, object code, unmodified, notices kept (see below)"),
]

# Terms of the IBM runtime redistributable (License Information of program 5765-J18 / 5725-C72, which
# lists libunwind.rte among the Redistributables).
IBM_NOTICE = [
    "## IBM runtime component",
    "",
    "`libunwind.a` comes, unmodified and in object-code form, from the IBM XL C/C++ for AIX 17.1.3",
    "Runtime Environment (programs 5765-J16, 5765-J18, 5725-C72), whose License Information lists",
    "`libunwind.rte` among its Redistributables. It is (C) Copyright IBM Corp. and others; its copyright",
    "notices are kept. It is redistributed only as part of this package, which uses it at run time, and",
    "only to support the use of this package.",
    "",
    "IBM, its suppliers and distributors provide this component without obligation of support and \"AS IS\",",
    "WITH NO WARRANTY OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING THE WARRANTY OF TITLE,",
    "NON-INFRINGEMENT OR NON-INTERFERENCE AND THE IMPLIED WARRANTIES AND CONDITIONS OF MERCHANTABILITY",
    "AND FITNESS FOR A PARTICULAR PURPOSE. IBM, its suppliers and distributors accept no liability for any",
    "use of this component as part of this package. This package is not affiliated with or endorsed by IBM.",
]


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "?"
    crates = []
    for line in sys.stdin:
        line = line.strip().replace(" (*)", "").replace(" (proc-macro)", "")
        if "|" not in line:
            continue
        pkg, lic = line.split("|", 1)
        parts = pkg.split()
        if len(parts) < 2 or parts[0] == "deno" and parts[1].lstrip("v") == version:
            continue
        crates.append((parts[0], parts[1].lstrip("v"), lic.strip() or "see the crate"))
    crates = sorted(set(crates))
    out = [f"# Third-party licenses of the deno {version} package for IBM i",
           "",
           "The deno-ibmi scripts, patches and libpaseat are under the MIT license (`LICENSE`). The deno binary",
           "and the libraries of this package contain the following third-party components, each under its own",
           "license. Their sources are available from the links below and from crates.io.",
           "",
           "## Native components",
           "",
           "| Component | Project | License | Notes |",
           "|---|---|---|---|"]
    out += [f"| {n} | {u} | {l} | {d} |" for n, u, l, d in NATIVE]
    out += [""] + IBM_NOTICE
    out += ["",
            f"## Rust crates linked into the deno binary ({len(crates)})",
            "",
            "| Crate | Version | License |",
            "|---|---|---|"]
    out += [f"| {n} | {v} | {l} |" for n, v, l in crates]
    print("\n".join(out))


if __name__ == "__main__":
    main()

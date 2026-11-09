"""Patches to the Deno test utilities (tests/util) needed to build test_server for AIX.

1. tests/util/lib/pty.rs: libc has no TIOCSCTTY for AIX (only used by the pty tests).
2. tests/util/server/servers/npm_registry.rs: esbuild does not exist for AIX; the test npm
   registry panicked ("unsupported platform") and took the whole test_server down.
Idempotent. Usage: python3 prepare-test-server.py <deno root>
"""
import pathlib
import sys

R = pathlib.Path(sys.argv[1])


def replace(f, a, b):
    """Replaces ALL occurrences of a (npm_registry.rs has two in 2.9.8: the second one had
    been fixed by hand in the 2026-11-02 tree, found by comparison on 2026-11-06)."""
    t = f.read_text()
    MARKER = "\0deja-corrige\0"
    masked = t.replace(b, MARKER)          # b may CONTAIN a (pty.rs): mask what is already patched
    if a not in masked:
        assert MARKER in masked, f"pattern not found in {f}"
        return
    n = masked.count(a)
    f.write_text(masked.replace(a, b).replace(MARKER, b))
    print(f"patched: {f} ({n} occurrence(s))")


replace(R / "tests/util/lib/pty.rs",
"""        if libc::ioctl(fds, libc::TIOCSCTTY as libc::c_ulong, 0) == -1 {
          return Err(std::io::Error::last_os_error());
        }""",
"""        // deno-ibmi : pas de TIOCSCTTY dans libc pour AIX (tests pty seulement)
        #[cfg(not(target_os = "aix"))]
        if libc::ioctl(fds, libc::TIOCSCTTY as libc::c_ulong, 0) == -1 {
          return Err(std::io::Error::last_os_error());
        }""")
replace(R / "tests/util/server/servers/npm_registry.rs",
"""  ensure_esbuild_prebuilt().await.unwrap();
""",
"""  // deno-ibmi : pas d esbuild pour AIX (sert au test bundle seulement)
  if let Err(e) = ensure_esbuild_prebuilt().await {
    eprintln!("esbuild indisponible : {e}");
  }
""")

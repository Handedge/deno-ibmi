# AIX/PASE patches applied to the crates copied into /QOpenSys/opt/denoibmi/patches
import sys, pathlib
REG = pathlib.Path(sys.argv[1])           # cargo registry (src/index.crates.io-...)
DST = pathlib.Path(sys.argv[2])           # patched crates directory
import shutil

def copy_crate(crate):
    src = REG / crate
    target = DST / crate
    if not target.exists():
        shutil.copytree(src, target)
    return target

import os
# PATCHES_REPORT=1: do not stop at the first missing pattern; list every patch that no longer
# applies (Deno version upgrade: phase 6 of the build project).
REPORT = os.environ.get("PATCHES_REPORT") == "1"
FAILURES = []


def replace(file, old, new):
    try:
        t = file.read_text()
    except FileNotFoundError:
        if REPORT:
            FAILURES.append((str(file), "file not found"))
            print("FAILED: file not found:", file)
            return
        raise
    if new in t:
        return
    if old not in t and REPORT:
        FAILURES.append((str(file), old.strip().splitlines()[0][:90]))
        print("FAILED: pattern not found:", file)
        return
    assert old in t, f"pattern not found in {file}"
    file.write_text(t.replace(old, new, 1))
    print("patched:", file)

# byteorder: on AIX, align_of::<f64>() == 4 < align_of::<u64>() == 8
b = copy_crate("byteorder-1.5.0") / "src" / "lib.rs"
replace(b,
"""        let dst = unsafe {
            const _: () = assert!(align_of::<u64>() <= align_of::<f64>());
            slice::from_raw_parts_mut(dst.as_mut_ptr() as *mut u64, dst.len())
        };
        Self::read_u64_into(src, dst);""",
"""        // AIX : f64 aligne sur 4 octets, pas de conversion de tranche
        assert_eq!(src.len(), 8 * dst.len());
        for (d, c) in dst.iter_mut().zip(src.chunks_exact(8)) {
            *d = Self::read_f64(c);
        }""")

# v8x / QuickJS-ng: AIX <sys/timer.h> defines "func_data" (t_union...),
# a variable name used heavily by quickjs.c
q = copy_crate("v8x-149.4.0-rc.4") / "vendor" / "quickjs-ng" / "quickjs.c"
replace(q,
'#include "quickjs-c-atomics.h"\n',
'#include "quickjs-c-atomics.h"\n\n#ifdef _AIX\n/* <sys/timer.h> : #define func_data t_union... */\n#undef func_data\n#endif\n')
# the #undef must come before quickjs.h (JS_NewCFunctionData prototype);
# AIX: struct tm has no tm_gmtoff -> use QuickJS's NO_TM_GMTOFF path
replace(q,
'#include "cutils.h"\n',
'#ifdef _AIX\n#undef func_data\n#ifndef NO_TM_GMTOFF\n#define NO_TM_GMTOFF\n#endif\n#endif\n#include "cutils.h"\n')
# cutils.h includes <pthread.h>, which brings the macro back: #undef in quickjs.h too
h = DST / "v8x-149.4.0-rc.4" / "vendor" / "quickjs-ng" / "quickjs.h"
replace(h,
'#include <math.h>\n',
'#include <math.h>\n#ifdef _AIX\n/* <sys/timer.h> : #define func_data t_union... */\n#undef func_data\n#endif\n')
# AIX: alloca is only declared by <alloca.h> under _ALL_SOURCE -> use the builtin explicitly
replace(q,
'#include "list.h"\n',
'#if defined(_AIX) && !defined(alloca)\n#define alloca __builtin_alloca\n#endif\n#include "list.h"\n')

# aws-lc-sys: on AIX, no linux-ppc64le assembly (ELF syntax); with
# AWS_LC_SYS_NO_ASM=1, aws-lc builds its portable C code (OPENSSL_NO_ASM)
for version in ("0.40.0", "0.46.0"):
    if not (REG / f"aws-lc-sys-{version}").exists():
        print("missing: aws-lc-sys", version)
        continue
    c = copy_crate(f"aws-lc-sys-{version}") / "builder" / "cc_builder.rs"
    replace(c,
'    } else if target_arch() == "powerpc64" {\n',
'    } else if target_arch() == "powerpc64" && target_os() != "aix" {\n')

# nix: AIX has a sun_len field in sockaddr_un but nix keeps its own as well
# (inconsistent cfgs) -> treat AIX like Linux; missing Pid import (pty)
def replace_all(file, old, new):
    t = file.read_text()
    if new in t or old not in t:
        return
    file.write_text(t.replace(old, new))
    print("patched:", file)

for version in ("0.29.0", "0.30.1"):
    if not (REG / f"nix-{version}").exists():
        continue
    src_dir = copy_crate(f"nix-{version}") / "src"
    replace_all(src_dir / "sys" / "socket" / "addr.rs",
        '                     target_os = "redox",\n                     target_os = "cygwin",\n                ))]',
        '                     target_os = "redox",\n                     target_os = "cygwin",\n                     target_os = "aix",\n                ))]')
    replace_all(src_dir / "pty.rs",
        '#[cfg(all(feature = "process", not(target_os = "aix")))]\nuse crate::unistd::Pid;',
        '#[cfg(feature = "process")]\nuse crate::unistd::Pid;')

# libz-sys / zlib-ng: gzread.c uses SIZE_MAX without <stdint.h> (AIX does not
# provide it otherwise)
g = copy_crate("libz-sys-1.1.20") / "src" / "zlib-ng" / "gzguts.h"
replace(g, '#include <limits.h>\n', '#include <limits.h>\n#include <stdint.h>\n')
replace(g, '#include <stdint.h>\n', '#include <stdint.h>\n#ifndef SIZE_MAX\n#define SIZE_MAX ((size_t)-1)\n#endif\n')

# ---- Deno's own sources ----
DENO = pathlib.Path(os.environ.get("DENO_TREE", "/QOpenSys/opt/denoibmi/deno"))  # other tree: analysis

# deno_core / uv_compat: errno address, which is _Errno() on AIX
# Formatting-independent (2026-11-06): the fallback condition `#[cfg(not(any(...)))]` is on one line
# in 2.9.8 and spans several in main (Android branch added); add AIX to it and insert the AIX
# variant just before.
import re
t = DENO / "libs" / "core" / "uv_compat" / "tty.rs"
if not t.exists():
    if REPORT:
        FAILURES.append((str(t), "file not found"))
        print("FAILED: file not found:", t)
    else:
        raise FileNotFoundError(t)
else:
    s = t.read_text()
    if "fn _Errno()" not in s:
        m = re.search(r"(  #\[cfg\(not\(any\()([^\]]*?)(\)\)\)\]\n  fn errno_location\(\) -> \*mut c_int \{)", s, re.S)
        if m:
            os_list = m.group(2).rstrip().rstrip(",")
            if "\n" in os_list:            # multi-line form (main)
                os_list = os_list + ',\n    target_os = "aix"\n  '
            else:                        # single-line form (2.9.8)
                os_list = os_list + ', target_os = "aix"'
            aix = ('  #[cfg(target_os = "aix")]\n'
                   '  fn errno_location() -> *mut c_int {\n'
                   '    unsafe extern "C" {\n'
                   '      fn _Errno() -> *mut c_int;\n'
                   '    }\n'
                   '    unsafe { _Errno() }\n'
                   '  }\n\n')
            s = s[:m.start()] + aix + m.group(1) + os_list + m.group(3) + s[m.end():]
            t.write_text(s)
            print("patched:", t)
        elif REPORT:
            FAILURES.append((str(t), "errno_location fallback condition not found"))
            print("FAILED:", t)
        else:
            raise AssertionError(f"errno_location not found in {t}")

# libsqlite3-sys: the session feature requires bindgen (no libclang on IBM i).
# Bindings generated once on LINUXBUILD for powerpc64-ibm-aix, copied here
# when LIBSQLITE3_SYS_BINDINGS_FILE is set.
b = copy_crate("libsqlite3-sys-0.38.1") / "build.rs"
replace(b,
'''    pub fn write_to_out_dir(header: HeaderLocation, out_path: &Path) {
        let header: String = header.into();''',
'''    pub fn write_to_out_dir(header: HeaderLocation, out_path: &Path) {
        if let Ok(f) = std::env::var("LIBSQLITE3_SYS_BINDINGS_FILE") {
            std::fs::copy(&f, out_path).expect("copie des liaisons pregenerees");
            return;
        }
        let header: String = header.into();''')

# Deno: a single aws-lc-sys version (0.46, the one used by aws-lc-rs); 0.40
# requires bindgen for a target without pregenerated bindings
replace(DENO / "Cargo.toml",
'aws-lc-sys = { version = "0.40.0", features = ["prebuilt-nasm"] }',
'aws-lc-sys = { version = "0.46.0", features = ["prebuilt-nasm"] }')

# aws-lc-sys 0.46: "all-bindings" bindings generated on LINUXBUILD (bindgen,
# PASE headers, powerpc64-ibm-aix target), copied if AWS_LC_SYS_BINDINGS_FILE is set
m = DST / "aws-lc-sys-0.46.0" / "builder" / "main.rs"
replace(m,
'''            let result = invoke_external_bindgen(&manifest_dir, &prefix, &gen_bindings_path);''',
'''            let result = match env::var("AWS_LC_SYS_BINDINGS_FILE") {
                Ok(f) => std::fs::copy(&f, &gen_bindings_path)
                    .map(|_| ())
                    .map_err(|e| e.to_string()),
                Err(_) => invoke_external_bindgen(&manifest_dir, &prefix, &gen_bindings_path),
            };''')

# netif: getifaddrs/ifaddrs missing from the libc crate for AIX (and from PASE) -> on AIX,
# enumerate with ioctl(SIOCGIFCONF); before 2026-11-05: empty list (migrated below)
n = copy_crate("netif-0.1.6") / "src" / "lib.rs"
replace_all(n, '/// AIX / IBM i PASE : getifaddrs n\'est pas expose par la crate libc ; liste vide.\n#[cfg(target_os = "aix")]\nmod aix {\n    use super::Interface;\n    use std::io;\n\n    pub fn up() -> io::Result<Up> {\n        Ok(Up)\n    }\n\n    pub struct Up;\n\n    impl Iterator for Up {\n        type Item = Interface;\n\n        fn next(&mut self) -> Option<Self::Item> {\n            None\n        }\n    }\n}', '/// AIX / IBM i PASE : pas de getifaddrs ; énumération par ioctl(SIOCGIFCONF) (05/11/2026).\n/// Relevé en C sur IBM i 7.5 (essais/signaux/ifconf.c) : ifreq de longueur variable (16 octets\n/// de nom + sockaddr de sa_len octets, 16 au moins) ; les noms sont les adresses IP (style\n/// IBM i) ; aucune entrée AF_LINK, donc pas d\'adresse MAC (00:00:00:00:00:00) ; masque IPv4 par\n/// SIOCGIFNETMASK ; SIOCGIFNETMASK6 échoue sous PASE : /128 pour ::1, /64 sinon.\n#[cfg(target_os = "aix")]\nmod aix {\n    use super::Interface;\n    use std::io;\n    use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};\n\n    const SIOCGIFCONF: libc::c_int = 0xc010_6945_u32 as libc::c_int;\n    const SIOCGIFNETMASK: libc::c_int = 0xc028_6925_u32 as libc::c_int;\n    const SIOCGIFFLAGS: libc::c_int = 0xc028_6911_u32 as libc::c_int;\n    const AF_INET6_AIX: i32 = 24;\n\n    #[repr(C)]\n    struct IfConf {\n        len: libc::c_int,\n        buf: *mut libc::c_char,\n    }\n\n    pub fn up() -> io::Result<Up> {\n        // SAFETY: appels système sur une socket locale et des tampons dimensionnés ici.\n        unsafe {\n            let s = libc::socket(libc::AF_INET, libc::SOCK_DGRAM, 0);\n            if s < 0 {\n                return Err(io::Error::last_os_error());\n            }\n            let mut buf = vec![0u8; 16384];\n            let mut ifc = IfConf { len: buf.len() as libc::c_int, buf: buf.as_mut_ptr() as *mut _ };\n            if libc::ioctl(s, SIOCGIFCONF, &mut ifc as *mut IfConf) < 0 {\n                let e = io::Error::last_os_error();\n                libc::close(s);\n                return Err(e);\n            }\n            let fin = (ifc.len.max(0) as usize).min(buf.len());\n            let mut liste = Vec::new();\n            let mut p = 0;\n            while p + 18 <= fin {\n                let nom_b = &buf[p..p + 16];\n                let n = nom_b.iter().position(|&c| c == 0).unwrap_or(16);\n                let nom = String::from_utf8_lossy(&nom_b[..n]).into_owned();\n                let lg = 16 + (buf[p + 16] as usize).max(16);\n                if p + lg > fin {\n                    break;\n                }\n                let sa = &buf[p + 16..p + lg];\n                let mut q = [0u8; 64];\n                q[..16].copy_from_slice(nom_b);\n                let flags = if libc::ioctl(s, SIOCGIFFLAGS, q.as_mut_ptr()) == 0 {\n                    u32::from_be_bytes([q[16], q[17], q[18], q[19]]) as u64\n                } else {\n                    0\n                };\n                let fam = sa[1] as i32;\n                if fam == libc::AF_INET && sa.len() >= 8 {\n                    let adresse = Ipv4Addr::new(sa[4], sa[5], sa[6], sa[7]);\n                    let mut m = [0u8; 64];\n                    m[..16].copy_from_slice(nom_b);\n                    let masque = if libc::ioctl(s, SIOCGIFNETMASK, m.as_mut_ptr()) == 0 {\n                        Ipv4Addr::new(m[20], m[21], m[22], m[23])\n                    } else {\n                        Ipv4Addr::BROADCAST\n                    };\n                    liste.push(Interface {\n                        name: nom,\n                        flags,\n                        mac: [0; 6],\n                        address: IpAddr::V4(adresse),\n                        scope_id: None,\n                        netmask: IpAddr::V4(masque),\n                    });\n                } else if fam == AF_INET6_AIX && sa.len() >= 28 {\n                    let mut o = [0u8; 16];\n                    o.copy_from_slice(&sa[8..24]);\n                    let adresse = Ipv6Addr::from(o);\n                    let portee = u32::from_be_bytes([sa[24], sa[25], sa[26], sa[27]]);\n                    let prefixe: u32 = if adresse.is_loopback() { 128 } else { 64 };\n                    liste.push(Interface {\n                        name: nom,\n                        flags,\n                        mac: [0; 6],\n                        address: IpAddr::V6(adresse),\n                        scope_id: Some(portee),\n                        netmask: IpAddr::V6(Ipv6Addr::from(u128::MAX << (128 - prefixe))),\n                    });\n                }\n                p += lg;\n            }\n            libc::close(s);\n            Ok(Up(liste.into_iter()))\n        }\n    }\n\n    pub struct Up(std::vec::IntoIter<Interface>);\n\n    impl Iterator for Up {\n        type Item = Interface;\n\n        fn next(&mut self) -> Option<Self::Item> {\n            self.0.next()\n        }\n    }\n}')
replace(n,
'''#[cfg(not(target_os = "windows"))]
pub use unix::*;''',
'''#[cfg(not(any(target_os = "windows", target_os = "aix")))]
pub use unix::*;

#[cfg(target_os = "aix")]
pub use aix::*;

/// AIX / IBM i PASE : pas de getifaddrs ; énumération par ioctl(SIOCGIFCONF) (05/11/2026).
/// Relevé en C sur IBM i 7.5 (essais/signaux/ifconf.c) : ifreq de longueur variable (16 octets
/// de nom + sockaddr de sa_len octets, 16 au moins) ; les noms sont les adresses IP (style
/// IBM i) ; aucune entrée AF_LINK, donc pas d'adresse MAC (00:00:00:00:00:00) ; masque IPv4 par
/// SIOCGIFNETMASK ; SIOCGIFNETMASK6 échoue sous PASE : /128 pour ::1, /64 sinon.
#[cfg(target_os = "aix")]
mod aix {
    use super::Interface;
    use std::io;
    use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};

    const SIOCGIFCONF: libc::c_int = 0xc010_6945_u32 as libc::c_int;
    const SIOCGIFNETMASK: libc::c_int = 0xc028_6925_u32 as libc::c_int;
    const SIOCGIFFLAGS: libc::c_int = 0xc028_6911_u32 as libc::c_int;
    const AF_INET6_AIX: i32 = 24;

    #[repr(C)]
    struct IfConf {
        len: libc::c_int,
        buf: *mut libc::c_char,
    }

    pub fn up() -> io::Result<Up> {
        // SAFETY: appels système sur une socket locale et des tampons dimensionnés ici.
        unsafe {
            let s = libc::socket(libc::AF_INET, libc::SOCK_DGRAM, 0);
            if s < 0 {
                return Err(io::Error::last_os_error());
            }
            let mut buf = vec![0u8; 16384];
            let mut ifc = IfConf { len: buf.len() as libc::c_int, buf: buf.as_mut_ptr() as *mut _ };
            if libc::ioctl(s, SIOCGIFCONF, &mut ifc as *mut IfConf) < 0 {
                let e = io::Error::last_os_error();
                libc::close(s);
                return Err(e);
            }
            let fin = (ifc.len.max(0) as usize).min(buf.len());
            let mut liste = Vec::new();
            let mut p = 0;
            while p + 18 <= fin {
                let nom_b = &buf[p..p + 16];
                let n = nom_b.iter().position(|&c| c == 0).unwrap_or(16);
                let nom = String::from_utf8_lossy(&nom_b[..n]).into_owned();
                let lg = 16 + (buf[p + 16] as usize).max(16);
                if p + lg > fin {
                    break;
                }
                let sa = &buf[p + 16..p + lg];
                let mut q = [0u8; 64];
                q[..16].copy_from_slice(nom_b);
                let flags = if libc::ioctl(s, SIOCGIFFLAGS, q.as_mut_ptr()) == 0 {
                    u32::from_be_bytes([q[16], q[17], q[18], q[19]]) as u64
                } else {
                    0
                };
                let fam = sa[1] as i32;
                if fam == libc::AF_INET && sa.len() >= 8 {
                    let adresse = Ipv4Addr::new(sa[4], sa[5], sa[6], sa[7]);
                    let mut m = [0u8; 64];
                    m[..16].copy_from_slice(nom_b);
                    let masque = if libc::ioctl(s, SIOCGIFNETMASK, m.as_mut_ptr()) == 0 {
                        Ipv4Addr::new(m[20], m[21], m[22], m[23])
                    } else {
                        Ipv4Addr::BROADCAST
                    };
                    liste.push(Interface {
                        name: nom,
                        flags,
                        mac: [0; 6],
                        address: IpAddr::V4(adresse),
                        scope_id: None,
                        netmask: IpAddr::V4(masque),
                    });
                } else if fam == AF_INET6_AIX && sa.len() >= 28 {
                    let mut o = [0u8; 16];
                    o.copy_from_slice(&sa[8..24]);
                    let adresse = Ipv6Addr::from(o);
                    let portee = u32::from_be_bytes([sa[24], sa[25], sa[26], sa[27]]);
                    let prefixe: u32 = if adresse.is_loopback() { 128 } else { 64 };
                    liste.push(Interface {
                        name: nom,
                        flags,
                        mac: [0; 6],
                        address: IpAddr::V6(adresse),
                        scope_id: Some(portee),
                        netmask: IpAddr::V6(Ipv6Addr::from(u128::MAX << (128 - prefixe))),
                    });
                }
                p += lg;
            }
            libc::close(s);
            Ok(Up(liste.into_iter()))
        }
    }

    pub struct Up(std::vec::IntoIter<Interface>);

    impl Iterator for Up {
        type Item = Interface;

        fn next(&mut self) -> Option<Self::Item> {
            self.0.next()
        }
    }
}''')
replace(n, '#[cfg(not(target_os = "windows"))]\nmod unix {',
          '#[cfg(not(any(target_os = "windows", target_os = "aix")))]\nmod unix {')
replace(n, '#[cfg(all(unix, not(any(target_os = "android", target_os = "linux"))))]\nmod bsd {',
          '#[cfg(all(unix, not(any(target_os = "android", target_os = "linux", target_os = "aix"))))]\nmod bsd {')

# rustix 0.38: on AIX, libc::cfmakeraw returns c_int (the function is declared -> ())
r = copy_crate("rustix-0.38.34") / "src" / "backend" / "libc" / "termios" / "syscalls.rs"
replace(r, '    unsafe { c::cfmakeraw(as_mut_ptr(termios).cast()) }\n',
             '    unsafe {\n        c::cfmakeraw(as_mut_ptr(termios).cast());\n    }\n')

# libnghttp2: bindings generated on LINUXBUILD (bindgen cannot run on IBM i)
g2 = copy_crate("libnghttp2-1.68.0") / "build.rs"
replace(g2,
'''fn generate_bindings(out_dir: &Path, include_dir: &Path) {
''',
'''fn generate_bindings(out_dir: &Path, include_dir: &Path) {
  if let Ok(f) = env::var("NGHTTP2_BINDINGS_FILE") {
    std::fs::copy(&f, out_dir.join("bindings.rs")).expect("copie des liaisons pregenerees");
    return;
  }
''')

# deno_io: no SOCK_CLOEXEC on AIX -> same handling as macOS
p = DENO / "ext" / "io" / "bi_pipe.rs"
replace(p, '    #[cfg(not(target_os = "macos"))]\n    let flags = libc::SOCK_CLOEXEC;',
             '    #[cfg(not(any(target_os = "macos", target_os = "aix")))]\n    let flags = libc::SOCK_CLOEXEC;')
replace(p, '    #[cfg(target_os = "macos")]\n    let flags = 0;',
             '    #[cfg(any(target_os = "macos", target_os = "aix"))]\n    let flags = 0;')
replace(p, '    if cfg!(target_os = "macos") {\n      let fcntl',
             '    if cfg!(any(target_os = "macos", target_os = "aix")) {\n      let fcntl')

# quinn-udp: socket options missing from libc for AIX -> fallback implementation
# (fallback.rs, no ECN), as for unsupported platforms
qu = copy_crate("quinn-udp-0.5.9") / "src" / "lib.rs"
replace(qu, '#[cfg(any(unix, windows))]\nmod cmsg;',
              '#[cfg(any(all(unix, not(target_os = "aix")), windows))]\nmod cmsg;')
replace(qu, '#[cfg(unix)]\n#[path = "unix.rs"]\nmod imp;',
              '#[cfg(all(unix, not(target_os = "aix")))]\n#[path = "unix.rs"]\nmod imp;')
replace(qu, '#[cfg(not(any(unix, windows)))]\n#[path = "fallback.rs"]\nmod imp;',
              '#[cfg(any(target_os = "aix", not(any(unix, windows))))]\n#[path = "fallback.rs"]\nmod imp;')
fb = DST / "quinn-udp-0.5.9" / "src" / "fallback.rs"
replace(fb,
'''        &socket2::SockAddr::from(transmit.destination),
    )
''',
'''        &socket2::SockAddr::from(transmit.destination),
    )
    .map(|_| ())
''')

# libffi-sys: config.guess answers powerpc-ibm-os400 (unknown to libffi) ->
# force the AIX triple
lf = copy_crate("libffi-sys-4.1.0") / "build" / "not_msvc.rs"
replace(lf,
'''        .arg("--disable-docs");
''',
'''        .arg("--disable-docs");
    // IBM i PASE : config.guess repond powerpc-ibm-os400, inconnu de libffi
    if cfg!(target_os = "aix") {
        command
            .arg("--build=powerpc-ibm-aix7.2.0.0")
            .arg("--host=powerpc-ibm-aix7.2.0.0");
    }
''')

# deno_fs: umask has no AIX branch
u = DENO / "ext" / "fs" / "std_fs.rs"
replace(u,
'''    #[cfg(any(
      target_os = "macos",
      target_os = "openbsd",
      target_os = "freebsd"
    ))]
    {
      Ok(r.bits() as u32)
    }''',
'''    #[cfg(any(
      target_os = "macos",
      target_os = "openbsd",
      target_os = "freebsd",
      target_os = "aix"
    ))]
    {
      Ok(r.bits() as u32)
    }''')

# libuv-sys-lite: no bindings for AIX -> bindgen; bindings generated
# on LINUXBUILD, copied if LIBUV_SYS_LITE_BINDINGS_FILE is set
lu = copy_crate("libuv-sys-lite-1.48.4") / "build.rs"
replace(lu,
'''fn main() {
''',
'''fn main() {
  if let Ok(f) = std::env::var("LIBUV_SYS_LITE_BINDINGS_FILE") {
    let dest = PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("bindings.rs");
    std::fs::copy(&f, &dest).expect("copie des liaisons pregenerees");
    return;
  }
''')

# libffi-sys: 64-bit AIX ABI constants (libffi src/powerpc/ffitarget.h,
# POWERPC_AIX + __64BIT__); the powerpc64 module assumes ELFv1/ELFv2
a = DST / "libffi-sys-4.1.0" / "src" / "arch.rs"
replace(a,
'''        #[cfg(any(
            all(target_arch = "powerpc64", target_abi = "elfv1"),
            not(target_arch = "powerpc64")
        ))]
        mod elf {''',
'''        #[cfg(any(
            all(target_arch = "powerpc64", target_abi = "elfv1"),
            not(target_arch = "powerpc64"),
            target_os = "aix"
        ))]
        mod elf {''')
replace(a,
'''#[cfg(target_arch = "powerpc64")]
pub use powerpc::powerpc64::*;''',
'''#[cfg(all(target_arch = "powerpc64", not(target_os = "aix")))]
pub use powerpc::powerpc64::*;

#[cfg(all(target_arch = "powerpc64", target_os = "aix"))]
pub use powerpc_aix::*;

/// AIX / IBM i PASE 64 bits : libffi src/powerpc/ffitarget.h (POWERPC_AIX)
#[cfg(all(target_arch = "powerpc64", target_os = "aix"))]
mod powerpc_aix {
    use crate::ffi_abi;

    pub const ffi_abi_FFI_FIRST_ABI: ffi_abi = 0;
    pub const ffi_abi_FFI_AIX: ffi_abi = 1;
    pub const ffi_abi_FFI_DARWIN: ffi_abi = 2;
    pub const ffi_abi_FFI_LAST_ABI: ffi_abi = 3;
    pub const ffi_abi_FFI_DEFAULT_ABI: ffi_abi = ffi_abi_FFI_AIX;

    pub const FFI_TRAMPOLINE_SIZE: usize = 24;
    pub const FFI_NATIVE_RAW_API: u32 = 0;
    pub const FFI_GO_CLOSURES: u32 = 1;
}''')

# deno_napi: export list in AIX format (-bE:, one symbol per line),
# derived from the Linux list
import re as _re
napi = DENO / "ext" / "napi"
aix_exports = napi / "generated_symbol_exports_list_aix.def"
if not aix_exports.exists():
    names = _re.findall(r'"([^"]+)"', (napi / "generated_symbol_exports_list_linux.def").read_text())
    aix_exports.write_text("\n".join(names) + "\n")
    print("created:", aix_exports, len(names), "symbols")
replace(napi / "lib.rs",
'''  #[cfg(target_os = "android")]
  println!(
    "cargo:rustc-link-arg-bin={name}=-Wl,--export-dynamic-symbol-list={}",
    symbols_path,
  );''',
'''  #[cfg(target_os = "android")]
  println!(
    "cargo:rustc-link-arg-bin={name}=-Wl,--export-dynamic-symbol-list={}",
    symbols_path,
  );

  // AIX / IBM i PASE : ld direct, liste d'exports -bE:
  #[cfg(target_os = "aix")]
  println!("cargo:rustc-link-arg-bin={name}=-bE:{}", symbols_path);''')

# dlopen2: no dladdr/Dl_info on AIX -> addr_info_obtain returns
# "address not in a library", a case the crate already handles
dl = copy_crate("dlopen2-0.6.1") / "src" / "raw" / "unix.rs"
replace(dl,
'use libc::{dladdr, dlclose, dlerror, dlopen, dlsym, Dl_info, RTLD_LAZY, RTLD_LOCAL};',
'use libc::{dlclose, dlerror, dlopen, dlsym, RTLD_LAZY, RTLD_LOCAL};\n#[cfg(not(target_os = "aix"))]\nuse libc::{dladdr, Dl_info};')
replace(dl,
'''pub fn addr_info_obtain(addr: *const ()) -> Result<AddressInfo, Error> {
    // let mut dlinfo''',
'''#[cfg(target_os = "aix")]
pub fn addr_info_obtain(_addr: *const ()) -> Result<AddressInfo, Error> {
    Err(Error::AddrNotMatchingDll(IoError::new(
        ErrorKind::NotFound,
        String::from("dladdr indisponible sur AIX"),
    )))
}

#[cfg(not(target_os = "aix"))]
pub fn addr_info_obtain(addr: *const ()) -> Result<AddressInfo, Error> {
    // let mut dlinfo''')

# memmap2: AIX madvise takes a caddr_t (*mut u8)
mm = copy_crate("memmap2-0.9.5") / "src" / "unix.rs"
replace(mm, 'if libc::madvise(self.ptr.offset(offset), len, advice) != 0 {',
              'if libc::madvise(self.ptr.offset(offset).cast(), len, advice) != 0 {')

# deno_signals: AIX signal table (PASE sys/signal.h)
sg = DENO / "ext" / "signals" / "dict.rs"
replace(sg, '#[cfg(target_os = "windows")]\nsignal_dict!(',
'''#[cfg(target_os = "aix")]
signal_dict!(
  (1, "SIGHUP"),
  (2, "SIGINT"),
  (3, "SIGQUIT"),
  (4, "SIGILL"),
  (5, "SIGTRAP"),
  (6, "SIGABRT" | "SIGIOT"),
  (7, "SIGEMT"),
  (8, "SIGFPE"),
  (9, "SIGKILL"),
  (10, "SIGBUS"),
  (11, "SIGSEGV"),
  (12, "SIGSYS"),
  (13, "SIGPIPE"),
  (14, "SIGALRM"),
  (15, "SIGTERM"),
  (16, "SIGURG"),
  (17, "SIGSTOP"),
  (18, "SIGTSTP"),
  (19, "SIGCONT"),
  (20, "SIGCHLD"),
  (21, "SIGTTIN"),
  (22, "SIGTTOU"),
  (23, "SIGIO" | "SIGPOLL"),
  (24, "SIGXCPU"),
  (25, "SIGXFSZ"),
  (27, "SIGMSG"),
  (28, "SIGWINCH"),
  (29, "SIGPWR"),
  (30, "SIGUSR1"),
  (31, "SIGUSR2"),
  (32, "SIGPROF"),
  (33, "SIGDANGER"),
  (34, "SIGVTALRM")
);

#[cfg(target_os = "windows")]
signal_dict!(''')

# deno_os: loadavg, os_release, uptime, rss for AIX
si = DENO / "ext" / "os" / "sys_info.rs"
replace(si,
'''  #[cfg(target_os = "windows")]
  {
    DEFAULT_LOADAVG
  }''',
'''  #[cfg(any(target_os = "windows", target_os = "aix"))]
  {
    DEFAULT_LOADAVG
  }''')
replace(si,
'''  #[cfg(target_os = "android")]
  {
    let mut info = std::mem::MaybeUninit::uninit();
    // SAFETY: `info` is a valid pointer to a `libc::utsname` struct.''',
'''  #[cfg(any(target_os = "android", target_os = "aix"))]
  {
    let mut info = std::mem::MaybeUninit::uninit();
    // SAFETY: `info` is a valid pointer to a `libc::utsname` struct.''')
# uptime and rss under PASE (2026-11-04): sysinfo, KERN_BOOTTIME and getrusage (ru_maxrss = 0
# under PASE) either do not exist or return nothing. getprocs64 works: start time of the
# partition's first process (pid 10: there is no process 1 under PASE; started at
# IPL, verified: 30.2 h, same as times()) and pi_dvm, data memory
# in 4 KB pages (verified: +200 MB allocated = +51,200 pages). times() is ruled out:
# clock_t is 32-bit on AIX and wraps around after 248 days.
# Offsets measured in C on IBM i 7.5 (examples/signals/os_pase.c): sizeof(procentry64) = 5024,
# pi_start at byte 1520, pi_dvm at byte 1704 (both 8 bytes wide).
AIX_UPTIME = '''  // AIX / IBM i PASE : pas de sysinfo ni de KERN_BOOTTIME ; démarrage du processus 1
  // (init, donc l'IPL de la partition) lu par getprocs64
  #[cfg(target_os = "aix")]
  {
    let maintenant = std::time::SystemTime::now()
      .duration_since(std::time::UNIX_EPOCH)
      .map(|d| d.as_secs())
      .unwrap_or(0);
    // pas de processus 1 sous PASE : le premier processus de la partition (pid 10 sur
    // IBM i 7.5) démarre à l'IPL
    uptime = aix_procentry64(0)
      .map(|(_, p)| maintenant.saturating_sub(p[AIX_PI_START]))
      .unwrap_or(0);
  }
'''
AIX_PROCENTRY = '''/// deno-ibmi : struct procentry64 d'AIX lue en mots de 64 bits (5024 octets, IBM i 7.5) ;
/// la crate libc ne déclare ni la structure ni getprocs64.
#[cfg(target_os = "aix")]
pub const AIX_PI_START: usize = 1520 / 8;
#[cfg(target_os = "aix")]
pub const AIX_PI_DVM: usize = 1704 / 8;
#[cfg(target_os = "aix")]
/// Rend (pid trouvé, entrée) : getprocs64 donne le premier processus de pid >= `pid`.
pub fn aix_procentry64(pid: libc::pid_t) -> Option<(libc::pid_t, Box<[u64; 628]>)> {
  unsafe extern "C" {
    fn getprocs64(
      procsinfo: *mut libc::c_void,
      sizproc: libc::c_int,
      fdsinfo: *mut libc::c_void,
      sizfd: libc::c_int,
      index: *mut libc::pid_t,
      count: libc::c_int,
    ) -> libc::c_int;
  }
  let mut p = Box::new([0u64; 628]);
  let mut index = pid;
  // SAFETY: tampon de 5024 octets = sizeof(struct procentry64), un seul processus demandé.
  let n = unsafe {
    getprocs64(p.as_mut_ptr() as *mut _, 5024, std::ptr::null_mut(), 0, &mut index, 1)
  };
  // pi_pid : 4 premiers octets (big-endian), donc moitié haute du premier mot
  (n == 1).then(|| ((p[0] >> 32) as libc::pid_t, p))
}

pub fn os_uptime() -> u64 {'''
replace_all(si,
'''  // AIX / IBM i PASE : pas de sysinfo ni de KERN_BOOTTIME
  #[cfg(target_os = "aix")]
  {
    uptime = 0;
  }
''', AIX_UPTIME)
replace(si,
'''  #[cfg(target_family = "windows")]
  // SAFETY: windows API usage
  unsafe {
    // Windows is the only one''',
AIX_UPTIME + '''
  #[cfg(target_family = "windows")]
  // SAFETY: windows API usage
  unsafe {
    // Windows is the only one''')
replace(si, 'pub fn os_uptime() -> u64 {', AIX_PROCENTRY)
ol = DENO / "ext" / "os" / "lib.rs"
AIX_RSS = '''/// AIX / IBM i PASE : mémoire de données du processus (pi_dvm, pages de 4 Ko) par
/// getprocs64 ; getrusage rend ru_maxrss = 0 sous PASE
#[cfg(target_os = "aix")]
fn rss() -> u64 {
  // SAFETY: getpid ne prend aucun argument.
  let pid = unsafe { libc::getpid() };
  sys_info::aix_procentry64(pid)
    .filter(|(trouve, _)| *trouve == pid)
    .map(|(_, p)| p[sys_info::AIX_PI_DVM] * 4096)
    .unwrap_or(0)
}
'''
replace_all(ol,
'''/// AIX / IBM i PASE : getrusage, ru_maxrss en kilo-octets (pic, faute de mieux)
#[cfg(target_os = "aix")]
fn rss() -> u64 {
  let mut usage = std::mem::MaybeUninit::<libc::rusage>::uninit();
  // SAFETY: `usage` is a valid pointer to a `libc::rusage` struct.
  if unsafe { libc::getrusage(libc::RUSAGE_SELF, usage.as_mut_ptr()) } != 0 {
    return 0;
  }
  // SAFETY: getrusage returned 0, `usage` is initialized.
  let usage = unsafe { usage.assume_init() };
  (usage.ru_maxrss as u64) * 1024
}
''', AIX_RSS)
replace(ol, '#[cfg(windows)]\nfn rss() -> u64 {', AIX_RSS + '''
#[cfg(windows)]
fn rss() -> u64 {''')

# ---- deno_node ----
nd = DENO / "ext" / "node" / "ops"
replace(nd / "constant.rs", '#[cfg(windows)]\n#[op2]\n#[serde]\npub fn op_node_fs_constants() -> FsConstants {',
'''#[cfg(target_os = "aix")]
#[op2]
#[serde]
pub fn op_node_fs_constants() -> FsConstants {
  common_unix_fs_constants()
}

#[cfg(windows)]
#[op2]
#[serde]
pub fn op_node_fs_constants() -> FsConstants {''')
# big-endian branch never compiled before: missing collect type
replace(nd / "buffer.rs", '      .map(|chunk| u16::from_le_bytes([chunk[0], chunk[1]]))\n      .collect();',
                            '      .map(|chunk| u16::from_le_bytes([chunk[0], chunk[1]]))\n      .collect::<Vec<u16>>();')
replace(nd / "dns.rs",
'''    let hints = libc::addrinfo {
      ai_flags: 0,
      ai_family,
      ai_socktype: libc::SOCK_STREAM,
      ai_protocol: 0,
      ai_addrlen: 0,
      ai_addr: std::ptr::null_mut(),
      ai_canonname: std::ptr::null_mut(),
      ai_next: std::ptr::null_mut(),
    };''',
'''    // SAFETY: addrinfo est une structure C sans invariant, zero = valeur neutre
    // (AIX a un champ ai_eflags en plus)
    let mut hints: libc::addrinfo = unsafe { std::mem::zeroed() };
    hints.ai_family = ai_family;
    hints.ai_socktype = libc::SOCK_STREAM;''')
replace(nd / "dns.rs", '            *len = info.ai_addrlen;', '            *len = info.ai_addrlen as _;')
replace(nd / "dns.rs", '      libc::getnameinfo(\n        c_sockaddr,\n        c_sockaddr_len,',
                         '      libc::getnameinfo(\n        c_sockaddr,\n        c_sockaddr_len as _,')
replace(nd / "os" / "cpus.rs", '#[cfg(target_os = "windows")]\npub fn cpu_info() -> Option<Vec<CpuInfo>> {',
'''/// AIX / IBM i PASE : une entree par processeur, sans temps CPU ni frequence
#[cfg(target_os = "aix")]
pub fn cpu_info() -> Option<Vec<CpuInfo>> {
  let n = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1);
  Some(
    (0..n)
      .map(|_| CpuInfo {
        model: String::from("IBM POWER (IBM i PASE)"),
        ..CpuInfo::default()
      })
      .collect(),
  )
}

#[cfg(target_os = "windows")]
pub fn cpu_info() -> Option<Vec<CpuInfo>> {''')
replace(nd / "udp.rs", '''  // No zone id was provided. Try to find interface by matching the address.
  #[cfg(unix)]''', '''  // No zone id was provided. Try to find interface by matching the address.
  #[cfg(all(unix, not(target_os = "aix")))]''')
# (the Windows branch already contains "as _": plain replacement)
_d = nd / "dns.rs"
_t = _d.read_text()
if "*len = info.ai_addrlen;\n" in _t:
    _d.write_text(_t.replace("*len = info.ai_addrlen;\n", "*len = info.ai_addrlen as _;\n"))
    print("patched:", _d, "(ai_addrlen)")

# rustyline: nix ioctl macros and Errno::EWOULDBLOCK are missing on AIX
ry = copy_crate("rustyline-17.0.0") / "src" / "tty" / "unix.rs"
replace(ry, 'nix::ioctl_read_bad!(win_size, libc::TIOCGWINSZ, libc::winsize);',
'''#[cfg(not(target_os = "aix"))]
nix::ioctl_read_bad!(win_size, libc::TIOCGWINSZ, libc::winsize);

/// AIX : nix ne fournit pas les macros ioctl ; appel direct
#[cfg(target_os = "aix")]
unsafe fn win_size(fd: libc::c_int, data: *mut libc::winsize) -> nix::Result<libc::c_int> {
    let r = libc::ioctl(fd, libc::TIOCGWINSZ as _, data);
    if r == -1 {
        Err(nix::errno::Errno::last())
    } else {
        Ok(r)
    }
}''')
replace(ry, 'Err(e) if e == Errno::EWOULDBLOCK || e == Errno::EINTR => Ok(None),',
              'Err(e) if e == Errno::EAGAIN || e == Errno::EINTR => Ok(None),')

# libsui (deno compile): reads the program's ELF notes; nothing like that in XCOFF. On AIX the
# section is appended after the end of the XCOFF file (the AIX loader only maps what the headers
# describe and ignores trailing bytes: verified on IBM i 7.5 with 1 MB appended to deno), followed
# by a trailer: <data><name><name length u32 BE><data length u64 BE>"SUIXCOF1". find_section reads
# the trailer of the running program (std::env::current_exe) and only the section, not the file.
su = copy_crate("libsui-0.16.4") / "lib.rs"
replace(su,
'''#[cfg(all(unix, not(target_vendor = "apple")))]
pub use elf::find_section;
#[cfg(all(unix, not(target_vendor = "apple")))]
pub use elf::find_section_in_current_image;''',
'''#[cfg(all(unix, not(target_vendor = "apple"), not(target_os = "aix")))]
pub use elf::find_section;
#[cfg(all(unix, not(target_vendor = "apple"), not(target_os = "aix")))]
pub use elf::find_section_in_current_image;
#[cfg(target_os = "aix")]
pub use xcoff::{find_section, find_section_in_current_image};

/// Trailer of a section appended to an XCOFF executable (AIX, IBM i PASE)
const XCOFF_SUI_MAGIC: &[u8; 8] = b"SUIXCOF1";

/// XCOFF (AIX, IBM i PASE): the section is appended after the end of the file, which the AIX
/// loader ignores, followed by <name><name length u32 BE><data length u64 BE>"SUIXCOF1".
pub struct Xcoff<'a> {
    data: &'a [u8],
}

impl<'a> Xcoff<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data }
    }

    pub fn append<W: Write>(&self, name: &str, sectdata: &[u8], writer: &mut W) -> Result<(), Error> {
        if !utils::is_xcoff(self.data) {
            return Err(Error::InvalidObject("Not a 64-bit XCOFF file"));
        }
        if self.data.ends_with(XCOFF_SUI_MAGIC) {
            return Err(Error::InvalidObject("XCOFF file already has an appended section"));
        }
        writer.write_all(self.data)?;
        writer.write_all(sectdata)?;
        writer.write_all(name.as_bytes())?;
        writer.write_all(&(name.len() as u32).to_be_bytes())?;
        writer.write_all(&(sectdata.len() as u64).to_be_bytes())?;
        writer.write_all(XCOFF_SUI_MAGIC)?;
        Ok(())
    }
}

#[cfg(target_os = "aix")]
mod xcoff {
    use std::io::{Read, Seek, SeekFrom};

    pub fn find_section(name: &str) -> std::io::Result<Option<&'static [u8]>> {
        let mut f = std::fs::File::open(std::env::current_exe()?)?;
        let size = f.seek(SeekFrom::End(0))?;
        if size < 20 {
            return Ok(None);
        }
        let mut trailer = [0u8; 20];
        f.seek(SeekFrom::End(-20))?;
        f.read_exact(&mut trailer)?;
        if &trailer[12..] != super::XCOFF_SUI_MAGIC {
            return Ok(None);
        }
        let name_len = u32::from_be_bytes(trailer[0..4].try_into().unwrap()) as u64;
        let data_len = u64::from_be_bytes(trailer[4..12].try_into().unwrap());
        let start = match size.checked_sub(20 + name_len).and_then(|n| n.checked_sub(data_len)) {
            Some(s) => s,
            None => return Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "bad XCOFF section trailer")),
        };
        let mut stored = vec![0u8; name_len as usize];
        f.seek(SeekFrom::Start(start + data_len))?;
        f.read_exact(&mut stored)?;
        if stored != name.as_bytes() {
            return Ok(None);
        }
        let mut data = vec![0u8; data_len as usize];
        f.seek(SeekFrom::Start(start))?;
        f.read_exact(&mut data)?;
        // read once per process, kept for its whole lifetime (like a mapped section)
        Ok(Some(Box::leak(data.into_boxed_slice())))
    }

    pub fn find_section_in_current_image(name: &str) -> std::io::Result<Option<&'static [u8]>> {
        find_section(name)
    }
}''')
replace(su,
'''    /// Check if the given data is a PE32+ binary''',
'''    /// Check if the given data is a 64-bit XCOFF binary (AIX, IBM i PASE)
    pub fn is_xcoff(data: &[u8]) -> bool {
        data.len() >= 2 && u16::from_be_bytes([data[0], data[1]]) == 0x01f7
    }

    /// Check if the given data is a PE32+ binary''')
replace(su, '#[cfg(all(unix, not(target_vendor = "apple")))]\nmod elf {',
              '#[cfg(all(unix, not(target_vendor = "apple"), not(target_os = "aix")))]\nmod elf {')

# zlib-ng: zbuild.h forces _POSIX_C_SOURCE, which hides UINT64_C & co in
# AIX <stdint.h> (unresolved .UINT64_C symbol at link time)
zb = DST / "libz-sys-1.1.20" / "src" / "zlib-ng" / "zbuild.h"
replace(zb, '#include <stdint.h>\n',
'''#include <stdint.h>
#ifdef _AIX
/* masques par _POSIX_C_SOURCE dans le <stdint.h> d'AIX */
#  ifndef UINT64_C
#    define UINT64_C(c) c ## ULL
#  endif
#  ifndef UINT32_C
#    define UINT32_C(c) c ## U
#  endif
#  ifndef INT64_C
#    define INT64_C(c) c ## LL
#  endif
#  ifndef SIZE_MAX
#    define SIZE_MAX ((size_t)-1)
#  endif
#endif
''')

# nix 0.29: AIX SigAction variants written for libc's old sa_union field;
# current libc has sa_sigaction as elsewhere -> use the generic variants
if (DST / "nix-0.29.0").exists():
    sg29 = DST / "nix-0.29.0" / "src" / "sys" / "signal.rs"
    replace_all(sg29, '        #[cfg(not(target_os = "aix"))]\n        unsafe fn install_sig',
                         '        #[cfg(all())] // AIX compris (correctif IBM i)\n        unsafe fn install_sig')
    replace_all(sg29, '        #[cfg(target_os = "aix")]\n        unsafe fn install_sig',
                         '        #[cfg(any())] // variante sa_union obsolete\n        unsafe fn install_sig')
    replace_all(sg29, '    #[cfg(not(target_os = "aix"))]\n    pub fn handler(&self) -> SigHandler {',
                         '    #[cfg(all())] // AIX compris (correctif IBM i)\n    pub fn handler(&self) -> SigHandler {')
    replace_all(sg29, '    #[cfg(target_os = "aix")]\n    pub fn handler(&self) -> SigHandler {',
                         '    #[cfg(any())] // variante sa_union obsolete\n    pub fn handler(&self) -> SigHandler {')

# open (open a URL): AIX joins the unix family (xdg-open...)
if (REG / "open-5.1.2").exists() or (DST / "open-5.1.2").exists():
    op = copy_crate("open-5.1.2") / "src" / "lib.rs"
    _t = op.read_text()
    if 'target_os = "aix"' not in _t:
        _t = _t.replace('    target_os = "solaris"\n))]', '    target_os = "solaris",\n    target_os = "aix"\n))]')
        _t = _t.replace('    target_os = "solaris",\n    target_os = "ios",', '    target_os = "solaris",\n    target_os = "aix",\n    target_os = "ios",')
        op.write_text(_t)
        print("patched:", op)
    # is_wsl is a dependency on Linux only: local function on AIX
    ou = DST / "open-5.1.2" / "src" / "unix.rs"
    _u = ou.read_text()
    if "fn est_wsl" not in _u:
        _u = _u.replace("is_wsl::is_wsl()", "est_wsl()")
        _u += '''
#[cfg(target_os = "aix")]
fn est_wsl() -> bool {
    false
}

#[cfg(not(target_os = "aix"))]
fn est_wsl() -> bool {
    is_wsl::is_wsl()
}
'''
        ou.write_text(_u)
        print("patched:", ou)

# aws-lc-sys: NO_ASM is rejected outside opt-level 0/1/2; on AIX there is no
# usable assembly, so accept it at any level (ibmi-os profile)
for version in ("0.40.0", "0.46.0"):
    ccb = DST / f"aws-lc-sys-{version}" / "builder" / "cc_builder.rs"
    if ccb.exists():
        replace_all(ccb, '            "0" | "1" | "2" => {\n                if is_no_asm() {',
                       '            _ if is_no_asm() || matches!(opt_level.as_str(), "0" | "1" | "2") => {\n                if is_no_asm() {')

# --- Deno's JavaScript: per-OS switches that ignore "aix" ---
# node:timers -> internal_binding/uv.ts: per-OS libuv error table, otherwise
# "Unreachable code" on the first setTimeout. AIX table = Linux names with
# PASE errno values (sys/errno.h); libuv-specific codes (EAI_*, -4xxx) kept,
# names without an AIX errno dropped (their Linux number would clash with an AIX errno).
uv = DENO / "ext" / "node" / "polyfills" / "internal_binding" / "uv.ts"
replace(uv,
"""const unreachable = () => {""",
"""// AIX / IBM i PASE : errno de sys/errno.h
const errnoAix: Record<string, number> = {
  EPERM: 1, ENOENT: 2, ESRCH: 3, EINTR: 4, EIO: 5, ENXIO: 6, E2BIG: 7,
  EBADF: 9, EAGAIN: 11, ENOMEM: 12, EACCES: 13, EFAULT: 14, EBUSY: 16,
  EEXIST: 17, EXDEV: 18, ENODEV: 19, ENOTDIR: 20, EISDIR: 21, EINVAL: 22,
  ENFILE: 23, EMFILE: 24, ENOTTY: 25, ETXTBSY: 26, EFBIG: 27, ENOSPC: 28,
  ESPIPE: 29, EROFS: 30, EMLINK: 31, EPIPE: 32, ERANGE: 34,
  EINPROGRESS: 55, EALREADY: 56, ENOTSOCK: 57, EDESTADDRREQ: 58,
  EMSGSIZE: 59, EPROTOTYPE: 60, ENOPROTOOPT: 61, EPROTONOSUPPORT: 62,
  EAFNOSUPPORT: 66, EADDRINUSE: 67, EADDRNOTAVAIL: 68, ENETDOWN: 69,
  ENETUNREACH: 70, ECONNABORTED: 72, ECONNRESET: 73, ENOBUFS: 74,
  EISCONN: 75, ENOTCONN: 76, ESHUTDOWN: 77, ETIMEDOUT: 78,
  ECONNREFUSED: 79, EHOSTDOWN: 80, EHOSTUNREACH: 81, ELOOP: 85,
  ENAMETOOLONG: 86, ENOTEMPTY: 87, ENOSYS: 109, EILSEQ: 116,
  ECANCELED: 117, EPROTO: 121, ENOTSUP: 124,
};
const codeToErrorAix: ErrorMapData = [];
for (let i = 0; i < codeToErrorLinux.length; i++) {
  const entry = codeToErrorLinux[i];
  const errno = errnoAix[entry[1][0]];
  if (errno !== undefined) {
    codeToErrorAix.push([-errno, entry[1]]);
  } else if (entry[0] <= -3000) {
    codeToErrorAix.push(entry);
  }
}
const errorToCodeAix: CodeMapData = ArrayPrototypeMap(
  codeToErrorAix,
  (entry) => [entry[1][0], entry[0]],
);

const unreachable = () => {""")
replace(uv, """    ? codeToErrorOpenBSD
    : unreachable(),""", """    ? codeToErrorOpenBSD
    : osType === "aix"
    ? codeToErrorAix
    : unreachable(),""")
replace(uv, """    ? errorToCodeOpenBSD
    : unreachable(),""", """    ? errorToCodeOpenBSD
    : osType === "aix"
    ? errorToCodeAix
    : unreachable(),""")

# node:os type(): Node on IBM i returns "OS400" (PASE uname)
replace(DENO / "ext" / "node" / "polyfills" / "os.ts",
"""    case "openbsd":
      return "OpenBSD";
    default:""",
"""    case "openbsd":
      return "OpenBSD";
    case "aix":
      return "OS400";
    default:""")

# Deno.stat: Unix fields (mode, uid, ino...) on AIX too
fsjs = DENO / "ext" / "fs" / "30_fs.js"
replace(fsjs, """Deno.build.os === "freebsd";' +""",
          """Deno.build.os === "freebsd" || Deno.build.os === "aix";' +""")
replace(fsjs, """    core.build.os === "freebsd" ||
    core.build.os === "openbsd";""", """    core.build.os === "freebsd" ||
    core.build.os === "openbsd" ||
    core.build.os === "aix";""")

# aws-lc: the "CPU jitter" entropy source finds no usable clock
# under PASE (jent_entropy_init = ENOTIME) -> RAND_bytes calls abort(): TLS,
# ECDSA, AES-GCM... abort. Use aws-lc's built-in no-jitter mode
# (OS seed: /dev/urandom, which works).
for version in ("0.40.0", "0.46.0"):
    es = DST / f"aws-lc-sys-{version}" / "aws-lc" / "crypto" / "fipsmodule" / "rand" / "entropy" / "entropy_sources.c"
    if es.exists():
        replace(es, "static int has_explicitly_opted_out_of_cpu_jitter(void) {\n#if defined(DISABLE_CPU_JITTER_ENTROPY)\n",
                  "static int has_explicitly_opted_out_of_cpu_jitter(void) {\n#if defined(DISABLE_CPU_JITTER_ENTROPY) || defined(_AIX)\n")

# process.arch (node:process, node:crypto...): big-endian powerpc64 unknown
# -> "unreachable". Node on IBM i returns "ppc64".
replace(DENO / "ext" / "node" / "polyfills" / "_process" / "process.ts",
"""  } else if (build.arch == "powerpc64le") {
    return "ppc64";""",
"""  } else if (build.arch == "powerpc64le" || build.arch == "powerpc64") {
    return "ppc64";""")

# mio: Deno 2.9.8 locks mio 1.0.3, whose poll() selector on AIX is
# broken (accepted socket left blocking, no data reported on a pipe:
# Deno.serve and Deno.Command hung). mio 1.2 fixes both: the
# Cargo.lock.ibmi moves to mio 1.2.4, no patch needed here anymore.

# dlopen2: on AIX, a shared library is often an archive member
# ("libdb400.a(shr_64.o)"); dlopen() then requires RTLD_MEMBER. Without it,
# Deno.dlopen can load neither the Db2 CLI nor the PASE libc.
du = DST / "dlopen2-0.6.1" / "src" / "raw" / "unix.rs"
replace(du, "    let handle = dlopen(cstr.as_ptr(), DEFAULT_FLAGS);\n",
"""    #[cfg(target_os = "aix")]
    let handle = {
        let membre = name.as_bytes().last() == Some(&b')');
        dlopen(cstr.as_ptr(), if membre { DEFAULT_FLAGS | libc::RTLD_MEMBER } else { DEFAULT_FLAGS })
    };
    #[cfg(not(target_os = "aix"))]
    let handle = dlopen(cstr.as_ptr(), DEFAULT_FLAGS);
""")

# Deno FFI: the "turbocall" call compiler (Cranelift) does not support
# POWER; Deno falls back to the regular call path but warns for every symbol.
replace(DENO / "ext" / "ffi" / "dlfcn.rs",
"""        log::warn!("Failed to compile FFI turbocall: {e}");""",
"""        #[cfg(not(target_os = "aix"))]
        log::warn!("Failed to compile FFI turbocall: {e}");
        #[cfg(target_os = "aix")]
        let _ = e; // pas de Cranelift pour POWER : appel FFI classique""")

# Deno ICU data (V8 engine): deno_core_icudata embeds icudtl.dat, which is
# little-endian; V8 on IBM i (big-endian) requires icudtb.dat ("Failed to
# initialize ICU" otherwise). Use the big-endian version shipped by Chromium with
# rusty_v8 (same ICU as the one compiled into librusty_v8.a).
ICU_BE = pathlib.Path("/QOpenSys/opt/denoibmi/v8aix/icudtb.dat")
if (REG / "deno_core_icudata-0.77.0").exists() and ICU_BE.exists():
    ic = copy_crate("deno_core_icudata-0.77.0") / "src" / "icudtl.dat"
    if ic.read_bytes()[:16] != ICU_BE.read_bytes()[:16] or ic.stat().st_size != ICU_BE.stat().st_size:
        shutil.copyfile(ICU_BE, ic)
        print("patched:", ic, "(big-endian ICU)")

# v8 crate (V8 engine): PropertyFilter, PropertyAttribute and PropertyHandlerFlags are
# #[repr(C)] struct(u32) passed by value to the C++ API, where they are enums. On
# big-endian POWER (AIX), a 4-byte struct is left-justified in the register,
# an integer right-justified: V8 read 0 (PropertyFilter → ALL_PROPERTIES, console.log printed
# keys twice and showed [length]). repr(transparent) = passed like a u32.
if (REG / "v8-150.4.0").exists():
    v8c = copy_crate("v8-150.4.0")
    for name in ("property_filter.rs", "property_attribute.rs", "property_handler_flags.rs"):
        f = v8c / "src" / name
        t = f.read_text()
        if "#[repr(C)]" in t:
            f.write_text(t.replace("#[repr(C)]", "#[repr(transparent)]  // deno-ibmi : ABI big-endian", 1))
            print("patched:", f)

# Return buffers read by JavaScript as Uint32Array (machine's NATIVE byte order):
# Rust wrote them little-endian → on IBM i (big-endian) line 4 read as 67108864
# (0x04000000), test and bench ids byte-swapped. to_ne_bytes = native order.
replace(DENO / "libs" / "core" / "ops_builtin_v8.rs",
"""  ret_buf[0..4].copy_from_slice(&line_number.to_le_bytes());
  ret_buf[4..8].copy_from_slice(&column_number.to_le_bytes());""",
"""  // deno-ibmi : lu par JS en Uint32Array, donc ordre natif (big-endian sur IBM i)
  ret_buf[0..4].copy_from_slice(&line_number.to_ne_bytes());
  ret_buf[4..8].copy_from_slice(&column_number.to_ne_bytes());""")
for f in (DENO / "cli" / "ops" / "testing.rs", DENO / "cli" / "ops" / "bench.rs"):
    replace(f,
"""  ret_buf.copy_from_slice(&(id as u32).to_le_bytes());""",
"""  ret_buf.copy_from_slice(&(id as u32).to_ne_bytes()); // deno-ibmi : Uint32Array natif""")

# os.totalmem() returned 0: Deno has no AIX branch in mem_info, and sysconf
# (_SC_AIX_REALMEM, _SC_PHYS_PAGES) fails under PASE. getsystemcfg(SC_PHYSMEM) works.
replace(DENO / "ext" / "os" / "sys_info.rs",
"""  #[cfg(any(target_os = "android", target_os = "linux"))]
  {
    let mut info = std::mem::MaybeUninit::uninit();
    // SAFETY: `info` is a valid pointer to a `libc::sysinfo` struct.""",
"""  // deno-ibmi : mémoire physique sous PASE (sysconf échoue, getsystemcfg répond)
  #[cfg(target_os = "aix")]
  {
    unsafe extern "C" {
      fn getsystemcfg(label: libc::c_int) -> u64;
    }
    const SC_PHYSMEM: libc::c_int = 33; // <sys/systemcfg.h>
    // SAFETY: getsystemcfg ne prend qu'un entier et ne touche à aucun pointeur.
    mem_info.total = unsafe { getsystemcfg(SC_PHYSMEM) };
  }
  #[cfg(any(target_os = "android", target_os = "linux"))]
  {
    let mut info = std::mem::MaybeUninit::uninit();
    // SAFETY: `info` is a valid pointer to a `libc::sysinfo` struct.""")

if (REG / "v8-150.4.0").exists():
    # Dynamic import callbacks: V8 expects a MaybeLocal<Promise> returned by value. The AIX
    # ABI returns every aggregate through a hidden pointer (like Windows x64), whereas the
    # rusty_v8 "unix" variant returns a raw pointer in a register: arguments shifted by one,
    # every import() crashed V8 ("null prototype chain root", PushStackTraceAndDie).
    # On AIX, use the Windows variant (return pointer as first argument).
    f = copy_crate("v8-150.4.0") / "src" / "isolate.rs"
    t = f.read_text()
    if "deno-ibmi : MaybeLocal" not in t:
        UNIX = '#[cfg(target_family = "unix")]'
        WIN = '#[cfg(all(\n  target_family = "windows",\n  any(target_arch = "x86_64", target_arch = "aarch64")\n))]'
        WIN_INDENTED = WIN.replace("\n", "\n    ").replace("#[cfg", "    #[cfg", 1)
        NEW_CFG = ('#[cfg(any(target_os = "aix", all(target_family = "windows", '
                'any(target_arch = "x86_64", target_arch = "aarch64"))))]')
        assert t.count(UNIX) == 4 and t.count(WIN) == 2 and t.count(WIN_INDENTED) == 2, "isolate.rs a changé"
        t = t.replace(UNIX, '#[cfg(all(target_family = "unix", not(target_os = "aix")))]')
        t = t.replace(WIN_INDENTED, "    " + NEW_CFG)
        t = t.replace(WIN, NEW_CFG + "  // deno-ibmi : MaybeLocal par pointeur caché (ABI AIX)")
        f.write_text(t)
        print("patched:", f)


# mio 1.2.4, accepted Unix sockets: on AIX mio assumes the accepted socket inherits
# O_NONBLOCK from the listener (true on BSD, false under PASE; same defect as the accepted
# TCP socket fixed in mio 1.2). The server's first read() blocked the whole thread
# (netUnixCloseCancelsPendingReadAndSendsEof, httpServerOnUnixSocket, websocket
# through a unix proxy; reproduced in pure Rust: examples/mio-wakeup/src/bin/unix.rs).
if (REG / "mio-1.2.4").exists():
    replace(copy_crate("mio-1.2.4") / "src" / "sys" / "unix" / "uds" / "listener.rs",
"""            target_os = "vita",
            target_os = "nto",
        ))]
        syscall!(fcntl(socket, libc::F_SETFL, libc::O_NONBLOCK))?;""",
"""            target_os = "vita",
            target_os = "nto",
            target_os = "aix", // deno-ibmi : PASE n'hérite pas O_NONBLOCK
        ))]
        syscall!(fcntl(socket, libc::F_SETFL, libc::O_NONBLOCK))?;""")

# inventory 0.3.21 (inheritance of deno_core cppgc objects, 25 declarations): its
# static constructors go through .init_array (ELF), __mod_init_func or .CRT$XCU;
# nothing for AIX, so they are never called: empty list, every AsyncWrap-derived object rejected
# ("TypeError: expected AsyncWrap" from node:net, fetch hung in
# fetchConnectionClosedBeforeMessageComplete). The AIX linker (-bcdtors) calls the
# functions named __sinit<priority>_…: unique name per submit! call.
# Reproduced: examples/inventory-ctors (0 items out of 3 without the patch, 3 with it).
if (REG / "inventory-0.3.21").exists():
    replace(copy_crate("inventory-0.3.21") / "src" / "lib.rs",
"""            unsafe extern "C" fn __ctor() {""",
"""            // deno-ibmi : constructeur statique XCOFF (lieur AIX -bcdtors)
            #[cfg_attr(target_os = "aix", export_name = $crate::core::concat!("__sinit80000000_inventory_", $crate::core::module_path!(), "_", $crate::core::line!(), "_", $crate::core::column!()))]
            unsafe extern "C" fn __ctor() {""")

# V8 under PASE: OS::DecommitPages (platform-aix.cc) does munmap then mmap(MAP_FIXED),
# because MAP_FIXED over an already mapped range fails on AIX (errno 12); another thread can
# grab the address in between → CHECK_EQ(ptr, address) and abort (worker_test under
# load). With XPG_SUS_ENV=ON (SPEC1170 mode, read by libc at startup only:
# setenv later has no effect), MAP_FIXED replaces the mapping directly,
# no more race (verified in C). Deno therefore re-executes itself with the variable set.
# Full run with the variable: no regression (93.6 %). DENO_IBMI_SANS_XPG=1
# disables the re-exec.
replace(DENO / "cli" / "lib.rs",
"""pub fn main() {
  boot_phase("main start");""",
"""// deno-ibmi : mode SPEC1170 de la libc AIX (MAP_FIXED direct), voir correctifs.py
#[cfg(target_os = "aix")]
fn relancer_avec_xpg_sus_env() {
  use std::os::unix::process::CommandExt;
  if env::var_os("XPG_SUS_ENV").is_some_and(|v| v == "ON")
    || env::var_os("DENO_IBMI_SANS_XPG").is_some()
  {
    return;
  }
  let Ok(exe) = env::current_exe() else { return };
  let err = std::process::Command::new(exe)
    .args(env::args_os().skip(1))
    .env("XPG_SUS_ENV", "ON")
    .exec();
  eprintln!("deno-ibmi : relance avec XPG_SUS_ENV=ON impossible ({err}), on continue");
}

pub fn main() {
  #[cfg(target_os = "aix")]
  relancer_avec_xpg_sus_env();
  boot_phase("main start");""")

# ---- 2026-11-04: towards 99 % ----

# JavaScript BigInt to num_bigint (Deno.KvU64, integer kv keys, serde_v8): V8's 64-bit
# words were reinterpreted as a u32 slice by align_to, which assumes a
# little-endian CPU. On POWER the two halves are swapped: 1n became 2^32
# (17 kv_test cases). Explicit split, low half first, as num_bigint expects.
replace(DENO / "libs" / "serde_v8" / "magic" / "bigint.rs",
"""    let (prefix, slice, suffix) = unsafe { words.align_to::<u32>() };
    assert!(prefix.is_empty());
    assert!(suffix.is_empty());
    assert_eq!(slice.len(), words.len() * 2);
    let big_int = num_bigint::BigInt::from_slice(sign, slice);""",
"""    // deno-ibmi : découpage portable (align_to suppose un processeur little-endian)
    let slice: Vec<u32> = words.iter().flat_map(|w| [*w as u32, (*w >> 32) as u32]).collect();
    let big_int = num_bigint::BigInt::from_slice(sign, &slice);""")
replace(DENO / "libs" / "core" / "convert.rs",
"""    let (prefix, slice, suffix) = unsafe { big_int.words.align_to::<u32>() };
    assert!(prefix.is_empty());
    assert!(suffix.is_empty());
    assert_eq!(slice.len(), big_int.words.len() * 2);""",
"""    // deno-ibmi : découpage portable (align_to suppose un processeur little-endian)
    let slice: Vec<u32> = big_int
      .words
      .iter()
      .flat_map(|w| [*w as u32, (*w >> 32) as u32])
      .collect();
    let slice = &slice[..];""")

# signal-hook 0.3.18 (Deno.addSignalListener, and SIGTERM/SIGINT/SIGHUP of every deno process):
# under PASE, recv(MSG_NONBLOCK) ignores the flag and BLOCKS on an empty socket (verified:
# examples/signals/src/bin/msg_nonblock.rs). The signal thread drains its socket pair with this
# recv before delivering signals: stuck on the first pass, no signal ever arrived
# (signal_test hung, "kill" had no effect on deno). Drain preceded by a zero-timeout poll();
# on the signal handler side, write socket set to O_NONBLOCK (send must never block).
if (REG / "signal-hook-0.3.18").exists():
    sh = copy_crate("signal-hook-0.3.18") / "src"
    replace(sh / "iterator" / "backend.rs",
"""            while libc::recv(
                self.read.as_raw_fd(),""",
"""            // deno-ibmi : PASE ignore MSG_NONBLOCK, recv bloquerait sur la socket vide
            #[cfg(target_os = "aix")]
            let pret = || {
                let mut p = libc::pollfd { fd: self.read.as_raw_fd(), events: libc::POLLIN, revents: 0 };
                libc::poll(&mut p, 1, 0) > 0
            };
            #[cfg(not(target_os = "aix"))]
            let pret = || true;
            while pret() && libc::recv(
                self.read.as_raw_fd(),""")
    replace(sh / "iterator" / "mod.rs",
"""        let (read, write) = UnixStream::pair()?;
        Ok(SignalsInfo(SignalDelivery::with_pipe(""",
"""        let (read, write) = UnixStream::pair()?;
        // deno-ibmi : PASE ignore MSG_NONBLOCK ; le send du gestionnaire ne doit pas bloquer
        #[cfg(target_os = "aix")]
        write.set_nonblocking(true)?;
        Ok(SignalsInfo(SignalDelivery::with_pipe(""")

# Normal exit after non-blocking FFI calls (Db2): SIGILL, rc 132, 2 times out of 3.
# Stack (dbx64 on the core): pthread_exit → _specific_data_cleanup → jump to 0. Deno closes
# (dlclose) the library at the end, then the non-blocking call threads exit and
# call the thread-specific data destructor registered by libdb400: unloaded code.
# On AIX, a library opened by Deno.dlopen is no longer unloaded.
replace(DST / "dlopen2-0.6.1" / "src" / "raw" / "unix.rs",
"""pub fn close_lib(handle: Handle) -> Handle {
    let result = unsafe { dlclose(handle) };""",
"""pub fn close_lib(handle: Handle) -> Handle {
    // deno-ibmi : pas de dlclose sous AIX (destructeurs de données de fil de la bibliothèque
    // appelés après déchargement : SIGILL à la sortie, cf. correctifs.py)
    #[cfg(target_os = "aix")]
    let result = { let _ = handle; 0 };
    #[cfg(not(target_os = "aix"))]
    let result = unsafe { dlclose(handle) };""")

# Deno.watchFs: notify has no native watcher for AIX and falls back to PollWatcher, which
# rescans the tree every 30 s by default: tests wait for their events
# until the timeout. 100 ms interval on AIX, with content comparison; and, to get closer
# to inotify: nonexistent path rejected (NotFound; PollWatcher accepts it), parent directory
# modification dropped (PollWatcher reports it on every entry creation or deletion).
# One gap remains: a rename arrives as create + remove, not as "rename".
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""  let watcher: RecommendedWatcher = Watcher::new(
""",
"""  // deno-ibmi : AIX → PollWatcher, 30 s par défaut ; 100 ms
  #[cfg(target_os = "aix")]
  let config = notify::Config::default()
    .with_poll_interval(std::time::Duration::from_millis(100))
    // date de modification à la seconde sous PASE : sans comparer le contenu, deux écritures
    // dans la même seconde passent inaperçues
    .with_compare_contents(true);
  #[cfg(not(target_os = "aix"))]
  let config = Default::default();
  let watcher: RecommendedWatcher = Watcher::new(
""")
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""    Default::default(),
  )
  .map_err(|e| FsEventsError::Notify(JsNotifyError(e)))?;""",
"""    config, // deno-ibmi : intervalle de scrutation sous AIX
  )
  .map_err(|e| FsEventsError::Notify(JsNotifyError(e)))?;""")
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""  matches!(
    event.kind,
    EventKind::Access(AccessKind::Open(AccessMode::Any))
  )
}""",
"""  // deno-ibmi : sous AIX (PollWatcher), créer ou supprimer une entrée produit aussi une
  // modification du dossier parent, qu'inotify ne signale pas
  #[cfg(target_os = "aix")]
  if matches!(event.kind, EventKind::Modify(_))
    && !event.paths.is_empty()
    && event.paths.iter().all(|p| p.is_dir())
  {
    return true;
  }
  matches!(
    event.kind,
    EventKind::Access(AccessKind::Open(AccessMode::Any))
  )
}""")
# AIX helper functions: anchored before "struct WatchSender {"
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""struct WatchSender {""",
"""/// deno-ibmi : PollWatcher accepte un chemin inexistant, inotify le refuse (NotFound)
fn aix_verifier_chemin(_path: &std::path::Path) -> notify::Result<()> {
  #[cfg(target_os = "aix")]
  if !_path.exists() {
    return Err(notify::Error::path_not_found().add_path(_path.to_path_buf()));
  }
  Ok(())
}

struct WatchSender {""")
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""        && let Err(e) = watcher.watch(path, recursive_mode)""",
"""        && let Err(e) = aix_verifier_chemin(path)
          .and_then(|_| watcher.watch(path, recursive_mode))""")

# notify 8.2.0, PollWatcher (the only watcher on AIX): inotify reports a file's creation
# THEN the write of its content; PollWatcher only saw the creation. Tests (and code
# waiting for "create" then "modify") kept waiting (watchFsBasic expects 3 events
# for 2 written files). On AIX: creation of a non-empty file → create + modify.
if (REG / "notify-8.2.0").exists():
    replace(copy_crate("notify-8.2.0") / "src" / "poll.rs",
"""                // emit event
                let event =
                    PathData::compare_to_event(path, old_path_data.as_ref(), Some(&new_path_data));
                if let Some(event) = event {
                    data_builder.emitter.emit_ok(event);
                }""",
"""                // deno-ibmi : fichier créé avec du contenu → création puis modification (inotify)
                #[cfg(target_os = "aix")]
                let cree_non_vide = old_path_data.is_none()
                    && std::fs::metadata(&path).map(|m| m.is_file() && m.len() > 0).unwrap_or(false);
                #[cfg(target_os = "aix")]
                let chemin = path.clone();
                // emit event
                let event =
                    PathData::compare_to_event(path, old_path_data.as_ref(), Some(&new_path_data));
                if let Some(event) = event {
                    data_builder.emitter.emit_ok(event);
                }
                #[cfg(target_os = "aix")]
                if cree_non_vide {
                    data_builder.emitter.emit_ok(
                        Event::new(EventKind::Modify(ModifyKind::Data(DataChange::Any))).add_path(chemin),
                    );
                }""")
    # Watched root deleted (watchFs on a file, then Deno.remove): PollWatcher emitted
    # a "not found" ERROR instead of the "remove" event (inotify: IN_DELETE_SELF).
    # On AIX, let the vanished-path detection emit the removal.
    replace(DST / "notify-8.2.0" / "src" / "poll.rs",
"""                    Err(err) => {
                        log::warn!("walkdir error scanning {err:?}");""",
"""                    Err(err) => {
                        // deno-ibmi : racine ou entrée disparue → « remove » au passage
                        // suivant (chemins disparus), pas d'erreur
                        #[cfg(target_os = "aix")]
                        if err.io_error().is_some_and(|e| e.kind() == io::ErrorKind::NotFound) {
                            return None;
                        }
                        log::warn!("walkdir error scanning {err:?}");""")

# Renames done by Deno itself (Deno.rename, Node's fs.rename): polling does not see
# a file created then renamed between two passes (watchFsRename waited forever and
# blocked the next 16 cases, which all pass without it). On AIX, deno_fs reports every
# successful rename to watchers in the same process ("rename" event [old, new],
# like inotify); changes made by other processes are still seen by polling.
replace(DENO / "ext" / "fs" / "lib.rs",
"""pub use crate::std_fs::RealFs;""",
"""pub use crate::std_fs::RealFs;

/// deno-ibmi : observateurs de renommage du processus (runtime/ops/fs_events.rs, AIX).
#[cfg(target_os = "aix")]
#[allow(clippy::type_complexity)]
pub static AIX_RENOMMAGE: std::sync::Mutex<
  Vec<std::sync::Weak<dyn Fn(&std::path::Path, &std::path::Path) + Send + Sync>>,
> = std::sync::Mutex::new(Vec::new());

/// deno-ibmi : signale un renommage réussi aux observateurs encore vivants.
#[cfg(target_os = "aix")]
pub fn aix_signaler_renommage(ancien: &std::path::Path, nouveau: &std::path::Path) {
  let vivants: Vec<_> = {
    let mut l = AIX_RENOMMAGE.lock().unwrap();
    l.retain(|w| w.strong_count() > 0);
    l.iter().filter_map(|w| w.upgrade()).collect()
  };
  for f in vivants {
    f(ancien, nouveau);
  }
}""")
replace(DENO / "ext" / "fs" / "ops.rs",
"""  let fs = state.borrow::<FileSystemRc>();
  fs.rename_sync(&oldpath, &newpath)
    .context_two_path("rename", &oldpath, &newpath)?;
""",
"""  let fs = state.borrow::<FileSystemRc>();
  fs.rename_sync(&oldpath, &newpath)
    .context_two_path("rename", &oldpath, &newpath)?;
  #[cfg(target_os = "aix")]
  crate::aix_signaler_renommage(AsRef::<Path>::as_ref(&oldpath), AsRef::<Path>::as_ref(&newpath));
""")
replace(DENO / "ext" / "fs" / "ops.rs",
"""  fs.rename_async(oldpath.as_owned(), newpath.as_owned())
    .await
    .context_two_path("rename", &oldpath, &newpath)?;
""",
"""  fs.rename_async(oldpath.as_owned(), newpath.as_owned())
    .await
    .context_two_path("rename", &oldpath, &newpath)?;
  #[cfg(target_os = "aix")]
  crate::aix_signaler_renommage(AsRef::<Path>::as_ref(&oldpath), AsRef::<Path>::as_ref(&newpath));
""")
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""  let watcher: RecommendedWatcher = Watcher::new(
    move |res: Result<NotifyEvent, NotifyError>| {""",
"""  let watcher: RecommendedWatcher = Watcher::new(
    aix_enregistrer(move |res: Result<NotifyEvent, NotifyError>| {""")
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""    },
    config, // deno-ibmi : intervalle de scrutation sous AIX""",
"""    }),
    config, // deno-ibmi : intervalle de scrutation sous AIX""")
replace(DENO / "runtime" / "ops" / "fs_events.rs",
"""/// deno-ibmi : PollWatcher accepte un chemin inexistant, inotify le refuse (NotFound)
fn aix_verifier_chemin""",
"""/// deno-ibmi : hors AIX, le gestionnaire d'événements est passé tel quel.
#[cfg(not(target_os = "aix"))]
fn aix_enregistrer<F>(f: F) -> F {
  f
}

/// deno-ibmi : sous AIX, le gestionnaire reçoit aussi les renommages faits par deno_fs.
#[cfg(target_os = "aix")]
fn aix_enregistrer<F>(f: F) -> impl Fn(Result<NotifyEvent, NotifyError>) + Send + 'static
where
  F: Fn(Result<NotifyEvent, NotifyError>) + Send + Sync + 'static,
{
  let f = Arc::new(f);
  let f2 = f.clone();
  let rappel: Arc<dyn Fn(&Path, &Path) + Send + Sync> =
    Arc::new(move |ancien: &Path, nouveau: &Path| {
      // chemins absolus, comme ceux de la scrutation (le dossier existe encore après coup)
      let absolu = |p: &Path| {
        let dossier = match p.parent() {
          Some(d) if !d.as_os_str().is_empty() => d,
          _ => Path::new("."),
        };
        std::fs::canonicalize(dossier)
          .map(|d| d.join(p.file_name().unwrap_or_default()))
          .unwrap_or_else(|_| p.to_path_buf())
      };
      let ev = NotifyEvent::new(EventKind::Modify(ModifyKind::Name(
        notify::event::RenameMode::Both,
      )))
      .add_path(absolu(ancien))
      .add_path(absolu(nouveau));
      f2(Ok(ev));
    });
  deno_fs::AIX_RENOMMAGE
    .lock()
    .unwrap()
    .push(Arc::downgrade(&rappel));
  // le rappel vit aussi longtemps que l'observateur
  move |res| {
    let _ = &rappel;
    f(res)
  }
}

/// deno-ibmi : PollWatcher accepte un chemin inexistant, inotify le refuse (NotFound)
fn aix_verifier_chemin""")
if (REG / "notify-8.2.0").exists():
    # Polling race: an entry listed then deleted before its metadata was read
    # raised a "not found" ERROR (watchFsIgnoreRemove, 1 time out of 3);
    # inotify never produces one. On AIX, vanished entry → nothing here, "remove" on the next
    # pass (vanished paths). Same rule in the walk (the "vanished root" block).
    replace(DST / "notify-8.2.0" / "src" / "poll.rs",
"""                        // emit event.
                        let path = entry.into_path();
                        data_builder.emitter.emit_io_err(e, Some(path));""",
"""                        // deno-ibmi : entrée disparue entre parcours et métadonnées → pas d'erreur
                        #[cfg(target_os = "aix")]
                        if e.io_error().is_some_and(|e| e.kind() == io::ErrorKind::NotFound) {
                            return None;
                        }
                        // emit event.
                        let path = entry.into_path();
                        data_builder.emitter.emit_io_err(e, Some(path));""")

# npm (2026-11-05): every npm package failed ("Failed loading https://registry.npmjs.org/chalk:
# UnmatchedBrace", or a "range end index … out of range" panic for cowsay). The registry's fast
# JSON parser (libs/npm/fast_registry_json, based on simdjson), in its portable version
# (neither x86_64 nor NEON), builds its bit masks in a 16-byte vector and then
# REINTERPRETS it as u16/u64 (bytemuck::must_cast): little-endian order assumed. On POWER the
# mask bytes are swapped, so braces and quotes are detected in the wrong place. Explicit
# little-endian read, identical on x86 and ARM.
SIMD = DENO / "libs" / "npm" / "fast_registry_json" / "simd" / "width_128.rs"
replace(SIMD,
"""            bytemuck::must_cast::<u8x16, wide::u16x8>(tmp).as_array_ref()[0] as u32""",
"""            // deno-ibmi : masque relu en little-endian (must_cast suppose un processeur LE)
            let o = tmp.as_array_ref();
            u16::from_le_bytes([o[0], o[1]]) as u32""")
replace(SIMD,
"""            bytemuck::must_cast::<u8x16, wide::u64x2>(sum0).as_array_ref()[0]""",
"""            // deno-ibmi : masque relu en little-endian (must_cast suppose un processeur LE)
            let o = sum0.as_array_ref();
            u64::from_le_bytes([o[0], o[1], o[2], o[3], o[4], o[5], o[6], o[7]])""")

# ---- 2026-11-12: deno compile ----

# deno compile on IBM i: the section is appended to the XCOFF runtime (libsui patch above);
# the runtime is the denort binary shipped next to deno (RPM: /QOpenSys/pkgs/lib/deno/denort),
# found there without DENORT_BIN (there is no denort download for AIX).
STANDALONE = DENO / "cli" / "standalone" / "binary.rs"
replace(STANDALONE,
"""  } else if target.contains("windows") {
    let mut pe = libsui::PortableExecutable::from(&original_bin)?;""",
"""  } else if target.contains("aix") {
    // deno-ibmi : section ajoutee apres la fin du fichier XCOFF (voir patches.py)
    libsui::Xcoff::new(&original_bin).append(
      "d3n0l4nd",
      &data_section_bytes,
      &mut file_writer,
    )?;
  } else if target.contains("windows") {
    let mut pe = libsui::PortableExecutable::from(&original_bin)?;""")
replace(STANDALONE,
"""  libsui::utils::is_elf(&data)
    || libsui::utils::is_pe(&data)""",
"""  libsui::utils::is_elf(&data)
    || libsui::utils::is_xcoff(&data)
    || libsui::utils::is_pe(&data)""")
replace(STANDALONE,
"""fn get_dev_binary_path() -> Option<OsString> {
  env::var_os("DENORT_BIN").or_else(|| {
    env::current_exe().ok().and_then(|exec_path| {
      if exec_path""",
"""fn get_dev_binary_path() -> Option<OsString> {
  env::var_os("DENORT_BIN").or_else(|| {
    env::current_exe().ok().and_then(|exec_path| {
      // deno-ibmi : pas de denort a telecharger pour AIX, il est livre a cote de deno
      if cfg!(target_os = "aix")
        || exec_path""")

# denort: same SPEC1170 re-exec as deno (V8 needs MAP_FIXED to replace mappings, see above), so
# that a compiled program runs correctly without XPG_SUS_ENV=ON set by the caller.
replace(DENO / "cli" / "rt" / "lib.rs",
"""pub fn main() {
  init_logging(None, None);""",
"""// deno-ibmi : mode SPEC1170 de la libc AIX (MAP_FIXED direct), comme deno (cli/lib.rs)
#[cfg(target_os = "aix")]
fn relancer_avec_xpg_sus_env() {
  use std::os::unix::process::CommandExt;
  if env::var_os("XPG_SUS_ENV").is_some_and(|v| v == "ON")
    || env::var_os("DENO_IBMI_SANS_XPG").is_some()
  {
    return;
  }
  let Ok(exe) = env::current_exe() else { return };
  let err = std::process::Command::new(exe)
    .args(env::args_os().skip(1))
    .env("XPG_SUS_ENV", "ON")
    .exec();
  eprintln!("deno-ibmi : relance avec XPG_SUS_ENV=ON impossible ({err}), on continue");
}

pub fn main() {
  #[cfg(target_os = "aix")]
  relancer_avec_xpg_sus_env();
  init_logging(None, None);""")

if REPORT:
    print()
    print(f"== REPORT: {len(FAILURES)} patch(es) no longer apply")
    for f, m in FAILURES:
        print(f"   {f}: {m}")

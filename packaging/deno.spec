# deno.spec - Deno for IBM i (PASE), repackaging of a binary built by build/build.sh.
#
# Usage: built by ibmi/make-rpm.sh on IBM i (rpm-build from the IBM yum repository):
#   rpmbuild --define "_topdir <dir>" --define "deno_version 2.9.8" --define "deno_release 1" \
#            --define "deno_ibmi_commit <commit>" -bb deno.spec
# Sources (in %{_sourcedir}): deno, libpaseat.a, libunwind.a, deno-launcher.sh, db2.ts, LICENSE,
# THIRD_PARTY_NOTICES.md, THIRD_PARTY_LICENSES.md, BUILD-INFO.
#
# The deno binary is cross-compiled on Linux, then linked and tested on IBM i (see the deno-ibmi
# repository); this spec only installs it, following the conventions of the IBM i RPMs
# (/QOpenSys/pkgs prefix, ppc64, OS tag ibmi7.5: built with --target ppc64-ibmi7.5,
# so that rpm refuses it on 7.3 and 7.4, where the binary does not load: the PASE libc of 7.3 lacks
# posix_fallocate64, posix_fadvise64 and strftime_l; 7.4 is not tested).

# no ".ibmi7.x" suffix in the release: the IBM i RPMs have none, and one package serves every release
%global dist %{nil}
%global _rpmfilename %%{ARCH}/%%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm
# no machine name in the package header
%global _buildhost ibmi-build
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _binary_payload w9.xzdio

%global pkgs  /QOpenSys/pkgs
%global libd  %{pkgs}/lib/deno

Name:           deno
Version:        %{deno_version}
Release:        %{deno_release}
Summary:        Deno JavaScript and TypeScript runtime (V8 engine) for IBM i PASE
License:        MIT; bundled components under their own licenses (see THIRD_PARTY_LICENSES.md)
URL:            https://github.com/Handedge/deno-ibmi
Packager:       Sylvain AKTEPE <16803966+Handedge@users.noreply.github.com>
Vendor:         Sylvain AKTEPE (deno-ibmi)
Source0:        deno
Source1:        libpaseat.a
Source2:        libunwind.a
Source3:        deno-launcher.sh
Source4:        db2.ts
Source5:        LICENSE
Source6:        THIRD_PARTY_NOTICES.md
Source7:        THIRD_PARTY_LICENSES.md
Source8:        BUILD-INFO
# Only PASE system libraries are needed (libc, libpthread, libbsd); libpaseat and the IBM
# libunwind are shipped in %{libd}, which is first in the binary's library search path.
AutoReqProv:    no

%description
Deno, the JavaScript and TypeScript runtime, ported to IBM i (PASE) with the V8 engine.
Unofficial build: not affiliated with, sponsored or endorsed by Deno Land Inc. or IBM.

Includes Deno.serve (HTTP and native HTTPS), fetch, npm packages, Deno.Command, FFI, and a Db2 for i
module for TypeScript (%{pkgs}/share/deno/db2.ts, through the PASE SQL CLI). Requires IBM i 7.5 or
later on a POWER8 or later system. "deno compile" is not supported. Built from deno-ibmi commit
%{deno_ibmi_commit}.

%prep
# nothing to unpack: the sources are the files listed above

%build
# nothing to build: the binary is built and tested by build/build.sh

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{pkgs}/bin %{buildroot}%{libd} %{buildroot}%{pkgs}/share/deno \
         %{buildroot}%{pkgs}/share/licenses/deno %{buildroot}%{pkgs}/share/doc/deno
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} %{buildroot}%{libd}/
cp %{SOURCE3} %{buildroot}%{pkgs}/bin/deno
cp %{SOURCE4} %{buildroot}%{pkgs}/share/deno/db2.ts
cp %{SOURCE5} %{SOURCE6} %{SOURCE7} %{buildroot}%{pkgs}/share/licenses/deno/
cp %{SOURCE8} %{buildroot}%{pkgs}/share/doc/deno/BUILD-INFO
chmod 755 %{buildroot}%{pkgs}/bin/deno %{buildroot}%{libd}/deno
chmod 644 %{buildroot}%{libd}/libpaseat.a %{buildroot}%{libd}/libunwind.a %{buildroot}%{pkgs}/share/deno/db2.ts

%files
%defattr(-,qsys,*none)
%{pkgs}/bin/deno
%dir %{libd}
%{libd}/deno
%{libd}/libpaseat.a
%{libd}/libunwind.a
%dir %{pkgs}/share/deno
%{pkgs}/share/deno/db2.ts
%dir %{pkgs}/share/licenses/deno
%{pkgs}/share/licenses/deno/LICENSE
%{pkgs}/share/licenses/deno/THIRD_PARTY_NOTICES.md
%{pkgs}/share/licenses/deno/THIRD_PARTY_LICENSES.md
%dir %{pkgs}/share/doc/deno
%{pkgs}/share/doc/deno/BUILD-INFO

%changelog
* Tue Nov 10 2026 Sylvain AKTEPE <16803966+Handedge@users.noreply.github.com> - 2.9.8-3
- Same binary as 2.9.8-1; db2.ts: Db2Pool reset "restore" also restores CURRENT PATH, and documents
  what it does not reset (global variables, job environment variables, CHGJOB attributes)

* Tue Nov 10 2026 Sylvain AKTEPE <16803966+Handedge@users.noreply.github.com> - 2.9.8-2
- Same binary as 2.9.8-1; THIRD_PARTY_LICENSES.md states the redistribution terms of the IBM libunwind

* Mon Nov 09 2026 Sylvain AKTEPE <16803966+Handedge@users.noreply.github.com> - 2.9.8-1
- First RPM: Deno 2.9.8 with V8 15.0 for IBM i PASE

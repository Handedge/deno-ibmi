"""Compares Deno unit test results on IBM i against the x64 reference (same version, same runner).

A test case is an IBM i-specific discrepancy only if it passes on x64 and fails on IBM i. A file
that produces no test case (crash, timeout) counts all x64 cases of that file as failed.
Usage: python3 comparer-unit.py <ibmi.jsonl> <x64.jsonl>
"""
import collections
import json
import sys


import re

# Some test case names contain a date generated at run time ("set and get invalid key
# [ 2026-11-03T09:19:52.… ]"): it is masked so that x64 and IBM i cases can be matched.
DATE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z")


def lire(f):
    res = {}
    for r in map(json.loads, filter(str.strip, open(f, encoding="utf-8"))):
        r["cas"] = {DATE.sub("<date>", k): v for k, v in r["cas"].items()}
        res[r["fichier"]] = r
    return res


ibmi, x64 = lire(sys.argv[1]), lire(sys.argv[2])
ref_ok = ibmi_ok = ign = 0
ecarts = collections.defaultdict(list)
for fichier, rx in sorted(x64.items()):
    ri = ibmi.get(fichier, {"cas": {}, "code": "absent", "sortie": ""})
    for cas, ex in rx["cas"].items():
        if ex == "ignored":
            ign += 1
            continue
        if ex != "ok":
            continue                      # already fails on x64: reference environment
        ref_ok += 1
        ei = ri["cas"].get(cas, "absent (fichier code=%s)" % ri["code"])
        if ei == "ok":
            ibmi_ok += 1
        else:
            ecarts[fichier].append((cas, ei))
print(f"cas réussis en x64 : {ref_ok} (+{ign} ignorés par les tests)")
print(f"réussis aussi sur IBM i : {ibmi_ok} = {100 * ibmi_ok / ref_ok:.2f} %")
print(f"écarts : {ref_ok - ibmi_ok} dans {len(ecarts)} fichiers")

# Second metric: cases APPLICABLE to IBM i. The following are removed, and listed by name:
# - cases that the test itself declares not applicable on this OS ("ignored" on IBM i:
#   ignore: Deno.build.os !== "linux", vsock, abstract sockets, /proc…);
# - the GPU (IBM i has none, wgpu does not know AIX) and esbuild (no AIX binary).
HORS_PLATEFORME_FICHIERS = {"webgpu_test", "canvas_test", "bundle_test"}
# Discrepancies caused by IBM i / PASE itself, verified one by one (reason alongside):
HORS_PLATEFORME_CAS = {
    "display GPUTexture": "GPU",
    "utimeSyncFileDateSuccess": "IFS : dates à la seconde (vérifié en C, utimensat)",
    "utimeFileDateSuccess": "IFS : dates à la seconde (vérifié en C, utimensat)",
    "utimeSyncLargeNumberSuccess": "IFS : date > 2^32 s refusée, EINVAL (vérifié en C)",
    "readDirDevFd": "PASE n'a pas /dev/fd",
    "readDirDevFdSync": "PASE n'a pas /dev/fd",
    "netUdpListenEphemeralClose": "plage de ports éphémères d'IBM i (le test attend celle de Linux)",
    "netTcpListenEphemeralClose": "plage de ports éphémères d'IBM i (port tiré au hasard dès 1024)",
    "createHttpClientWithVsockProxy": "vsock : Linux seulement",
    "buildInfo": "la liste d'OS du test ne contient pas aix",
    "nonExistentCwd": "PASE refuse rmdir du répertoire courant d'un processus (EBUSY)",
    "\"Blob\" colorSpaceConversion: \"none\"": "le test lit les u16 en little-endian (même pixel)",
    "imageBitmapFromBlobColorspaceConversion": "étape ci-dessus",
    # AIX flock = fcntl locks: owned by the process (2 descriptors of the same process do not
    # exclude each other) and no exclusive lock on a file opened read-only (EBADF), verified
    "fsFileLockFileSync": "flock d'AIX : exclusif refusé en lecture seule (EBADF)",
    "fsFileLockFileAsync": "flock d'AIX : exclusif refusé en lecture seule (EBADF)",
    "fsFileTryLockSync": "flock d'AIX : verrou propre au processus, pas au descripteur",
    "fsFileTryLockAsync": "flock d'AIX : verrou propre au processus, pas au descripteur",
    "fsFileTryLockSharedSync": "flock d'AIX : verrou propre au processus, pas au descripteur",
}
# Discrepancies still COUNTED, but caused by the test bench, not by Deno (fixable by configuration):
ENVIRONNEMENT = {
    "hostnameDir": "nom d'hôte TCP/IP de IBMI non configuré (CFGTCP 12 : UNKNOWN)",
    "hostnameWithoutOtherNetworkUsages": "nom d'hôte TCP/IP de IBMI non configuré",
    "getGid": "tests lancés sous un profil *ALLOBJ, sans groupe (gid 0) ; x64 : utilisateur ordinaire",
    "chownSyncPermissionDenied": "tests lancés sous un profil *ALLOBJ (*ALLOBJ, équivalent root)",
    "chownPermissionDenied": "tests lancés sous un profil *ALLOBJ (*ALLOBJ, équivalent root)",
    "httpServeCurlH2C": "curl de PASE compilé sans HTTP/2",
    "httpsServeCurlH2C": "curl de PASE compilé sans HTTP/2",
    "inspectLargeArrayBuffer": "ArrayBuffer de 4 Go : plafond ulimit -d 8 Go de sécurité ASP",
    "tlsHandshakeWithTcpCorruptionImmediately": "instable (2 réussites sur 5, avec et sans correctifs)",
}
hors_detail = [(f, cas, e) for f, l in ecarts.items() for cas, e in l
               if e == "ignored" or f in HORS_PLATEFORME_FICHIERS
               or cas.split(" > ")[-1] in HORS_PLATEFORME_CAS]
hors = len(hors_detail)
applicables = ref_ok - hors
print(f"hors plateforme (ignorés par le test sur AIX, GPU, esbuild) : {hors}")
for f, cas, e in hors_detail:
    nom = cas.split(" > ")[-1]
    if e != "ignored" and f not in HORS_PLATEFORME_FICHIERS:
        print(f"   - {f} > {nom[:50]} : {HORS_PLATEFORME_CAS[nom]}")
print(f"cas applicables à IBM i : {applicables}, réussis : {ibmi_ok} = {100 * ibmi_ok / applicables:.2f} %"
      f" ({applicables - ibmi_ok} écarts)")
restants = [(f, cas.split(" > ")[-1]) for f, l in ecarts.items() for cas, e in l
            if (f, cas, e) not in hors_detail]
env = [(f, n) for f, n in restants if n in ENVIRONNEMENT]
print(f"   dont environnement du banc de test : {len(env)}")
for f, n in env:
    print(f"   - {f} > {n[:50]} : {ENVIRONNEMENT[n]}")
print(f"   dont propres à Deno sur IBM i : {len(restants) - len(env)}")
for f, n in restants:
    if n not in ENVIRONNEMENT:
        print(f"   - {f} > {n[:60]}")
for fichier, l in sorted(ecarts.items(), key=lambda x: -len(x[1])):
    print(f"\n## {fichier} : {len(l)} écart(s), code IBM i = {ibmi.get(fichier, {}).get('code')}")
    for cas, e in l[:8]:
        print(f"   {cas[:70]:70} {e[:110]!r}")
    if len(l) > 8:
        print(f"   … et {len(l) - 8} autres")

# Tests officiels de Deno sur IBM i

Tests unitaires de Deno 2.9.8 (`tests/unit/*_test.ts`, 104 fichiers), lancés comme le fait
`tests/unit/mod.rs`, sur IBM i et sur un Deno 2.9.8 x64 officiel (référence). Un écart
propre à IBM i est un cas qui réussit en x64 et échoue sur IBM i.

## Préparation (LINUXBUILD)
```
git clone --depth 1 --branch v2.9.8 https://github.com/denoland/deno ~/denogit
cd ~/denogit && git submodule update --init --depth 1 tests/util/std
# Deno x64 de référence : release v2.9.8 deno-x86_64-unknown-linux-gnu.zip dans ~/denoref
python3 preparer-test-server.py /QOpenSys/opt/denoibmi/deno
source ~/deno-ibmi/linux/croise/env-croise.sh && cd /QOpenSys/opt/denoibmi/deno
cargo +1.99.1 build -p test_server --release                       # x64
cargo +1.99.1 build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix \
  --profile ibmi-rel -p test_server                                # IBM i (lien rejoué)
```
Sur IBM i : `BINAIRE=test_server PROFIL=ibmi-rel` pour `ibmi/rejouer-lien.sh` (en SBMJOB).
Arbre de test : `~/denogit` sans `.git`, `target`, `tests/{wpt,node_compat,bench,specs}`
→ `/QOpenSys/opt/denoibmi/denotests`, `test_server` dans `target/aix/` (le serveur déduit
la racine du dépôt de son propre chemin : `<racine>/target/<x>/test_server`).

## Lancement
```
python3 unit.py <racine> <deno> <test_server> <sortie.jsonl> [parallélisme] [filtre]
python3 comparer-unit.py ibmi.jsonl x64.jsonl
```
Le test_server n'écoute que sur 127.0.0.1 et ::1.

## Profil de test ordinaire (05/11/2026)

La référence x64 tourne sous un utilisateur ordinaire : sur IBM i, les tests tournent donc sous
`DENOTEST` (USRCLS *USER, SPCAUT *NONE, PASSWORD *NONE), du groupe `DENOTSTG` (GID 104), qui a
`*RWX` sur `/QOpenSys/opt/denoibmi/denotests` (CHGAUT SUBTREE(*ALL)). Sous un profil *ALLOBJ (
équivalent root), `chown*PermissionDenied` et `getGid` échouaient. Lancement :

    SBMJOB CMD(QSH CMD('NOM=passe9 /QOpenSys/usr/bin/sh /tmp/rustpoc/unit-denotest.sh'))
           JOB(PASSE9) USER(DENOTEST) INLLIBL(*JOBD) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)

Nom d'hôte TCP/IP de IBMI fixé le 05/11 (`CHGTCPDMN HOSTNAME('IBMI') DMNNAME('example.com')` ;
il valait UNKNOWN, `Deno.hostname()` rendait "").

Passe 9 : 97,08 % brut, **99,87 % des cas applicables** (3 écarts : curl de PASE sans HTTP/2,
ArrayBuffer de 4 Go sous le plafond `ulimit -d` de 8 Go).

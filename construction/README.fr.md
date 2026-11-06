# Reconstruire Deno pour IBM i

Ce guide permet à quelqu'un qui n'a jamais participé au chantier de **reconstruire Deno pour IBM i, de le
tester et de le mettre en service**, sans connaissance orale. Tout part du dépôt `deno-ibmi`.

Résultat : un paquet `deno-ibmi-<version>-<date>` sur IBMI (binaire `deno` pour IBM i PASE, `libpaseat.a`,
fiche INFO, empreintes SHA-256), **testé** (≥ 99,5 % des tests unitaires officiels de Deno applicables,
0 écart propre à Deno), prêt à installer.

## En bref

```bash
# sur LINUXBUILD, compte de construction, dans le dépôt deno-ibmi
bash construction/verifier-prerequis.sh        # rien n'est modifié ; doit finir par « PRÊT »
bash construction/construire.sh                # ≈ 18 min (clone neuf) ; Deno 2.9.8 par défaut
```
```sh
# sur IBMI, par un ADMINISTRATEUR (décision humaine), session ssh ou QP2TERM
sh /QOpenSys/opt/deno-ibmi/ibmi/livrer.sh --verifier deno-ibmi-2.9.8-AAAAMMJJ-HHMM   # contrôle seul
sh /QOpenSys/opt/deno-ibmi/ibmi/livrer.sh deno-ibmi-2.9.8-AAAAMMJJ-HHMM              # mise en service
sh /QOpenSys/opt/deno-ibmi/ibmi/livrer.sh --retour                                   # en cas de souci
```

La construction est **automatique** ; la **mise en service ne l'est pas**, elle reste décidée par un
administrateur.

## Qui fait quoi

| Machine / profil | Rôle |
|---|---|
| **LINUXBUILD** (Ubuntu, 28 cœurs, compte de construction) | compile tout en croisé (`powerpc64-ibm-aix`) : Rust, V8, Deno ; pilote la construction |
| **IBMI** (IBM i 7.5, `192.0.2.82`) | édition de liens (le lieur d'AIX n'existe pas sous Linux), fabrication du snapshot par le V8 d'IBM i, tests, livraison |
| profil **DENOBUILD** (IBMI) | utilisé par LINUXBUILD en ssh ; sans droits spéciaux, sans mot de passe ; clé `~/.ssh/id_denobuild` acceptée **seulement depuis l'adresse de LINUXBUILD** |
| profil **DENOTEST** (IBMI) | exécute les tests unitaires (utilisateur ordinaire, comme la référence x64) |
| profil **DENOAPP** (IBMI) | fait tourner les services en production (sous-système `DENOIBMI/DENOWS`) |
| administrateur IBM i (ex. QSECOFR) | installe un paquet (`livrer.sh`) |

Pourquoi IBM i intervient pendant la construction : le lien des binaires XCOFF demande le `ld` d'AIX de
PASE, et le snapshot de démarrage de Deno doit être produit par un V8 **big-endian**, donc sur IBM i.

## 1. Avant de commencer

`bash construction/verifier-prerequis.sh` contrôle tout et dit, pour chaque manque, quoi faire. Il
ne demande aucun mot de passe et ne modifie rien. Ce qu'il vérifie :

- **LINUXBUILD** : rustup, Rust 1.99.1 avec `rust-src` **retouché pour AIX** (`preparer-rust.sh` le fait,
  `construire.sh` le relance à chaque fois) ; V8 compilé pour AIX dans `~/v8aix` (voir § 6) ;
  `/QOpenSys/opt/denoibmi` **vrai dossier** (pas un lien) accessible en écriture ; ≥ 20 Go libres ;
  référence x64 des tests ; objets assemblés sur IBM i (`construction/objets-ibmi`).
- **IBMI** : accès ssh DENOBUILD sans mot de passe, shell `sh`, dossiers accessibles en écriture,
  runtime Rust et `libpaseat.a`, jeu de tests et `test_server`, ASP < 75 %, profil DENOTEST.

Le dépôt sur LINUXBUILD doit garder les **modes exécutables** des scripts (un `git clone` le fait ; une
copie par `git archive` ou `tar` aussi ; une copie par le poste Windows non : alors
`chmod +x construction/*.sh linux/croise/*.sh linux/croise/cc-aix`).

## 2. Construire

```bash
bash construction/construire.sh                     # tests complets (par défaut)
bash construction/construire.sh --tests rapide      # sans les tests unitaires : pas de paquet produit
VERSION_DENO=v2.10.0 bash construction/construire.sh   # autre version de Deno (voir § 4)
```

Journal : `~/construction-deno/construire-AAAAMMJJ-HHMM.log` (tout ce qui s'affiche). Lancement détaché
conseillé (la session ssh peut tomber sans conséquence) :
`setsid nohup bash construction/construire.sh > ~/construction-deno/lancement.log 2>&1 < /dev/null &`

| Étape | Ce qui se passe | Durée (clone neuf) |
|---|---|---|
| 0. garde-fous | IBMI joignable, ASP < 75 % (sinon arrêt) | 2 s |
| 1. arbre | Rust figé ; clone de Deno dans `/QOpenSys/opt/denoibmi/deno` ; crates à corriger téléchargées ; Cargo.toml et Cargo.lock IBM i ; **tous les correctifs AIX/PASE** (`ibmi/correctifs.py`) | 1 min |
| 2. dépôt sur IBMI | scripts du dépôt (`/QOpenSys/opt/deno-ibmi`) et sources JS de Deno | 5 s |
| 3. générateur de snapshot | compilé sur LINUXBUILD, **lié sur IBMI** (SBMJOB `LIEN`) | 4 min |
| 4. snapshot | fabriqué sur IBMI par le V8 d'IBM i, rapatrié | 10 s |
| 5. Deno | compilé sur LINUXBUILD avec ce snapshot, **lié sur IBMI** | 8 min |
| 6. test rapide | `--version`, `eval`, format `fr-FR`, `node:crypto` | 2 s |
| 7. tests complets | tests unitaires officiels sous DENOTEST (SBMJOB `TESTSDENO`), comparés à la référence x64 ; **seuil bloquant** ≥ 99,5 % des cas applicables et 0 écart propre à Deno | 6 min |
| 8. paquet | `/QOpenSys/opt/denoibmi/livraisons/deno-ibmi-<version>-<date>/` ; les 3 plus récents sont gardés | 5 s |

Une reconstruction sur un arbre déjà compilé ne recompile que ce qui a changé (quelques minutes).

Le binaire de l'étape 5 est aussi laissé dans `/QOpenSys/opt/denoibmi/croise/deno` : il n'est **pas** en
service (les services utilisent `/QOpenSys/opt/denoibmi/bin/deno`).

## 3. Mettre en service (administrateur IBM i)

`ibmi/livrer.sh` (sur IBMI : `/QOpenSys/opt/deno-ibmi/ibmi/livrer.sh`) :

1. vérifie les empreintes SHA-256 du paquet et exécute le binaire (`--version`, `eval`) ;
2. garde la version en service (`bin/ACTUELLE` → `bin/PRECEDENTE`), installe la nouvelle atomiquement,
   remplace `libpaseat.a` seulement si elle diffère (copie de secours datée) ;
3. arrête proprement l'API (SIGTERM), DENOWS et la veille, attend l'arrêt complet du sous-système,
   le redémarre (`STRSBS DENOIBMI/DENOWS` : les 3 travaux automatiques DENOWS, DENOVEILLE, DENOAPI) ;
4. contrôle que `http://127.0.0.1:3081/bonjour`, `https://127.0.0.1:3444/bonjour` et
   `https://127.0.0.1:3091/api/sante` répondent 200 en moins de 60 s ;
5. sinon **revient tout seul** à la version précédente.

Coupure de service : ≈ 30 s. `--retour` revient à la version précédente à tout moment.

## 4. Monter de version de Deno

1. **Bilan des correctifs** sur un clone de la nouvelle version (sans toucher à l'arbre en service) :
   ```bash
   git clone --depth 1 --branch v2.X.Y https://github.com/denoland/deno /tmp/deno-neuf
   mkdir -p /tmp/bilan && CORRECTIFS_BILAN=1 DENO_ARBRE=/tmp/deno-neuf \
     python3 ibmi/correctifs.py /QOpenSys/opt/denoibmi/crates-src /tmp/bilan
   ```
   La dernière ligne donne le nombre de correctifs qui ne s'appliquent plus ; les adapter dans
   `ibmi/correctifs.py` (ils doivent rester valables pour l'ancienne version aussi).
2. **Version de V8** : `grep '^v8 = ' /tmp/deno-neuf/Cargo.toml`. Si elle n'est plus `150.4.0`, il faut
   reconstruire V8 pour AIX (§ 6) avant tout.
3. **Crates** : `preparer-arbre.sh` part du Cargo.lock de la nouvelle version et y applique nos montées de
   version (sans jamais descendre) ; il affiche ensuite les crates corrigées qui changent de version par
   rapport à la production (`comparer-crates.py`). Une crate corrigée qui change : ajouter la nouvelle
   version à la liste de l'étape 4 de `preparer-arbre.sh` et adapter `correctifs.py` /
   `deno/Cargo.toml.ibmi`.
4. **Arbre** : `construire.sh` refuse un arbre d'une autre version. Mettre l'ancien de côté
   (`mv /QOpenSys/opt/denoibmi/deno /QOpenSys/opt/denoibmi/deno-2.9.8`), puis
   `VERSION_DENO=v2.X.Y bash construction/construire.sh`.

Essai fait le 06/11/2026 sur `main` de Deno (commit e7b39ebd) : 1 correctif adapté, 18 min, 99,87 %.

**Limite connue** : les tests unitaires lancés sur IBMI (`/QOpenSys/opt/denoibmi/denotests`, avec son
`test_server`) et la référence x64 (`tests-deno/resultats-x64.jsonl`) sont ceux de **2.9.8**. Pour valider
une nouvelle version avec ses propres tests, les refaire comme décrit dans `tests-deno/README.md`.

## 5. Dépannage

| Symptôme | Cause | Remède |
|---|---|---|
| `ASP à NN % : construction refusée` | garde-fou (75 %) | faire de la place sur IBMI (`/tmp/rustpoc`, anciens paquets) |
| `Permission denied` sur `emballer-lien.sh` ou `cc-aix` | copie du dépôt sans les modes exécutables | `chmod +x` (§ 1) |
| `L'arbre … est en X, pas en Y` | arbre d'une autre version | § 4, point 4 |
| `error[E0609]: no field sa_union` (signal-hook-registry) ou autre erreur de compilation dans une crate | version de crate sans support AIX | monter la crate (liste de `preparer-arbre.sh`) ou ajouter un correctif |
| `macros.rs : N occurrences au lieu de 7` | autre version de Rust | garder `RUST_VERSION=1.99.1` ou adapter `preparer-rust.sh` |
| `lien de deno : rc=1` | lien refusé sur IBMI | `/tmp/rustpoc/rejouer-lien.log` et `/QOpenSys/opt/denoibmi/croise/lien.txt` (sur IBMI) |
| `0711-407 … .rint` au lien | `rust-src` non retouché | `bash construction/preparer-rust.sh` |
| étape 7 sans fin, test_server bloqué | tests soumis par `QSH CMD` (travail sans fils d'exécution) | toujours `CALL QP2SHELL` (c'est ce que fait le script) |
| `export: … not an identifier` en ssh | shell `bsh` du profil | `CALL QSYS2.SET_PASE_SHELL_INFO('DENOBUILD', '/QOpenSys/usr/bin/sh')` |
| `SEUIL NON ATTEINT` | régression réelle ou test instable | lire `~/construction-deno/construire-HHMM.txt` (écarts listés) ; relancer une fois avant de conclure |
| `livrer.sh` : `STRSBS` refusé CPF1010 | sous-système pas encore arrêté | corrigé (attente) ; le retour automatique protège |

## 6. Ce qui n'est pas automatisé (et quand y toucher)

| Élément | Où | Quand le refaire | Comment |
|---|---|---|---|
| **V8 pour AIX** (`librusty_v8.a`, `src_binding_aix.rs`, `icudtb.dat`) | LINUXBUILD `~/v8aix` | changement de version de V8 (crate `v8`) | `v8aix/README.md` ; aller-retour sur IBM i manuel (mksnapshot) |
| Objets assemblés sur IBM i (`libffi.a`, `libz.a`, `powerpc64_aix.o`) | `construction/objets-ibmi` | changement de version de libffi-sys, libz-sys ou psm | `construction/objets-ibmi/README.md` |
| Liaisons bindgen (sqlite, aws-lc, nghttp2, libuv) | `liaisons/` | changement de version de ces crates | `linux/generer_liaisons.sh` |
| Jeu de tests et `test_server` sur IBMI, référence x64 | `/QOpenSys/opt/denoibmi/denotests`, `tests-deno/` | nouvelle version de Deno à valider avec ses propres tests | `tests-deno/README.md` |
| Mise en place de IBMI (une fois) | IBMI | nouvelle machine | § 7 |

## 7. Mise en place sur une nouvelle machine IBM i (une fois)

Fait sur IBMI le 05-06/11/2026 ; à refaire seulement pour une autre machine.

- Rust sous PASE (`/QOpenSys/opt/rust`, runtime Open XL, `libpaseat.a` thread-safe) : `README.md` du dépôt
  (« Installation de Rust sous PASE ») et `ibmi/paseat/construire.sh`.
- Profil **DENOBUILD** : `USRCLS(*USER) SPCAUT(*NONE) PASSWORD(*NONE)`, shell `sh`
  (`QSYS2.SET_PASE_SHELL_INFO`), `~/.ssh/authorized_keys` avec la clé publique de LINUXBUILD préfixée de
  `from="<adresse de LINUXBUILD>",no-port-forwarding,no-agent-forwarding,no-X11-forwarding`. Propriétaire
  de `/QOpenSys/opt/denoibmi/{croise,deno,livraisons}` et `/QOpenSys/opt/deno-ibmi` ; `*USE` sur le profil
  DENOTEST (pour soumettre les tests sous ce profil).
- Profil **DENOTEST** : `*USER`, `*NONE`, groupe `DENOTSTG`, `*RWX` sur `/QOpenSys/opt/denoibmi/denotests`.
- Services : `essais/deno-ws/sous-systeme.md` (sous-système DENOWS, profil DENOAPP, démarrage à l'IPL).

## Règles à respecter sur IBMI

- Ne jamais lancer de test ou de service avec `ulimit -d unlimited` (seul le lien le fait) : un processus
  emballé a déjà rempli l'ASP (incident du 03/11/2026). Garde-fou d'arrêt à 80 % pendant les tests.
- Pas de `dbx64` attaché à un Deno en cours d'exécution.
- Au plus 4 processus de test en parallèle.
- Aucun service Deno exposé au-delà du réseau interne.

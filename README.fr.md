# deno-ibmi : Rust et Deno sur IBM i

Faire tourner **Deno** (runtime JavaScript/TypeScript écrit en Rust) sur **IBM i 7.5**, dans PASE, et lui faire servir des webservices. À notre connaissance, une première.

Projet personnel et non officiel de Sylvain AKTEPE : ni Deno Land Inc. ni IBM ne sont associés à ce dépôt.

> ⚠️ **Avant tout un projet ludique.** C'est une expérience menée pour le plaisir de la voir marcher, pas
> un produit. Elle est fournie **sans garantie, sans support et sans aucune responsabilité** : vous
> l'utilisez entièrement à vos risques, et l'auteur décline toute responsabilité pour tout dommage,
> perte de données, arrêt ou autre conséquence. Ne la faites pas tourner sur un système de production
> sans l'avoir relue et testée vous-même. Les droits des tiers (marques, licences, logiciels IBM) sont
> listés dans l'[Avertissement](#avertissement) et dans [THIRD_PARTY_NOTICES.fr.md](THIRD_PARTY_NOTICES.fr.md).

> **Reconstruire Deno pour IBM i : [`build/README.md`](build/README.fr.md)** (une commande sur
> LINUXBUILD, tests et paquet de livraison compris ; mise en service par `ibmi/deploy.sh`).

## Installer avec yum

Deno est disponible en RPM signé dans un dépôt yum tiers, comme les paquets open source d'IBM i.
Prérequis : **IBM i 7.5 ou plus récent**, POWER8 ou plus récent, l'environnement yum d'IBM
(`/QOpenSys/pkgs/bin` dans le `PATH`). En administrateur, en ssh ou sous QP2TERM :

```
curl -o /QOpenSys/etc/yum/repos.d/deno-ibmi.repo https://yum.job-i.fr/deno-ibmi/deno-ibmi.repo
yum install deno
```

À la première installation, yum demande d'accepter la clé de signature
(`RPM-GPG-KEY-deno-ibmi`, Sylvain AKTEPE, empreinte `8182 36E7 94FB B0BF D6DE  D98C 003F 3EDC D33E 3056`).
Ensuite :

```
deno --version
deno eval "console.log(Deno.build.os, Deno.build.arch)"     # aix powerpc64
```

| Installé | Chemin |
|---|---|
| commande `deno` | `/QOpenSys/pkgs/bin/deno` (lanceur : `XPG_SUS_ENV=ON` et `DENO_NO_UPDATE_CHECK=1` par défaut) |
| binaire et bibliothèques d'exécution | `/QOpenSys/pkgs/lib/deno/` (`deno`, `libpaseat.a`, `libunwind.a` d'IBM) |
| module Db2 for i | `/QOpenSys/pkgs/share/deno/db2.ts` (`import { Db2 } from "/QOpenSys/pkgs/share/deno/db2.ts"`, lancer avec `--allow-ffi`) |
| licences | `/QOpenSys/pkgs/share/licenses/deno/` |

Mise à jour : `yum upgrade deno` ; désinstallation : `yum remove deno`. IBM i 7.3 n'est pas pris en charge
(sa libc PASE n'a pas des fonctions dont le binaire a besoin) et la 7.4 n'est pas testée ; rpm refuse le
paquet en dessous de la 7.5.

## État (06/11/2026)

- **Deno 2.9.8 sur moteur V8** (compilé en croisé sur LINUXBUILD, lié sur IBM i) en service sur IBMI
  depuis le 06/11 : sous-système `DENOIBMI/DENOWS` (webservice, veille, API CRUD Db2), démarrage à l'IPL.
- Tests unitaires officiels de Deno : **99,87 % des cas applicables, 0 écart propre à Deno** ; endurance
  48 h : 1,7 million de requêtes, 0 erreur.
- Construction reproductible en une commande depuis un clone neuf (18 min), essayée aussi sur `main`
  de Deno (prochaine version) avec le même score.

Historique des jalons du portage QuickJS (29/10/2026), conservé pour mémoire :

| Jalon | État |
|---|---|
| rustc / cargo 1.96 sous PASE (SDK Rust AIX d'IBM, Community Edition) | fait |
| Programme Rust (threads, panique, IFS) | fait |
| Webservice Rust axum + tokio servi par IBM i | fait (HTTP 200, 40 ms) |
| Toutes les crates de Deno 2.9.8 (moteur QuickJS) compilent | fait |
| Édition de liens du binaire `deno` | fait (profil `ibmi-o1`, 493 Mo) |
| `deno --version`, `deno eval`, `deno run` d'un `.ts` | fait (29/10, 17 h 52) |
| `Deno.serve()` sur IBM i, appelé depuis un poste | fait (29/10, 18 h 23 : HTTP 200, ~40 ms, 200/200) |
| `fetch()` sortant HTTPS, certificat vérifié | fait (30/10) |
| `Deno.serve()` avec gestionnaire asynchrone (minuteur, fichier, fetch) | fait (30/10, correctif mio) |
| Accès Db2 for i (`examples/deno-db2/db2.ts`, FFI sur la CLI `libdb400`) | fait (30/10 : 0,5 ms par requête préparée, UTF-8, LOB, erreurs SQLSTATE) |
| Webservice Deno lisant Db2, appelé depuis un poste | fait (30/10, routes `/db2/*`) |
| HTTPS natif de Deno (rustls, TLS 1.3) sur 3444 | fait (30/10, autorité locale deno-ibmi) |
| HTTPS par Apache (instance DENOWS, reverse proxy 3443) | configuré ; attend le certificat dans le DCM |
| WebAssembly (wasmi à la place de WAMR) | à faire |
| Moteur V8 | à faire |

Machine de travail : IBMI (Power S922, IBM i 7.5, 2 cœurs, 64 Go).

## Organisation du dépôt

| Répertoire | Contenu |
|---|---|
| `ibmi/rustenv.sh` | environnement Rust sous PASE (à sourcer) |
| `ibmi/paseat/` | **libpaseat** : couche de compatibilité PASE (voir plus bas) |
| `ibmi/patches.py` | rejoue tous les correctifs (crates et sources de Deno) |
| `ibmi/build-deno.sh` | construction de Deno (soumise en batch) |
| `bindings/` | liaisons bindgen pré-générées pour `powerpc64-ibm-aix` |
| `linux/generate_bindings.sh` | génération de ces liaisons sur Linux |
| `tools/` | extracteur d'images installp (BFF), réécriture des imports XCOFF, WAMR factice |
| `workstation/` | aides côté poste Windows (envoi et rapatriement de fichiers via Mapepire) |
| `examples/` | webservice Rust, webservice Deno (`examples/deno-ws`), diagnostics PASE |

## Installation de Rust sous PASE (résumé)

1. RPM AIX 7.2 de l'**IBM Open SDK for Rust on AIX** (AIX Toolbox, `RPMS/ppc-7.2/rust/`, Community Edition gratuite) extraits dans `/QOpenSys/opt/rust/1.96`, sans passer par la base rpm d'IBM i.
2. **Runtime IBM Open XL C/C++ 17.1.4.2** (Fix Central) : `libc++`, `libc++abi`, `libunwind`, `libcompiler_rt` extraits des images installp par `tools/bff_extract.py`, copiés dans `/QOpenSys/opt/rust/runtime` (jamais dans `/QOpenSys/usr/lib`).
3. `libz`, `libatomic` de yum réemballés au format attendu (`archive.a(lib.so.N)`).
4. `.cargo.orig` : table d'imports réécrite (`tools/xcoff_imports.py`) pour utiliser l'OpenSSL de yum (évite deux instances de libcrypto).
5. Certificats : bundle construit depuis `/QOpenSys/var/lib/ca-certificates/openssl` (le `cert.pem` de IBMI était vide).
6. `libpaseat` : `ibmi/paseat/build.sh`.

Toujours lancer les travaux par `SBMJOB CMD(CALL PGM(QP2SHELL) ...) ALWMLTTHD(*YES)` : sous QSH, la résolution DNS échoue (`getaddrinfo() thread failed to start`).

## libpaseat : ce que PASE ne fait pas comme AIX

| Constat sous PASE (IBM i 7.5) | Effet | Correction |
|---|---|---|
| `openat`, `fstatat`, `unlinkat`… : EINVAL dès que le répertoire n'est pas `AT_FDCWD` | `std::fs::remove_dir_all` cassé | émulation par chemin absolu |
| `open(O_DIRECTORY)` réussit sur un fichier ordinaire | parcours de répertoires faux | ENOTDIR rétabli |
| `fcntl(F_DUPFD_CLOEXEC)` : EINVAL | `try_clone`, pilote de signaux de tokio | émulé par `F_DUPFD` + `FD_CLOEXEC` |

libpaseat est liée avant libc (`RUSTFLAGS -l paseat`) : l'éditeur de liens AIX rattache alors ces symboles à elle.

## Portage de Deno : nature des correctifs

- **Crate `libc` incomplète pour AIX** : `getifaddrs`, `dladdr`, `SOCK_CLOEXEC`, `in6_pktinfo`, types `caddr_t` et `socklen_t`… (nix, netif, quinn-udp, dlopen2, memmap2, rustix, rustyline, libsui).
- **ABI AIX** : `f64` aligné sur 4 octets (byteorder), constantes libffi (`FFI_AIX`, trampoline de 24 octets).
- **En-têtes AIX** : `<sys/timer.h>` définit `func_data` (QuickJS), pas de `tm_gmtoff`, `SIZE_MAX` masqué (zlib-ng).
- **Pas de libclang sur IBM i** : liaisons générées sur Linux (`linux/`), réinjectées par variables `*_BINDINGS_FILE`.
- **Assembleur** : sources `linux-ppc64le` (ELF) inutilisables ; aws-lc en C portable (`AWS_LC_SYS_NO_ASM=1`).
- **Deno lui-même** : branches AIX (errno, signaux, umask, informations système, DNS, fs, napi) et **un bogue big-endian** (`buffer.rs`, jamais compilé auparavant).
- **WebAssembly** : WAMR suppose une machine little-endian (accès mémoire natifs) et ne connaît ni AIX ni PowerPC ; remplacé par une bibliothèque factice en attendant wasmi.

## HTTPS

Deux voies, comme pour Node.js :

- **Native** : `Deno.serve({ port: 3444, cert, key })` (rustls, TLS 1.3, `TLS_AES_256_GCM_SHA384`, TLS 1.1 refusé). Certificat créé par `examples/deno-ws/apache/create-certificate.sh` dans `/QOpenSys/opt/denoibmi/tls` : autorité locale « deno-ibmi CA locale » (10 ans) et certificat `CN=ibmi` avec SAN `ibmi`, `localhost`, `192.0.2.82`, `127.0.0.1` (2 ans). Clé lisible par `DENOAPP` seul. Côté poste, faire confiance à `ca.crt` (curl de Windows : `--ssl-no-revoke`, l'autorité privée n'a pas de liste de révocation).
- **Apache** (instance `DENOWS`, `examples/deno-ws/apache/httpd.conf`, même modèle que NODEWS) : TLS sur `*:3443` par l'ID d'application DCM `QIBM_HTTP_SERVER_DENOWS`, relais vers `127.0.0.1:3081`. `httpd.conf` doit être marqué CCSID 1208 (`CHGATR ... ATR(*CCSID) VALUE(1208)`), sinon Apache le lit en EBCDIC. Le certificat s'attribue dans le DCM (pas de voie scriptable) ; sans certificat, les travaux de l'instance avortent (HTP8351) : ne pas la laisser démarrée.

## Db2 for i depuis Deno

`examples/deno-db2/db2.ts` : module TypeScript sans code natif, qui appelle la CLI SQL de PASE (`libdb400.a(shr_64.o)`) par `Deno.dlopen`, comme le fait en C++ idb-connector, le pilote Node.js d'IBM (CLI en UTF-8 par `SQLOverrideCCSID400(1208)`, mode serveur, colonnes lues en caractères puis converties).

```ts
import { Db2 } from "./db2.ts";
const db = new Db2();                      // *LOCAL, profil du travail ; options : user, password, library, systemNaming
const rows = db.query("SELECT * FROM QSYS2.SYSTABLES WHERE TABLE_SCHEMA = ?", ["QSYS2"]);
db.execute("UPDATE ... WHERE ID = ?", [42]);   // { rows, rowsAffected } : lignes et nombre de lignes touchées
```

Version non bloquante et pool de connexions (l'exécution SQL tourne dans un thread de Deno, la boucle d'événements continue de servir) :

```ts
import { Db2Pool } from "./db2.ts";
const pool = new Db2Pool(4);               // 4 connexions, 4 travaux QSQSRVR
const rows = await pool.query("SELECT ... WHERE X = ?", [x]);
await pool.withConnection(async (db) => { await db.executeAsync("UPDATE ..."); db.commit(); });  // transaction
```

Mesuré sur IBMI : 4 requêtes d'1 s (DLYJOB) en parallèle en 1,04 s ; 50 requêtes concurrentes justes en 29 ms.

**Connexions du pool et état du travail.** Chaque connexion fonctionne en mode serveur, donc dans son propre travail QSQSRVR, sous le profil avec lequel elle a été ouverte (celui du travail si aucun utilisateur n'est donné). Ce travail est réutilisé par la requête suivante : tout ce qu'une requête y modifie (liste de bibliothèques, schéma courant, objets de QTEMP comme les tables temporaires globales déclarées, travail non validé) serait hérité par la suivante. L'option `reset` de `Db2Pool` fixe ce qui se passe quand une connexion revient dans le pool :

| `reset` | Effet |
|---|---|
| `"restore"` (par défaut) | annule le travail non validé, rétablit le schéma courant, le chemin SQL (`CURRENT PATH`) et la liste de bibliothèques d'origine, vide QTEMP ; en cas d'échec, la connexion est jetée |
| `"discard"` | ferme la connexion ; la requête suivante en reçoit une neuve |
| `"none"` | rien n'est réinitialisé : seulement avec des noms entièrement qualifiés et aucune instruction qui modifie l'état du travail |

`"restore"` ne couvre que ce qui est listé ci-dessus. **Les valeurs des variables globales** (`SET MABIB.MAVAR = ...`), **les variables d'environnement du travail** (`ADDENVVAR ... LEVEL(*JOB)`) et **les attributs du travail modifiés par `CHGJOB`** (`DATFMT`, etc.) n'ont pas de remise à zéro simple et restent visibles pour la requête suivante : si des requêtes en modifient, choisir `"discard"`.

La remise à zéro se fait après le renvoi du résultat : elle n'ajoute pas de délai à la requête. `examples/deno-db2/test-pool-isolation.ts` reproduit la fuite avec `"none"` (bibliothèque ajoutée, `SET SCHEMA`, `SET PATH`, table QTEMP, variable globale, variable d'environnement, `CHGJOB DATFMT` encore présents à la requête suivante), montre que `"restore"` supprime les quatre premiers mais pas les trois derniers, et que `"discard"` les supprime tous (vérifié sur IBM i 7.5, le 10/11/2026).

**Noms non qualifiés en nommage système.** Dès qu'un schéma par défaut est fixé, par `SET SCHEMA` ou par l'option `library` (attribut de connexion `SQL_ATTR_DBC_DEFAULT_LIB`), les tables non qualifiées sont cherchées dans ce schéma et **plus à travers `*LIBL`**, même si une autre bibliothèque contenant la même table est placée avant dans la liste, ou si la bibliothèque du schéma n'est même pas dans la liste. « Schéma par défaut » et « nommage système + CHGLIBL » sont donc deux alternatives, pas des options à combiner. Règle la plus simple pour les connexions d'un pool : des noms entièrement qualifiés.

Lancer avec `--allow-ffi`. Types : entiers, DOUBLE et DECIMAL jusqu'à 15 chiffres en nombres ; BIGINT au-delà de 2^53 et grands DECIMAL en chaînes ; CHAR sans blancs de fin ; dates et heures ISO ; BLOB/BINARY en `Uint8Array`. `query`/`execute` sont synchrones, `queryAsync`/`executeAsync` et `Db2Pool` non bloquants ; options de `Db2` : `user` (profil), `password` (mot de passe), `library` (schéma par défaut), `systemNaming` (nommage *SYS), `database`, `autocommit` ; `pool.stats` rend `{ size, open, idle, waiting }`.

## Lancer le webservice Deno

Sous un profil dédié sans droits spéciaux (`DENOAPP` : `*USER`, `PASSWORD(*NONE)`, `LMTCPB(*YES)`). Le binaire, `serveur.ts`, `ws.sh` et `db2.ts` sont en `*PUBLIC *RX` (le service ne peut pas modifier son propre code, vérifié par `examples/deno-ws/check-authorities.sh`) ; seuls `ws/logs` et `ws/cache` appartiennent à `DENOAPP`.

```
SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/sh' '/QOpenSys/opt/denoibmi/ws/ws.sh'))
       JOB(DENOWS) USER(DENOAPP) INLLIBL(*JOBD) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)
```

`INLLIBL(*JOBD)` : sinon la liste de bibliothèques du demandeur est recopiée (CPF1266 si le profil n'y a pas droit).

`ws.sh` (dans `examples/deno-ws`) positionne `DENO_NO_UPDATE_CHECK=1` : sans elle, la vérification de mise à jour de `deno run` (fetch HTTPS sortant) fait avorter le processus.

## Limites actuelles

Vérifiées sur la version V8 le 06/11/2026 :

- `Deno.resolveDns` échoue (pas de `/etc/resolv.conf` sous PASE) ; la résolution ordinaire (`fetch`, `Deno.connect`) fonctionne.
- `Deno.loadavg()` renvoie `0,0,0` (non fourni par PASE).
- `Deno.networkInterfaces()` : interfaces nommées par leur adresse IP, sans adresse MAC.
- `deno compile` inutilisable (pas de section embarquée en XCOFF).
- WAMR remplacé par une bibliothèque factice ; l'API `WebAssembly` standard, fournie par V8, fonctionne.

Fonctionnent (vérifié) : `WebAssembly`, `Deno.Command`, `node:crypto`, `Deno.osUptime()`, `Deno.systemMemoryInfo()`, sortie naturelle du processus après des appels Db2 asynchrones.

## Avertissement

**Aucune responsabilité.** Projet personnel, non officiel et ludique, fourni « tel quel », sans garantie d'aucune sorte, expresse ou implicite, et sans support. L'auteur **décline toute responsabilité** quant à l'utilisation de ce code ou des binaires construits avec, et quant à tout dommage direct ou indirect (perte de données, arrêt d'un système, incident de sécurité, ASP plein, etc.). Vous êtes seul responsable de ce que vous exécutez sur vos machines. Voir aussi la [LICENSE](LICENSE) (MIT), dont l'exclusion de garantie et de responsabilité s'applique pleinement.

**Non affilié.** Ce projet n'est ni affilié, ni parrainé, ni approuvé, ni soutenu par Deno Land Inc., IBM ou toute autre société.

**Ce qui est soumis aux droits de tiers :**

- **Marques** : « Deno » et le logo Deno sont des marques de Deno Land Inc. IBM, IBM i, AIX, Power, Db2 et PASE sont des marques d'International Business Machines Corporation. Les autres noms peuvent être des marques de leurs propriétaires respectifs. Ils ne sont cités que pour décrire ce avec quoi le projet fonctionne.
- **Code open source modifié** : les correctifs modifient Deno (MIT), rusty_v8 (MIT), V8 (BSD-3-Clause) et de nombreuses crates Rust (surtout MIT et/ou Apache-2.0). Le code modifié reste sous sa licence et son copyright d'origine.
- **Fichiers construits à partir de sources tierces** (objets de libffi, zlib-ng et psm ; liaisons bindgen des en-têtes de SQLite, AWS-LC, nghttp2, libuv et V8) : chacun reste sous sa propre licence, listée dans [THIRD_PARTY_NOTICES.fr.md](THIRD_PARTY_NOTICES.fr.md).
- **Logiciels IBM** : l'IBM Open SDK for Rust on AIX, le compilateur et le runtime IBM Open XL C/C++, la CLI SQL de PASE (`libdb400`) et IBM i lui-même s'obtiennent auprès d'IBM et s'utilisent selon les conditions de licence d'IBM. Le seul fichier IBM redistribué l'est dans le RPM : `libunwind.a`, non modifié, issu de l'IBM XL C/C++ for AIX 17.1.3 Runtime Environment, dont les License Information le classent parmi les Redistributables ; IBM le fournit « tel quel », sans garantie ni support (détails dans [`packaging/THIRD_PARTY_LICENSES.md`](packaging/THIRD_PARTY_LICENSES.md)).
- **Binaires** : ce dépôt ne contient aucun binaire de Deno ni de V8, seulement de quoi en construire un. Le RPM du dépôt yum contient un binaire construit ainsi ; il inclut du code tiers soumis aux licences listées dans [`packaging/THIRD_PARTY_LICENSES.md`](packaging/THIRD_PARTY_LICENSES.md) (installé dans `/QOpenSys/pkgs/share/licenses/deno/`) et relève des mêmes conditions « sans garantie, sans responsabilité » que le reste du projet.

## Licence

MIT (voir [LICENSE](LICENSE)). Composants tiers : [THIRD_PARTY_NOTICES.fr.md](THIRD_PARTY_NOTICES.fr.md).

## Auteur

Sylvain AKTEPE.

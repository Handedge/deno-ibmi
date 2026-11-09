# Générateur du snapshot de Deno pour IBM i (06/11/2026)

Le snapshot du CLI (`CLI_SNAPSHOT.bin` + sources résiduelles) fige le JavaScript de Deno : il change
**à chaque version de Deno**. Il doit être produit par le V8 d'IBM i (big-endian), pas par celui de
LINUXBUILD. Jusqu'au 05/11, seul l'arbre natif de IBMI savait le faire (plusieurs heures, 30 Go,
supprimé le 04/11). Le générateur ci-dessous le refait en **4 secondes** sur IBMI.

## Principe

`install.py` **dérive** un programme autonome du `cli/snapshot/build.rs` d'origine de Deno (même
code, dossier de sortie en argument) et l'ajoute au workspace (`cli/snapshot/generateur`, crate
`generer-snapshot`). On le compile en croisé comme Deno, on le lie sur IBM i, on l'exécute sur IBM i,
et ses sorties deviennent `DENO_SNAPSHOT_PREBUILT` de la compilation de Deno.

## Procédure

**Automatisée depuis le 06/11/2026 (étapes 1, 3 et 4 de `build/build.sh`).** Détail, pour
mise au point (chemins d'avant la phase 1 : l'arbre est désormais `/QOpenSys/opt/denoibmi`) :

1. LINUXBUILD : `python3 install.py ~/denox/arbre/deno <build.rs d'origine de cli/snapshot>`
   (le `build.rs` de l'arbre croisé est remplacé par `prepare-cross.py` : prendre celui d'un clone
   git propre).
2. LINUXBUILD : `cargo +stable build -Z build-std=std,panic_unwind --target powerpc64-ibm-aix
   --profile ibmi-rel -p generer-snapshot -j 28` (2 min 20).
3. Emballer `deps/generer_snapshot-*.lien` (`pack-link.sh`), déposer dans
   `/QOpenSys/opt/denoibmi/croise/lien.tar.gz`, lier en SBMJOB avec
   `PROFILE=ibmi-rel BINARY=generer_snapshot` (`replay-link.sh`) → `croise/generer_snapshot` (198 Mo).
4. IBMI : **synchroniser les sources JS/TS** de l'arbre croisé dans `/QOpenSys/opt/denoibmi/deno`
   (`ext`, `runtime`, `cli`, `libs` : `*.js *.ts *.mjs *.cjs *.json`, 717 fichiers, 20 Mo). La
   création du snapshot relit ces sources sur disque : elles doivent être celles qui seront compilées.
5. IBMI : `ulimit -d 8388608; XPG_SUS_ENV=ON croise/generer_snapshot <dossier>` (4 s).
6. Rapatrier `<dossier>` dans `~/denox/arbre/snapshot-genere` et compiler Deno avec
   `DENO_SNAPSHOT_PREBUILT=/QOpenSys/opt/denoibmi/snapshot-genere`.

## Piège : chemins figés

Les sources sont référencées par des chemins absolus figés à la compilation
(`concat!(env!("CARGO_MANIFEST_DIR"), …)`), et Linux rend toujours le chemin **physique** du dossier
courant : cargo voit `/home/build/denox/arbre/deno/…` même lancé depuis le lien
`/QOpenSys/opt/denoibmi`. Sur IBMI, le lien `/home/build/denox/arbre → /QOpenSys/opt/denoibmi`
fait exister ces chemins (créé le 06/11). **Réglé par la phase 1** : `/QOpenSys/opt/denoibmi` est un
vrai dossier sur LINUXBUILD, les chemins figés sont identiques des deux côtés, le lien a été supprimé.

## Validation (06/11/2026)

- `EXTENSION_RESIDUAL_SOURCES.rs` identique octet pour octet à la référence du 02/11 ; les 335 sources
  résiduelles identiques une à une.
- `CLI_SNAPSHOT.bin` : 2,1 Mo contre 3,1 Mo (référence produite par un profil de mise au point, avec
  assertions) : la comparaison binaire n'a pas de sens, la preuve est fonctionnelle.
- Deno recompilé avec ce snapshot : passe complète des tests unitaires (passe 10, sous DENOTEST)
  **identique à la passe 9** : 99,87 % des cas applicables, 0 écart propre à Deno.

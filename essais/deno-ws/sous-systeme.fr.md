# Sous-système DENOWS (IBMI, 04/11/2026)

Le webservice Deno tourne dans son propre sous-système, démarré à l'IPL par `QGPL/QSTRUP`.

| Travail | Rôle | Script |
|---|---|---|
| `DENOWS` (entrée automatique) | superviseur : lance deno, le relance s'il s'arrête (pause 5 s → 300 s), message QSYSOPR | `ws.sh` |
| `DENOVEILLE` (entrée automatique) | veille : santé HTTP chaque minute, mesures toutes les 5 min (`logs/mesures.csv`), alertes QSYSOPR (3 échecs HTTP, ASP ≥ 80 %, mémoire DENOWS ≥ 6 Go), rotation des journaux > 20 Mo | `veille.sh` |

Exploitation (profil *ALLOBJ) :
- arrêter : `sh /QOpenSys/opt/denoibmi/ws/arret.sh` (dépose `logs/ARRET`, `kill -9` de deno, attend
  superviseur et veille, `ENDSBS`). Pas d'`ENDJOB` sur deno : le travail reste en END et garde le port.
- démarrer : `STRSBS SBSD(DENOIBMI/DENOWS)`.
- remplacer un script : `cp` vers `x.nouveau` puis `mv -f` (nouvel inode), **jamais `cp` par-dessus un
  script en cours** : sh lit son script au fil de l'eau et exécute alors un mélange des deux versions.

## Objets créés

```
CRTLIB LIB(DENOIBMI) TEXT('Webservice Deno : sous-systeme et JOBD')
CRTSBSD SBSD(DENOIBMI/DENOWS) POOLS((1 *BASE)) MAXJOBS(*NOMAX) TEXT('Webservice Deno (DENOAPP)')
CRTJOBQ JOBQ(DENOIBMI/DENOWS) TEXT('Webservice Deno')
ADDJOBQE SBSD(DENOIBMI/DENOWS) JOBQ(DENOIBMI/DENOWS) MAXACT(*NOMAX)
CRTCLS CLS(DENOIBMI/DENOWS) RUNPTY(20) TEXT('Webservice Deno, priorite 20')
ADDRTGE SBSD(DENOIBMI/DENOWS) SEQNBR(10) CMPVAL(*ANY) PGM(QSYS/QCMD) CLS(DENOIBMI/DENOWS)
CRTJOBD JOBD(DENOIBMI/DENOWS) JOBQ(DENOIBMI/DENOWS) USER(DENOAPP) ALWMLTTHD(*YES)
        RQSDTA('CALL PGM(QP2SHELL) PARM(''/QOpenSys/usr/bin/sh'' ''/QOpenSys/opt/denoibmi/ws/ws.sh'')')
CRTJOBD JOBD(DENOIBMI/DENOVEILLE) JOBQ(DENOIBMI/DENOWS) USER(DENOAPP) ALWMLTTHD(*YES)
        RQSDTA('CALL PGM(QP2SHELL) PARM(''/QOpenSys/usr/bin/sh'' ''/QOpenSys/opt/denoibmi/ws/veille.sh'')')
ADDAJE SBSD(DENOIBMI/DENOWS) JOB(DENOWS) JOBD(DENOIBMI/DENOWS)
ADDAJE SBSD(DENOIBMI/DENOWS) JOB(DENOVEILLE) JOBD(DENOIBMI/DENOVEILLE)
```

Droits : les deux JOBD en `*PUBLIC *EXCLUDE` (une JOBD avec `USER()` permet sinon à n'importe qui de
soumettre sous DENOAPP) ; DENOAPP en `*USE` sur la bibliothèque, les JOBD, la classe, la JOBQ **et la
description de sous-système** (sans ce dernier droit : CPF1178 « ne peut pas démarrer travail automatique »).

## QSTRUP

`QGPL/QSTRUP` était déjà personnalisé (lancement de Mapepire). Source réel extrait par `RTVCLSRC` dans
`DENOIBMI/QCLSRC(QSTRUP)` (copie : `ibmi-qstrup.clp`), deux lignes ajoutées après Mapepire :
```
     QSYS/STRSBS SBSD(DENOIBMI/DENOWS)
     MONMSG MSGID(CPF0000)
```
recompilé (`CRTCLPGM ... REPLACE(*YES)`), propriétaire rendu à QPGMR, `*PUBLIC *USE`. Ancien programme :
`DENOIBMI/QSTRUP0411`. **Piège** : `QGPL/QCLSRC(QSTRUP)` est le source IBM d'origine *sans* Mapepire
(extrait le 28/10) ; le recompiler ferait perdre le démarrage de Mapepire.

## Pièges rencontrés

- `qsh -c "db2 ..."` dans un travail batch écrit son résultat dans un spool QPRINT (même avec
  `QIBM_QSH_CMD_OUTPUT=STDOUT`) : la veille utilise `/QOpenSys/pkgs/bin/db2util -o space`.
- Sous PASE, `ps -o rss` vaut 0 et `/proc` n'existe pas : la mémoire d'un processus se lit dans la
  mémoire temporaire du travail (`QSYS2.ACTIVE_JOB_INFO.TEMPORARY_STORAGE`, en Mo).

## Endurance

`endurance/charge.py` sur LINUXBUILD (10 req/s, mélange de routes HTTP, HTTPS et Db2, 48 h) ; résultats dans
`~/endurance/charge.csv` (LINUXBUILD) et `logs/mesures.csv` (IBMI).

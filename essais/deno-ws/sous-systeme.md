# DENOWS subsystem (IBMI, 2026-11-04)

The Deno web service runs in its own subsystem, started at IPL by `QGPL/QSTRUP`.

| Job | Role | Script |
|---|---|---|
| `DENOWS` (autostart job entry) | supervisor: starts deno, restarts it if it stops (pause 5 s → 300 s), QSYSOPR message | `ws.sh` |
| `DENOVEILLE` (autostart job entry) | health monitor: HTTP health check every minute, metrics every 5 min (`logs/mesures.csv`), QSYSOPR alerts (3 HTTP failures, ASP ≥ 80%, DENOWS memory ≥ 6 GB), rotation of logs > 20 MB | `veille.sh` |

Operations (*ALLOBJ profile):
- stop: `sh /QOpenSys/opt/denoibmi/ws/arret.sh` (drops `logs/ARRET`, `kill -9` of deno, waits for the
  supervisor and the monitor, `ENDSBS`). No `ENDJOB` on deno: the job stays in END status and keeps the port.
- start: `STRSBS SBSD(DENOIBMI/DENOWS)`.
- replace a script: `cp` to `x.nouveau` then `mv -f` (new inode), **never `cp` over a running
  script**: sh reads its script as it goes and would then execute a mix of both versions.

## Objects created

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

Authorities: both JOBDs are `*PUBLIC *EXCLUDE` (otherwise a JOBD with `USER()` lets anyone
submit jobs under DENOAPP); DENOAPP has `*USE` on the library, the JOBDs, the class, the JOBQ **and the
subsystem description** (without this last authority: CPF1178 "cannot start autostart job").

## QSTRUP

`QGPL/QSTRUP` was already customized (Mapepire startup). The actual source was extracted with `RTVCLSRC` into
`DENOIBMI/QCLSRC(QSTRUP)` (copy: `ibmi-qstrup.clp`), and two lines were added after Mapepire:
```
     QSYS/STRSBS SBSD(DENOIBMI/DENOWS)
     MONMSG MSGID(CPF0000)
```
recompiled (`CRTCLPGM ... REPLACE(*YES)`), owner given back to QPGMR, `*PUBLIC *USE`. Previous program:
`DENOIBMI/QSTRUP0411`. **Pitfall**: `QGPL/QCLSRC(QSTRUP)` is IBM's original source *without* Mapepire
(extracted on 2026-10-28); recompiling it would lose the Mapepire startup.

## Pitfalls encountered

- `qsh -c "db2 ..."` in a batch job writes its result to a QPRINT spooled file (even with
  `QIBM_QSH_CMD_OUTPUT=STDOUT`): the health monitor uses `/QOpenSys/pkgs/bin/db2util -o space`.
- Under PASE, `ps -o rss` is 0 and `/proc` does not exist: a process's memory is read from the job's
  temporary storage (`QSYS2.ACTIVE_JOB_INFO.TEMPORARY_STORAGE`, in MB).

## Endurance

`endurance/charge.py` on LINUXBUILD (10 req/s, mix of HTTP, HTTPS and Db2 routes, 48 h); results in
`~/endurance/charge.csv` (LINUXBUILD) and `logs/mesures.csv` (IBMI).

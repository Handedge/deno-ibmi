#!/QOpenSys/usr/bin/sh
# Supervisor of the Deno web service: job DENOWS, profile DENOAPP, subsystem DENOIBMI/DENOWS.
# Started at IPL by the autostart job entry of the subsystem (QSTRUP runs STRSBS).
# Restarts deno if it stops (increasing delay 5 s → 300 s), unless arret.sh created logs/ARRET.
# Equivalent manual start:
#   SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/sh' '/QOpenSys/opt/denoibmi/ws/ws.sh'))
#          JOB(DENOWS) JOBD(DENOIBMI/DENOWS) USER(DENOAPP) INLLIBL(*JOBD) ALWMLTTHD(*YES)
W=/QOpenSys/opt/denoibmi/ws
L=$W/logs
exec >> $L/denows.log 2>&1          # append (not overwrite): the watchdog may truncate the log
rm -f $L/ARRET                      # a start always clears a stale stop request
. /QOpenSys/opt/rust/rustenv.sh
# 8 GB of data at most: an unbounded PASE process can fill the ASP and bring the
# partition down (incident of 2026-11-03); the V8 heap is 4 GB
ulimit -d 8388608; ulimit -s unlimited
export HOME=/home/DENOAPP
export DENO_DIR=$W/cache               # TypeScript compilation cache (owned by DENOAPP)
export DENO_NO_UPDATE_CHECK=1          # no outbound call at startup
export XPG_SUS_ENV=ON                  # direct MAP_FIXED mmap (V8 race on AIX); also avoids
                                       # Deno re-executing itself at startup (+117 ms)
h() { date '+%Y-%m-%d %H:%M:%S'; }
echo "$(h) superviseur demarre (pid $$, $(id -un))"
pause=5
relances=0
echo 0 > $L/relances
while :; do
  debut=$(date +%s)
  echo "$(h) lancement de deno"
  /QOpenSys/opt/denoibmi/bin/deno run --allow-net --allow-ffi --allow-env=DENOWS_HOTE \
    --allow-read=/QOpenSys/opt/denoibmi/tls $W/serveur.ts
  rc=$?
  [ -f $L/ARRET ] && { echo "$(h) arret demande (rc=$rc)"; break; }
  duree=$(( $(date +%s) - debut ))
  # a long run resets the delay to 5 s; stops in quick succession double it, up to 5 min
  if [ $duree -ge 600 ]; then pause=5; else pause=$((pause * 2)); [ $pause -gt 300 ] && pause=300; fi
  relances=$((relances + 1))
  echo $relances > $L/relances
  echo "$(h) deno arrete rc=$rc apres $duree s ; relance $relances dans $pause s"
  /QOpenSys/usr/bin/system "SNDMSG MSG('DENOWS : deno arrete (rc=$rc apres $duree s), relance dans $pause s') TOUSR(*SYSOPR)" >/dev/null 2>&1
  sleep $pause
  [ -f $L/ARRET ] && { echo "$(h) arret demande pendant la pause"; break; }
done
echo "$(h) superviseur termine"

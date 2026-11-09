#!/QOpenSys/usr/bin/sh
# Clean shutdown of the Deno web service (run under an *ALLOBJ profile, via ssh or SBMJOB):
# 1. create logs/ARRET (the ws.sh supervisor will not restart deno, the watchdog stops);
# 2. kill -9 deno (ENDJOB leaves the job in END status and the port still in use);
# 3. wait for the supervisor and the watchdog to end (90 s at most), then ENDSBS.
# Restart: STRSBS SBSD(DENOIBMI/DENOWS).
L=/QOpenSys/opt/denoibmi/ws/logs
touch $L/ARRET
for p in $(ps -ef | awk '$1 == "denoapp" && /bin\/deno run/ && /serveur.ts/ {print $2}'); do
  echo "kill -9 deno $p"; kill -9 $p
done
i=0
while [ $i -lt 90 ] && ps -ef | grep -v grep | grep -q -e 'ws/ws.sh' -e 'ws/veille.sh'; do sleep 1; i=$((i + 1)); done
ps -ef | grep -v grep | grep -e 'ws/ws.sh' -e 'ws/veille.sh' && echo "WARNING: processes still running"
/QOpenSys/usr/bin/system "ENDSBS SBS(DENOWS) OPTION(*IMMED)" 2>&1 | tail -1
echo "shutdown completed in $i s"

#!/QOpenSys/usr/bin/sh
# Watchdog for the Deno web service: job DENOVEILLE, profile DENOAPP, subsystem DENOIBMI/DENOWS.
# - every minute: GET http://127.0.0.1:3081/bonjour; QSYSOPR alert after 3 consecutive failures,
#   then a back-to-normal message;
# - every 5 minutes: measurements in logs/mesures.csv (HTTPS 3444, ASP, temporary storage of the
#   DENOWS jobs (where the memory of a PASE process is accounted for), deno VSZ and threads,
#   restart count); alerts on ASP >= 80 % and DENOWS memory >= 6 GB (ulimit cap 8 GB);
# - log rotation above 20 MB (5 generations).
# Stops when arret.sh creates logs/ARRET.
W=/QOpenSys/opt/denoibmi/ws
L=$W/logs
CSV=$L/mesures.csv
CURL=/QOpenSys/pkgs/bin/curl
DB2=/QOpenSys/pkgs/bin/db2util
exec >> $L/veille.log 2>&1
rm -f $L/ARRET
h() { date '+%Y-%m-%d %H:%M:%S'; }
alert() {
  echo "$(h) ALERT $1"
  /QOpenSys/usr/bin/system "SNDMSG MSG('$1') TOUSR(*SYSOPR)" >/dev/null 2>&1
}
file_size() { ls -l "$1" 2>/dev/null | awk '{print $5}'; }
rotate_log() {   # rotate by copy then truncate: deno writes in append mode, it goes on without reopening
  t=$(file_size "$1")
  [ -n "$t" ] && [ "$t" -gt 20971520 ] || return 0
  i=4
  while [ $i -ge 1 ]; do [ -f "$1.$i" ] && mv -f "$1.$i" "$1.$((i + 1))"; i=$((i - 1)); done
  cp "$1" "$1.1" && : > "$1"
  echo "$(h) rotated $1 ($t bytes)"
}
measure() {
  rs=$($CURL -s -o /dev/null -m 10 --cacert /QOpenSys/opt/denoibmi/tls/ca.crt \
       -w '%{http_code}' https://127.0.0.1:3444/bonjour)
  # ASP and temporary storage (MB) of the DENOWS jobs (sh + deno), in a single query. db2util (PASE
  # CLI) rather than "qsh -c db2": in batch, qsh writes its output to a QPRINT spooled file on every call.
  set -- $($DB2 -o space "select (select system_asp_used from qsys2.system_status_info), \
coalesce(sum(temporary_storage), 0) from table(qsys2.active_job_info(job_name_filter => 'DENOWS')) x" \
    | tr -d '"' | awk '$1 ~ /^[0-9.]+$/ && NF == 2 {print $1, $2}')
  asp=${1:-?}; tmp=${2:-?}
  pid=$(ps -ef | awk '$1 == "denoapp" && /bin\/deno run/ && /serveur.ts/ {print $2}' | head -1)
  vsz=; threads=
  [ -n "$pid" ] && set -- $(ps -o vsz=,thcount= -p $pid) && vsz=$1 && threads=$2
  echo "$(h);$code;$ms;$rs;$asp;$tmp;$pid;$vsz;$threads;$(cat $L/relances 2>/dev/null)" >> $CSV
  if [ "$asp" != "?" ]; then
    a=${asp%.*}
    if [ "$a" -ge 80 ] && [ $asp_state = ok ]; then alert "IBMI: ASP at $asp % (threshold 80 %)"; asp_state=ko
    elif [ "$a" -lt 75 ] && [ $asp_state = ko ]; then alert "IBMI: ASP back to $asp %"; asp_state=ok; fi
  fi
  if [ "$tmp" != "?" ]; then
    if [ "$tmp" -ge 6144 ] && [ $mem_state = ok ]; then alert "DENOWS: temporary storage $tmp MB (cap 8 GB)"; mem_state=ko
    elif [ "$tmp" -lt 4096 ] && [ $mem_state = ko ]; then mem_state=ok; fi
  fi
  rotate_log $L/denows.log
  rotate_log $L/veille.log
}

[ -f $CSV ] || echo "horodatage;http;duree_ms;https;asp_pct;memoire_tmp_mo;deno_pid;deno_vsz_ko;deno_fils;relances" > $CSV
echo "$(h) watchdog started (pid $$, $(id -un))"
sleep 60                              # give deno time to start
failures=0; http_state=ok; asp_state=ok; mem_state=ok; n=0
while [ ! -f $L/ARRET ]; do
  r=$($CURL -s -o /dev/null -m 10 -w '%{http_code} %{time_total}' http://127.0.0.1:3081/bonjour)
  code=${r% *}
  ms=$(echo "${r#* }" | awk '{printf "%d", $1 * 1000}')
  if [ "$code" = 200 ]; then
    failures=0
    [ $http_state = ko ] && { alert "DENOWS answers again (HTTP 200)"; http_state=ok; }
  else
    failures=$((failures + 1))
    echo "$(h) failure $failures: HTTP $code"
    [ $failures -ge 3 ] && [ $http_state = ok ] && { alert "DENOWS not answering for 3 min (HTTP $code)"; http_state=ko; }
  fi
  [ $((n % 5)) -eq 0 ] && measure
  n=$((n + 1))
  sleep 60
done
echo "$(h) watchdog stopped (stop requested)"

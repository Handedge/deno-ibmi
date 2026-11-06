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
alerte() {
  echo "$(h) ALERTE $1"
  /QOpenSys/usr/bin/system "SNDMSG MSG('$1') TOUSR(*SYSOPR)" >/dev/null 2>&1
}
taille() { ls -l "$1" 2>/dev/null | awk '{print $5}'; }
tourner() {   # rotate by copy then truncate: deno writes in append mode, it goes on without reopening
  t=$(taille "$1")
  [ -n "$t" ] && [ "$t" -gt 20971520 ] || return 0
  i=4
  while [ $i -ge 1 ]; do [ -f "$1.$i" ] && mv -f "$1.$i" "$1.$((i + 1))"; i=$((i - 1)); done
  cp "$1" "$1.1" && : > "$1"
  echo "$(h) rotation de $1 ($t octets)"
}
mesurer() {
  rs=$($CURL -s -o /dev/null -m 10 --cacert /QOpenSys/opt/denoibmi/tls/ca.crt \
       -w '%{http_code}' https://127.0.0.1:3444/bonjour)
  # ASP and temporary storage (MB) of the DENOWS jobs (sh + deno), in a single query. db2util (PASE
  # CLI) rather than "qsh -c db2": in batch, qsh writes its output to a QPRINT spooled file on every call.
  set -- $($DB2 -o space "select (select system_asp_used from qsys2.system_status_info), \
coalesce(sum(temporary_storage), 0) from table(qsys2.active_job_info(job_name_filter => 'DENOWS')) x" \
    | tr -d '"' | awk '$1 ~ /^[0-9.]+$/ && NF == 2 {print $1, $2}')
  asp=${1:-?}; tmp=${2:-?}
  pid=$(ps -ef | awk '$1 == "denoapp" && /bin\/deno run/ && /serveur.ts/ {print $2}' | head -1)
  vsz=; fils=
  [ -n "$pid" ] && set -- $(ps -o vsz=,thcount= -p $pid) && vsz=$1 && fils=$2
  echo "$(h);$code;$ms;$rs;$asp;$tmp;$pid;$vsz;$fils;$(cat $L/relances 2>/dev/null)" >> $CSV
  if [ "$asp" != "?" ]; then
    a=${asp%.*}
    if [ "$a" -ge 80 ] && [ $etat_asp = ok ]; then alerte "IBMI : ASP a $asp % (seuil 80 %)"; etat_asp=ko
    elif [ "$a" -lt 75 ] && [ $etat_asp = ko ]; then alerte "IBMI : ASP revenu a $asp %"; etat_asp=ok; fi
  fi
  if [ "$tmp" != "?" ]; then
    if [ "$tmp" -ge 6144 ] && [ $etat_mem = ok ]; then alerte "DENOWS : memoire temporaire $tmp Mo (plafond 8 Go)"; etat_mem=ko
    elif [ "$tmp" -lt 4096 ] && [ $etat_mem = ko ]; then etat_mem=ok; fi
  fi
  tourner $L/denows.log
  tourner $L/veille.log
}

[ -f $CSV ] || echo "horodatage;http;duree_ms;https;asp_pct;memoire_tmp_mo;deno_pid;deno_vsz_ko;deno_fils;relances" > $CSV
echo "$(h) veille demarree (pid $$, $(id -un))"
sleep 60                              # give deno time to start
echecs=0; etat_http=ok; etat_asp=ok; etat_mem=ok; n=0
while [ ! -f $L/ARRET ]; do
  r=$($CURL -s -o /dev/null -m 10 -w '%{http_code} %{time_total}' http://127.0.0.1:3081/bonjour)
  code=${r% *}
  ms=$(echo "${r#* }" | awk '{printf "%d", $1 * 1000}')
  if [ "$code" = 200 ]; then
    echecs=0
    [ $etat_http = ko ] && { alerte "DENOWS repond de nouveau (HTTP 200)"; etat_http=ok; }
  else
    echecs=$((echecs + 1))
    echo "$(h) echec $echecs : HTTP $code"
    [ $echecs -ge 3 ] && [ $etat_http = ok ] && { alerte "DENOWS ne repond plus depuis 3 min (HTTP $code)"; etat_http=ko; }
  fi
  [ $((n % 5)) -eq 0 ] && mesurer
  n=$((n + 1))
  sleep 60
done
echo "$(h) veille terminee (arret demande)"

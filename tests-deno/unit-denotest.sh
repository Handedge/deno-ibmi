# Deno unit tests under the ordinary DENOTEST profile (group DENOTSTG), matching the
# x64 reference, which runs as an ordinary user. Usage (SBMJOB USER(DENOTEST)):
#   NOM=passe9 FILTRE=... sh unit-denotest.sh
NOM=${NOM:-denotest}
exec > /tmp/rustpoc/$NOM.log 2>&1
. /QOpenSys/opt/rust/rustenv.sh
ulimit -d 8388608; ulimit -s unlimited
export HOME=/home/DENOTEST
id
T=/QOpenSys/opt/denoibmi/denotests
# ASP safeguard: stop at 80 % (incidents of 2026-11-03)
(
  while [ ! -f /tmp/rustpoc/$NOM.fin ]; do
    a=$(/QOpenSys/pkgs/bin/db2util -o space "select system_asp_used from qsys2.system_status_info" | tr -d '"' | awk '$1 ~ /^[0-9.]+$/ {print int($1)}')
    echo "$(date +%T) ASP=$a %" >> /tmp/rustpoc/$NOM-asp.log
    if [ -n "$a" ] && [ "$a" -ge 80 ]; then echo "ASP $a % : ARRET" >> /tmp/rustpoc/$NOM-asp.log; pkill -f unit.py; break; fi
    sleep 30
  done
) &
rm -f /tmp/rustpoc/$NOM.fin
cd $T && /QOpenSys/pkgs/bin/python3.9 unit.py $T /QOpenSys/opt/denoibmi/croise/deno $T/target/aix/test_server /tmp/rustpoc/$NOM.jsonl 3 $FILTRE
touch /tmp/rustpoc/$NOM.fin
echo "FIN $NOM"

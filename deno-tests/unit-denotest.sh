# Deno unit tests under the ordinary DENOTEST profile (group DENOTSTG), matching the
# x64 reference, which runs as an ordinary user. Usage (SBMJOB USER(DENOTEST)):
#   RUN_NAME=passe9 FILTER=... sh unit-denotest.sh
RUN_NAME=${RUN_NAME:-denotest}
exec > /tmp/rustpoc/$RUN_NAME.log 2>&1
. /QOpenSys/opt/rust/rustenv.sh
ulimit -d 8388608; ulimit -s unlimited
export HOME=/home/DENOTEST
id
T=/QOpenSys/opt/denoibmi/denotests
# ASP safeguard: stop at 80 % (incidents of 2026-11-03)
(
  while [ ! -f /tmp/rustpoc/$RUN_NAME.fin ]; do
    a=$(/QOpenSys/pkgs/bin/db2util -o space "select system_asp_used from qsys2.system_status_info" | tr -d '"' | awk '$1 ~ /^[0-9.]+$/ {print int($1)}')
    echo "$(date +%T) ASP=$a %" >> /tmp/rustpoc/$RUN_NAME-asp.log
    if [ -n "$a" ] && [ "$a" -ge 80 ]; then echo "ASP $a %: STOP" >> /tmp/rustpoc/$RUN_NAME-asp.log; pkill -f unit.py; break; fi
    sleep 30
  done
) &
rm -f /tmp/rustpoc/$RUN_NAME.fin
cd $T && /QOpenSys/pkgs/bin/python3.9 unit.py $T /QOpenSys/opt/denoibmi/croise/deno $T/target/aix/test_server /tmp/rustpoc/$RUN_NAME.jsonl 3 $FILTER
touch /tmp/rustpoc/$RUN_NAME.fin
echo "DONE $RUN_NAME"

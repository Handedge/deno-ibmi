#!/QOpenSys/usr/bin/sh
# Installs a Deno package built by build.sh, restarts the services and checks them;
# automatically rolls back to the previous version if a service does not respond.
# Must be run by an ADMINISTRATOR (a human decision: the build is automatic, the
# installation is not).
#   sh deploy.sh --check <package>    check only (checksums, execution), installs nothing
#   sh deploy.sh <package>             install, restart, check (automatic rollback on failure)
#   sh deploy.sh --rollback            roll back to the previous version
# <package>: name or path under /QOpenSys/opt/denoibmi/livraisons
set -u
L=/QOpenSys/opt/denoibmi/livraisons
B=/QOpenSys/opt/denoibmi/bin
RT=/QOpenSys/opt/rust/runtime
CURL=/QOpenSys/pkgs/bin/curl
h() { date '+%H:%M:%S'; }

check_package() {   # check_package <package directory>
  [ -d "$1" ] || { echo "ERROR: package not found: $1"; return 1; }
  (cd "$1" && /QOpenSys/pkgs/bin/sha256sum -c SHA256SUMS) || { echo "ERROR: wrong checksums: package refused"; return 1; }
  XPG_SUS_ENV=ON "$1/deno" --version | head -1 || return 1
  XPG_SUS_ENV=ON DENO_NO_UPDATE_CHECK=1 "$1/deno" eval 'console.log("eval OK", Deno.build.os)' || return 1
}

restart_services() {
  echo "$(h) stopping the API (SIGTERM: Db2 sessions closed cleanly)"
  for p in $(ps -ef | awk '$1 == "denoapp" && /api\/api.ts/ {print $2}'); do kill -TERM $p; done
  echo "$(h) stopping DENOWS and the watchdog"
  /QOpenSys/usr/bin/sh /QOpenSys/opt/denoibmi/ws/arret.sh
  # ENDSBS is asynchronous: a STRSBS issued too early is rejected (CPF1010, subsystem still active)
  # and nothing restarts (seen on the first delivery of 2026-11-06) → wait for complete shutdown
  i=0
  while [ $i -lt 30 ]; do
    n=$(/QOpenSys/pkgs/bin/db2util -o space "select count(*) from qsys2.subsystem_info where subsystem_description_library = 'DENOIBMI' and subsystem_description = 'DENOWS' and status <> 'INACTIVE'" | tr -d '"' | awk '$1 ~ /^[0-9]+$/ {print $1}')
    [ "${n:-1}" = 0 ] && break
    sleep 2; i=$((i + 1))
  done
  echo "$(h) subsystem ended (waited $((i * 2)) s)"
  # the three jobs (DENOWS, DENOVEILLE, DENOAPI) are autostart jobs of the subsystem
  echo "$(h) restarting the subsystem (DENOWS, watchdog, API)"
  /QOpenSys/usr/bin/system "STRSBS SBSD(DENOIBMI/DENOWS)"
}

health_check() {   # all three endpoints must answer 200 within 60 s
  i=0
  while [ $i -lt 12 ]; do
    a=$($CURL -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:3081/bonjour)
    b=$($CURL -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1:3444/bonjour)
    c=$($CURL -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1:3091/api/sante)
    [ "$a$b$c" = 200200200 ] && { echo "$(h) health check: DENOWS http $a, https $b; API $c"; return 0; }
    sleep 5; i=$((i + 1))
  done
  echo "$(h) ERROR: health check failed: DENOWS http $a, https $b; API $c"
  return 1
}

install_binary() {   # install_binary <source binary> <name to keep in bin/>
  cp "$1" "$B/$2.nouveau" && chmod 755 "$B/$2.nouveau" && mv -f "$B/$2.nouveau" "$B/$2"
  cp "$B/$2" "$B/deno.nouveau" && mv -f "$B/deno.nouveau" "$B/deno"     # new inode
}

case "${1:-}" in
  --check)
    P=${2:?package}; [ -d "$P" ] || P=$L/$P
    check_package "$P"; exit $? ;;
  --rollback)
    PREVIOUS=$(cat $B/PRECEDENTE 2>/dev/null) || { echo "ERROR: no previous version recorded"; exit 1; }
    echo "$(h) rolling back to $PREVIOUS"
    cp "$B/$PREVIOUS" "$B/deno.nouveau" && mv -f "$B/deno.nouveau" "$B/deno"
    cat $B/ACTUELLE > $B/PRECEDENTE.annulee 2>/dev/null; echo "$PREVIOUS" > $B/ACTUELLE
    restart_services; health_check; exit $? ;;
  ""|-*) sed -n '2,10p' "$0"; exit 1 ;;
esac

P=$1; [ -d "$P" ] || P=$L/$P
PACKAGE=$(basename "$P")
check_package "$P" || exit 1
CURRENT=$(cat $B/ACTUELLE 2>/dev/null || echo deno-0611)   # 2026-11-06: last manual installation
[ -f "$B/$CURRENT" ] || cp "$B/deno" "$B/$CURRENT"                # the version in service is kept
echo "$CURRENT" > $B/PRECEDENTE
echo "$(h) installing $PACKAGE (previous: $CURRENT)"
install_binary "$P/deno" "$PACKAGE"
# libpaseat: replaced only if it differs (backup copy kept), atomically
if ! cmp -s "$P/libpaseat.a" "$RT/libpaseat.a"; then
  cp -p "$RT/libpaseat.a" "$RT/libpaseat.a.avant-$PACKAGE"
  cp "$P/libpaseat.a" "$RT/libpaseat.a.tmp" && mv -f "$RT/libpaseat.a.tmp" "$RT/libpaseat.a"
  echo "$(h) libpaseat replaced (backup: libpaseat.a.avant-$PACKAGE)"
fi
echo "$PACKAGE" > $B/ACTUELLE
restart_services
if health_check; then
  echo "$(h) DEPLOYED: $PACKAGE in service (rollback: sh deploy.sh --rollback)"
else
  echo "$(h) automatic rollback to $CURRENT"
  cp "$B/$CURRENT" "$B/deno.nouveau" && mv -f "$B/deno.nouveau" "$B/deno"
  [ -f "$RT/libpaseat.a.avant-$PACKAGE" ] && cp "$RT/libpaseat.a.avant-$PACKAGE" "$RT/libpaseat.a.tmp" && mv -f "$RT/libpaseat.a.tmp" "$RT/libpaseat.a"
  echo "$CURRENT" > $B/ACTUELLE
  restart_services; health_check
  exit 1
fi

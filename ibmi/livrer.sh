#!/QOpenSys/usr/bin/sh
# Installs a Deno package built by construire.sh, restarts the services and checks them;
# automatically rolls back to the previous version if a service does not respond.
# Must be run by an ADMINISTRATOR (a human decision: the build is automatic, the
# installation is not).
#   sh livrer.sh --verifier <package>  check only (checksums, execution), installs nothing
#   sh livrer.sh <package>             install, restart, check (automatic rollback on failure)
#   sh livrer.sh --retour              roll back to the previous version
# <package>: name or path under /QOpenSys/opt/denoibmi/livraisons
set -u
L=/QOpenSys/opt/denoibmi/livraisons
B=/QOpenSys/opt/denoibmi/bin
RT=/QOpenSys/opt/rust/runtime
CURL=/QOpenSys/pkgs/bin/curl
h() { date '+%H:%M:%S'; }

verifier() {   # verifier <package directory>
  [ -d "$1" ] || { echo "paquet introuvable : $1"; return 1; }
  (cd "$1" && /QOpenSys/pkgs/bin/sha256sum -c SHA256SUMS) || { echo "EMPREINTES FAUSSES : paquet refusé"; return 1; }
  XPG_SUS_ENV=ON "$1/deno" --version | head -1 || return 1
  XPG_SUS_ENV=ON DENO_NO_UPDATE_CHECK=1 "$1/deno" eval 'console.log("eval OK", Deno.build.os)' || return 1
}

redemarrer() {
  echo "$(h) arrêt de l'API (SIGTERM : sessions Db2 fermées proprement)"
  for p in $(ps -ef | awk '$1 == "denoapp" && /api\/api.ts/ {print $2}'); do kill -TERM $p; done
  echo "$(h) arrêt de DENOWS et de la veille"
  /QOpenSys/usr/bin/sh /QOpenSys/opt/denoibmi/ws/arret.sh
  # ENDSBS is asynchronous: a STRSBS issued too early is rejected (CPF1010, subsystem still active)
  # and nothing restarts (seen on the first delivery of 2026-11-06) → wait for complete shutdown
  i=0
  while [ $i -lt 30 ]; do
    n=$(/QOpenSys/pkgs/bin/db2util -o space "select count(*) from qsys2.subsystem_info where subsystem_description_library = 'DENOIBMI' and subsystem_description = 'DENOWS' and status <> 'INACTIVE'" | tr -d '"' | awk '$1 ~ /^[0-9]+$/ {print $1}')
    [ "${n:-1}" = 0 ] && break
    sleep 2; i=$((i + 1))
  done
  echo "$(h) sous-système arrêté (attente $((i * 2)) s)"
  # the three jobs (DENOWS, DENOVEILLE, DENOAPI) are autostart jobs of the subsystem
  echo "$(h) redémarrage du sous-système (DENOWS, veille, API)"
  /QOpenSys/usr/bin/system "STRSBS SBSD(DENOIBMI/DENOWS)"
}

controler() {   # all three endpoints must answer 200 within 60 s
  i=0
  while [ $i -lt 12 ]; do
    a=$($CURL -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:3081/bonjour)
    b=$($CURL -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1:3444/bonjour)
    c=$($CURL -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1:3091/api/sante)
    [ "$a$b$c" = 200200200 ] && { echo "$(h) contrôle : DENOWS http $a, https $b ; API $c"; return 0; }
    sleep 5; i=$((i + 1))
  done
  echo "$(h) CONTRÔLE ÉCHOUÉ : DENOWS http $a, https $b ; API $c"
  return 1
}

installer() {   # installer <source binary> <name to keep in bin/>
  cp "$1" "$B/$2.nouveau" && chmod 755 "$B/$2.nouveau" && mv -f "$B/$2.nouveau" "$B/$2"
  cp "$B/$2" "$B/deno.nouveau" && mv -f "$B/deno.nouveau" "$B/deno"     # new inode
}

case "${1:-}" in
  --verifier)
    P=${2:?paquet}; [ -d "$P" ] || P=$L/$P
    verifier "$P"; exit $? ;;
  --retour)
    PREC=$(cat $B/PRECEDENTE 2>/dev/null) || { echo "aucune version précédente enregistrée"; exit 1; }
    echo "$(h) retour à $PREC"
    cp "$B/$PREC" "$B/deno.nouveau" && mv -f "$B/deno.nouveau" "$B/deno"
    cat $B/ACTUELLE > $B/PRECEDENTE.annulee 2>/dev/null; echo "$PREC" > $B/ACTUELLE
    redemarrer; controler; exit $? ;;
  ""|-*) sed -n '2,10p' "$0"; exit 1 ;;
esac

P=$1; [ -d "$P" ] || P=$L/$P
NOM=$(basename "$P")
verifier "$P" || exit 1
ACT=$(cat $B/ACTUELLE 2>/dev/null || echo deno-0611)   # 2026-11-06: last manual installation
[ -f "$B/$ACT" ] || cp "$B/deno" "$B/$ACT"                # the version in service is kept
echo "$ACT" > $B/PRECEDENTE
echo "$(h) installation de $NOM (précédente : $ACT)"
installer "$P/deno" "$NOM"
# libpaseat: replaced only if it differs (backup copy kept), atomically
if ! cmp -s "$P/libpaseat.a" "$RT/libpaseat.a"; then
  cp -p "$RT/libpaseat.a" "$RT/libpaseat.a.avant-$NOM"
  cp "$P/libpaseat.a" "$RT/libpaseat.a.tmp" && mv -f "$RT/libpaseat.a.tmp" "$RT/libpaseat.a"
  echo "$(h) libpaseat remplacée (secours : libpaseat.a.avant-$NOM)"
fi
echo "$NOM" > $B/ACTUELLE
redemarrer
if controler; then
  echo "$(h) LIVRÉ : $NOM en service (retour possible : sh livrer.sh --retour)"
else
  echo "$(h) retour automatique à $ACT"
  cp "$B/$ACT" "$B/deno.nouveau" && mv -f "$B/deno.nouveau" "$B/deno"
  [ -f "$RT/libpaseat.a.avant-$NOM" ] && cp "$RT/libpaseat.a.avant-$NOM" "$RT/libpaseat.a.tmp" && mv -f "$RT/libpaseat.a.tmp" "$RT/libpaseat.a"
  echo "$ACT" > $B/ACTUELLE
  redemarrer; controler
  exit 1
fi

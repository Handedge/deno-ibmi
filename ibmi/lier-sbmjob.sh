#!/QOpenSys/usr/bin/sh
# Runs the link of a cross-compiled binary AS A SBMJOB (if started directly from ssh, the link
# would die when the session closes) and waits for it. Writes the result to /tmp/rustpoc/lien-<BINAIRE>.rc.
# Usage (over ssh, DENOBUILD profile): sh lier-sbmjob.sh <binary> [profile]
B=${1:-deno}; P=${2:-ibmi-rel}
D=$(cd "$(dirname "$0")" && pwd)
F=/tmp/rustpoc/lien-$B.rc
mkdir -p /tmp/rustpoc; rm -f $F
cat > /tmp/rustpoc/lien-$B.sh <<EOF
export PROFIL=$P BINAIRE=$B
/QOpenSys/usr/bin/sh $D/rejouer-lien.sh
if [ -x /QOpenSys/opt/denoibmi/croise/$B ]; then echo 0 > $F; else echo 1 > $F; fi
EOF
rm -f /QOpenSys/opt/denoibmi/croise/$B
/QOpenSys/usr/bin/system "SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/sh' '/tmp/rustpoc/lien-$B.sh')) JOB(LIEN) ALWMLTTHD(*YES) JOBQ(QSYSNOMAX)"
i=0
while [ ! -f $F ] && [ $i -lt 360 ]; do sleep 5; i=$((i + 1)); done
[ -f $F ] || { echo "lien de $B : délai dépassé (30 min)"; exit 1; }
rc=$(cat $F)
echo "lien de $B : rc=$rc en $((i * 5)) s"; ls -l /QOpenSys/opt/denoibmi/croise/$B 2>/dev/null
exit $rc

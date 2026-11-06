L=/QOpenSys/opt/denoibmi/ws/logs/droits.log
exec > $L 2>&1
echo "profil : $(id -un)"
for f in /QOpenSys/opt/denoibmi/bin/deno /QOpenSys/opt/denoibmi/ws/serveur.ts /QOpenSys/opt/denoibmi/ws/ws.sh /QOpenSys/opt/denoibmi/deno-db2/db2.ts; do
  if ( : >> $f ) 2>/dev/null; then echo "ECRITURE POSSIBLE : $f"; else echo "ecriture refusee : $f"; fi
done
if touch /QOpenSys/opt/denoibmi/ws/intrus 2>/dev/null; then echo "CREATION POSSIBLE dans ws"; rm -f /QOpenSys/opt/denoibmi/ws/intrus; else echo "creation refusee dans ws"; fi
if touch /QOpenSys/opt/denoibmi/ws/cache/essai 2>/dev/null; then echo "cache : ecriture ok"; rm -f /QOpenSys/opt/denoibmi/ws/cache/essai; fi

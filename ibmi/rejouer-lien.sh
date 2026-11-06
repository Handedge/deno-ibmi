#!/QOpenSys/usr/bin/sh
# Replays on IBM i the link of a Deno binary cross-compiled on LINUXBUILD.
# Input: /QOpenSys/opt/denoibmi/croise/lien.tar.gz (emballer-lien.sh); LINUXBUILD paths
# (/home/<account>/...) are relocated under /QOpenSys/opt/denoibmi/croise.
# Output: /QOpenSys/opt/denoibmi/croise/deno (or $BINAIRE: another binary of the same tree, e.g. test_server)
exec > /tmp/rustpoc/rejouer-lien.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
ulimit -d unlimited; ulimit -s unlimited; ulimit -f unlimited
C=/QOpenSys/opt/denoibmi/croise
cd $C || exit 1
date
# Packages are layered (full, then only the command and the objects of the linked
# crate): the extracted tree is never emptied.
if [ -f lien.tar.gz ]; then
  python3.9 -c '
import tarfile
with tarfile.open("lien.tar.gz", "r:gz") as t:
    for m in t:
        m.name = m.name.lstrip("/")
        if m.islnk() or m.issym():           # liens physiques du tar : cible aussi relative
            m.linkname = m.linkname.lstrip("/")
        t.extract(m, ".")
' && rm -f lien.tar.gz
fi
date
# most recent link command: new tree (/QOpenSys/opt/denoibmi, 2026-11-06) or old LINUXBUILD tree
# (/home/build/denox/arbre); the extracted package is never emptied (layering)
L=$(ls -t $C/QOpenSys/opt/denoibmi/deno/target/powerpc64-ibm-aix/${PROFIL:-ibmi-o1}/deps/${BINAIRE:-deno}-*.lien           $C/home/*/denox/arbre/deno/target/powerpc64-ibm-aix/${PROFIL:-ibmi-o1}/deps/${BINAIRE:-deno}-*.lien 2>/dev/null | head -1)
echo "commande : $L"
G=$L.d
# arguments: relocated paths; saved rustc files; output; options unknown to the PASE ld
sed -e "s|@GARDE@|$G|" \
    -e "s|^/home/|$C/home/|" \
    -e "s|^/QOpenSys/opt/denoibmi/deno/target|$C/QOpenSys/opt/denoibmi/deno/target|" \
    -e "s|^-bE:/home/|-bE:$C/home/|" \
    -e '/^-bdbg:namedsects/d' \
    -e '/^-Wl,/d' \
    "$L" > $C/args.txt
# -o: the output goes to $C/deno (or $C/$BINAIRE)
awk -v sortie="$C/${BINAIRE:-deno}" 'p=="-o"{print sortie; p=""; next} {print; p=$0}' $C/args.txt > $C/args2.txt
grep -c . $C/args2.txt
/QOpenSys/usr/bin/ld -bbinder:/QOpenSys/opt/rust/outils/bin/bind -s -bbigtoc $(cat $C/args2.txt) > $C/lien.txt 2>&1
rc=$?
echo "rc lien=$rc"
grep -v "0711-783\|Extra instructions\|symbol is in the TOC\|Instructions de correction\|dépassement de capacité\|Dépassement" $C/lien.txt | head -30
ls -l $C/${BINAIRE:-deno}
date

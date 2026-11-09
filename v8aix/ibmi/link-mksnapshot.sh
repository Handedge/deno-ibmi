#!/QOpenSys/usr/bin/sh
# Links on IBM i (PASE) the V8 mksnapshot executable built on LINUXBUILD:
# tarball mks.tar.gz = XCOFF objects + archives (Chromium libc++ included) +
# mksnapshot.entrees (link order). Linux options of the original command
# (lld, --icf, -pie) are dropped: PASE ld through the gcc-12 C driver.
exec > /tmp/rustpoc/link-mksnapshot.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
ulimit -d unlimited; ulimit -s unlimited
V=/QOpenSys/opt/denoibmi/v8aix
cd $V && rm -rf aix && mkdir aix && cd aix
python3.9 -c 'import sys,tarfile; tarfile.open(sys.argv[1]).extractall()' ../mks.tar.gz  # neither gzip nor tar z under PASE
echo "inputs: $(tr ' ' '\n' < mksnapshot.entrees | grep -c .)"
date
gcc-12 -maix64 -pthread -o mksnapshot \
  -Wl,-bbigtoc -Wl,-bbinder:/QOpenSys/opt/rust/outils/bin/bind -Wl,-bnoquiet \
  $(cat mksnapshot.entrees) -lm -ldl -lpthread > lien.txt 2>&1
echo "link rc=$?"; date
grep -E "ERROR|ERREUR|0711-[0-9]+" lien.txt | sort | uniq -c | sort -rn | head -20
grep -E "Symbole non défini" lien.txt | sed "s/.*: //" | sort -u | tr "
" " "; echo
ls -l mksnapshot 2>&1
echo DONE

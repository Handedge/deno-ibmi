#!/QOpenSys/usr/bin/sh
# Links then runs mksnapshot under PASE with the exact arguments of the ninja action
# run_mksnapshot_default (mksnapshot.args file, extracted on LINUXBUILD);
# produces gen/v8/embedded.S, gen/v8/snapshot.cc, gen/v8/src/builtins/builtins-effects.cc,
# assembles embedded.S (gcc-12 + PASE as) and bundles everything into
# sorties-mksnapshot.tar.gz for LINUXBUILD (~/v8aix/sorties-ibmi).
exec > /tmp/rustpoc/run-mksnapshot.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
ulimit -d unlimited; ulimit -s unlimited
V=/QOpenSys/opt/denoibmi/v8aix
cd $V/aix
# Direct ld (as rustc does): crt0_64.o + crti_64.o + -bcdtors to run clang static
# constructors (__sinit*); IBM libunwind for libc++abi
/QOpenSys/usr/bin/ld -b64 -bpT:0x100000000 -bpD:0x110000000 -bcdtors:all:0:s -bbigtoc \
  -bbinder:/QOpenSys/opt/rust/outils/bin/bind -o mksnapshot \
  /QOpenSys/usr/lib/crt0_64.o /QOpenSys/usr/lib/crti_64.o $(cat mksnapshot.entrees) \
  -L/QOpenSys/opt/rust/runtime -lunwind $(gcc-12 -maix64 -print-libgcc-file-name) \
  -lpthread -lm -ldl -lc -blibpath:/QOpenSys/opt/rust/runtime:/usr/lib:/lib > lien.txt 2>&1
echo "link rc=$?"; grep -E "Symbole non défini" lien.txt | sed "s/.*: //" | sort -u | head
ls -l mksnapshot || exit 1
cp ../icudtb.dat .
rm -rf gen; mkdir -p gen/v8/src/builtins
echo "arguments: $(cat mksnapshot.args)"
date
time ./mksnapshot $(cat mksnapshot.args)
echo "rc mksnapshot=$?"; date
ls -lR gen
time gcc-12 -maix64 -c gen/v8/embedded.S -o embedded.o
echo "assembly rc=$?"; ls -l embedded.o
python3.9 -c 'import tarfile; t=tarfile.open("../sorties-mksnapshot.tar.gz","w:gz"); t.add("gen"); t.add("embedded.o"); t.close()'
ls -l ../sorties-mksnapshot.tar.gz
echo DONE

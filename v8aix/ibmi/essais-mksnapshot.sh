#!/QOpenSys/usr/bin/sh
# mksnapshot run variants to narrow down the garbage collector crash,
# then the faulting instruction (dbx64 on the core dump of the base variant).
exec > /tmp/rustpoc/essais-mksnapshot.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
ulimit -d unlimited; ulimit -s unlimited; ulimit -c 0
cd /QOpenSys/opt/denoibmi/v8aix/aix
BASE="--turbo_instruction_scheduling --turbo-always-optimize-spills --target_os=aix --target_arch=ppc64 --predictable --no-use-ic --turbo-elide-frames --embedded_variant Default --random-seed 314159265 --no-native-code-counters --concurrent-builtin-generation --concurrent-turbofan-max-threads=0"
essai() {
  nom=$1; shift
  rm -rf sortie_$nom; mkdir -p sortie_$nom
  t0=$(date +%s)
  ./mksnapshot $BASE "$@" --embedded_src sortie_$nom/embedded.S --startup_src sortie_$nom/snapshot.cc > sortie_$nom/sortie.txt 2>&1
  rc=$?
  echo "== $nom : rc=$rc en $(( $(date +%s) - t0 )) s ; $(ls -l sortie_$nom | grep -c 'embedded\|snapshot') fichiers produits"
  tail -3 sortie_$nom/sortie.txt | cut -c1-200
}
essai gc1fil --single-threaded-gc
essai unfil --single-threaded
essai sansconcurrent --no-concurrent-marking --no-parallel-marking --no-parallel-compaction --no-concurrent-sweeping
echo "== instruction fautive (core de la variante de base)"
printf 'listi $iar - 0x20, $iar + 0x8\nprint $r3\nprint $r9\nquit\n' > /tmp/rustpoc/dbx2.cmd
timeout 300 /QOpenSys/usr/bin/dbx64 ./mksnapshot core < /tmp/rustpoc/dbx2.cmd 2>&1 | sed 's/(std::__Cr::pair[^)]*)//; s/v8::internal::MarkCompactCollector::ProcessMarkingWorklist.*unsigned long)//' | grep -v '^$' | tail -16
echo FIN

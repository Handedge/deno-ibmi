#!/QOpenSys/usr/bin/sh
# mksnapshot run variants to narrow down the garbage collector crash,
# then the faulting instruction (dbx64 on the core dump of the base variant).
exec > /tmp/rustpoc/try-mksnapshot.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
ulimit -d unlimited; ulimit -s unlimited; ulimit -c 0
cd /QOpenSys/opt/denoibmi/v8aix/aix
BASE="--turbo_instruction_scheduling --turbo-always-optimize-spills --target_os=aix --target_arch=ppc64 --predictable --no-use-ic --turbo-elide-frames --embedded_variant Default --random-seed 314159265 --no-native-code-counters --concurrent-builtin-generation --concurrent-turbofan-max-threads=0"
run_variant() {
  name=$1; shift
  rm -rf output_$name; mkdir -p output_$name
  t0=$(date +%s)
  ./mksnapshot $BASE "$@" --embedded_src output_$name/embedded.S --startup_src output_$name/snapshot.cc > output_$name/output.txt 2>&1
  rc=$?
  echo "== $name: rc=$rc in $(( $(date +%s) - t0 )) s; $(ls -l output_$name | grep -c 'embedded\|snapshot') files produced"
  tail -3 output_$name/output.txt | cut -c1-200
}
run_variant gc_single_thread --single-threaded-gc
run_variant single_thread --single-threaded
run_variant no_concurrent --no-concurrent-marking --no-parallel-marking --no-parallel-compaction --no-concurrent-sweeping
echo "== faulting instruction (core of the base variant)"
printf 'listi $iar - 0x20, $iar + 0x8\nprint $r3\nprint $r9\nquit\n' > /tmp/rustpoc/dbx2.cmd
timeout 300 /QOpenSys/usr/bin/dbx64 ./mksnapshot core < /tmp/rustpoc/dbx2.cmd 2>&1 | sed 's/(std::__Cr::pair[^)]*)//; s/v8::internal::MarkCompactCollector::ProcessMarkingWorklist.*unsigned long)//' | grep -v '^$' | tail -16
echo DONE

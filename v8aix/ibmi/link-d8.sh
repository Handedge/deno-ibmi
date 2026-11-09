#!/QOpenSys/usr/bin/sh
# Links d8 (the V8 JavaScript shell) on IBM i from d8.tar.gz (objects built
# on LINUXBUILD + d8.entrees), then runs first JavaScript smoke tests.
exec > /tmp/rustpoc/link-d8.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
ulimit -d unlimited; ulimit -s unlimited
V=/QOpenSys/opt/denoibmi/v8aix
cd $V && rm -rf d8 && mkdir d8 && cd d8
python3.9 -c 'import sys,tarfile; tarfile.open(sys.argv[1]).extractall()' ../d8.tar.gz
cp ../icudtb.dat .
echo "inputs: $(tr ' ' '\n' < d8.entrees | grep -c .)"
# Direct ld, as rustc does on AIX: the gcc driver goes through collect2, which ignores
# clang static initializers (__sinit*/__sterm*); -bcdtors:all:0:s collects them.
/QOpenSys/usr/bin/ld -b64 -bpT:0x100000000 -bpD:0x110000000 -bcdtors:all:0:s -bbigtoc   -bbinder:/QOpenSys/opt/rust/outils/bin/bind -o d8 /QOpenSys/usr/lib/crt0_64.o /QOpenSys/usr/lib/crti_64.o   $(cat d8.entrees) -L/QOpenSys/opt/rust/runtime -lunwind $(gcc-12 -maix64 -print-libgcc-file-name) -lpthread -lm -ldl -lc -blibpath:/QOpenSys/opt/rust/runtime:/usr/lib:/lib > lien.txt 2>&1
echo "link rc=$?"
grep -E "Symbole non défini" lien.txt | sed "s/.*: //" | sort -u | head -20
ls -l d8 || exit 1
echo "== version";      ./d8 -e 'print("V8 " + version() + " on IBM i")'
echo "== arithmetic";   ./d8 -e 'print(1 + 1, 6 * 7, Math.sqrt(2))'
echo "== fib(30)";      ./d8 -e 'function fib(n){return n<2?n:fib(n-1)+fib(n-2)}; const t=Date.now(); print(fib(30), (Date.now()-t)+" ms")'
echo "== loop 3e6";     ./d8 -e 'const t=Date.now(); let s=0; for (let i=0;i<3e6;i++) s+=i%7; print(s, (Date.now()-t)+" ms")'
echo "== JSON/regex";   ./d8 -e 'const o=JSON.parse("{\"a\":[1,2,{\"b\":\"été €\"}]}"); print(JSON.stringify(o), /(\d+)-(\d+)/.exec("10-20")[2])'
echo "== Intl";         ./d8 -e 'print(new Intl.NumberFormat("fr-FR").format(1234567.891), new Date(0).toISOString())'
echo "== typed array";  ./d8 -e 'const b=new Uint8Array(new Uint32Array([0x01020304]).buffer); print(b[0]===1 ? "big-endian" : "little-endian")'
echo "== promises";     ./d8 -e 'Promise.resolve(41).then(x=>print("promise", x+1))'
echo "== WebAssembly";  ./d8 -e 'const m=new WebAssembly.Module(new Uint8Array([0,97,115,109,1,0,0,0,1,7,1,96,2,127,127,1,127,3,2,1,0,7,7,1,3,97,100,100,0,0,10,9,1,7,0,32,0,32,1,106,11])); print("wasm add", new WebAssembly.Instance(m).exports.add(40,2))'
echo DONE

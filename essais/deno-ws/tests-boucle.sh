exec > /tmp/rustpoc/denot2.log 2>&1
. /QOpenSys/opt/rust/rustenv.sh
ulimit -d unlimited; ulimit -s unlimited
export RUST_BACKTRACE=full
D=/QOpenSys/opt/denoibmi/deno/target/ibmi-o1/deno
cd /QOpenSys/opt/denoibmi/ws
echo "== timer"; $D eval 'setTimeout(()=>console.log("timer ok"),500)'; echo "rc=$?"
echo "== promesse"; $D eval 'await new Promise(r=>setTimeout(r,200)); console.log("await ok")'; echo "rc=$?"
echo "== ts"; echo 'const x: number = 41; console.log("ts ok", x+1)' > t.ts; $D run t.ts; echo "rc=$?"
echo "== listen seul"; $D eval 'const l = Deno.listen({port:3082}); console.log("listen ok"); setTimeout(()=>{l.close(); console.log("close ok")},1000)'; echo "rc=$?"
echo "== serve 3s"; $D eval --allow-net 'const s = Deno.serve({port:3083, onListen(){console.log("ecoute")}}, ()=>new Response("ok")); setTimeout(()=>{console.log("arret"); s.shutdown()},3000)'; echo "rc=$?"
echo FIN

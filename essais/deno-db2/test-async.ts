// Test bench for non-blocking Db2 calls: deno run --allow-ffi test-async.ts
import { Db2, Db2Error, Db2Pool } from "./db2.ts";

// an exact one-second wait inside the QSQSRVR job of the connection
const LENTE = "CALL QSYS2.QCMDEXC('DLYJOB DLY(1)')";
const ms = (t: number) => `${(performance.now() - t).toFixed(0)} ms`;

// 1. baseline: one slow query, synchronous
const db = new Db2();
let t = performance.now();
db.execute(LENTE);
console.log(`1 requête lente, synchrone : ${ms(t)}`);

// 2. does the event loop stay free during an asynchronous query?
let tics = 0;
const minuteur = setInterval(() => tics++, 50);
t = performance.now();
await db.executeAsync(LENTE);
console.log(`1 requête lente, asynchrone : ${ms(t)}, minuteur 50 ms pendant ce temps : ${tics} tics`);
clearInterval(minuteur);

// 3. parallelism: 4 concurrent slow queries on a pool of 4 connections
const pool = new Db2Pool(4);
await Promise.all([1, 2, 3, 4].map(() => pool.query("VALUES 1"))); // opens the 4 connections
t = performance.now();
await Promise.all([1, 2, 3, 4].map(() => pool.execute(LENTE)));
console.log(`4 requêtes lentes en parallèle (pool de 4) : ${ms(t)}`);

// 4. same thing on a single connection: serialized
t = performance.now();
await Promise.all([1, 2, 3, 4].map(() => db.executeAsync(LENTE)));
console.log(`4 requêtes lentes sur 1 connexion (sérialisées) : ${ms(t)}`);

// 5. correctness under concurrency: 50 parameterized queries on the pool
t = performance.now();
const r = await Promise.all(
  Array.from({ length: 50 }, (_, i) =>
    pool.query("VALUES (CAST(? AS INTEGER) * 2, CAST(? AS VARCHAR(20)))", [i, `n°${i} é`])),
);
const justes = r.filter((l, i) => l[0]["00001"] === i * 2 && l[0]["00002"] === `n°${i} é`).length;
console.log(`50 requêtes concurrentes : ${justes}/50 justes en ${ms(t)}`, pool.stats);

// 6. asynchronous error
try {
  await pool.query("SELECT * FROM QTEMP.NEXISTEPAS");
} catch (e) {
  console.log("erreur asynchrone :", e instanceof Db2Error ? `${e.sqlState} ${e.sqlCode}` : e);
}
console.log("pool après erreur :", pool.stats);

pool.close();
db.close();
console.log("FIN");
if (Deno.args.includes("--exit")) Deno.exit(0);

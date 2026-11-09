// Test bench for non-blocking Db2 calls: deno run --allow-ffi test-async.ts
import { Db2, Db2Error, Db2Pool } from "./db2.ts";

// an exact one-second wait inside the QSQSRVR job of the connection
const SLOW = "CALL QSYS2.QCMDEXC('DLYJOB DLY(1)')";
const ms = (t: number) => `${(performance.now() - t).toFixed(0)} ms`;

// 1. baseline: one slow query, synchronous
const db = new Db2();
let t = performance.now();
db.execute(SLOW);
console.log(`1 slow query, synchronous: ${ms(t)}`);

// 2. does the event loop stay free during an asynchronous query?
let ticks = 0;
const timer = setInterval(() => ticks++, 50);
t = performance.now();
await db.executeAsync(SLOW);
console.log(`1 slow query, asynchronous: ${ms(t)}, 50 ms timer meanwhile: ${ticks} ticks`);
clearInterval(timer);

// 3. parallelism: 4 concurrent slow queries on a pool of 4 connections
const pool = new Db2Pool(4);
await Promise.all([1, 2, 3, 4].map(() => pool.query("VALUES 1"))); // opens the 4 connections
t = performance.now();
await Promise.all([1, 2, 3, 4].map(() => pool.execute(SLOW)));
console.log(`4 slow queries in parallel (pool of 4): ${ms(t)}`);

// 4. same thing on a single connection: serialized
t = performance.now();
await Promise.all([1, 2, 3, 4].map(() => db.executeAsync(SLOW)));
console.log(`4 slow queries on 1 connection (serialized): ${ms(t)}`);

// 5. correctness under concurrency: 50 parameterized queries on the pool
t = performance.now();
const r = await Promise.all(
  Array.from({ length: 50 }, (_, i) =>
    pool.query("VALUES (CAST(? AS INTEGER) * 2, CAST(? AS VARCHAR(20)))", [i, `n°${i} é`])),
);
const correct = r.filter((l, i) => l[0]["00001"] === i * 2 && l[0]["00002"] === `n°${i} é`).length;
console.log(`50 concurrent queries: ${correct}/50 correct in ${ms(t)}`, pool.stats);

// 6. asynchronous error
try {
  await pool.query("SELECT * FROM QTEMP.NEXISTEPAS");
} catch (e) {
  console.log("asynchronous error:", e instanceof Db2Error ? `${e.sqlState} ${e.sqlCode}` : e);
}
console.log("pool after error:", pool.stats);

pool.close();
db.close();
console.log("DONE");
if (Deno.args.includes("--exit")) Deno.exit(0);

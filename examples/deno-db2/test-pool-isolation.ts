// Pool isolation test (IBM i): does a pooled connection leak its job state to the next request?
// Scenario reported on Reddit (PUB400, JDBC): CHGLIBL, SET SCHEMA and QTEMP survive on a reused
// connection. Also checks how unqualified names resolve with system naming once a default schema
// is set (SET SCHEMA, or the SQL_ATTR_DBC_DEFAULT_LIB connection attribute).
//
// Usage (profile allowed to create libraries; test libraries are created then deleted):
//   deno run --allow-ffi --allow-read test-pool-isolation.ts
import { Db2, Db2Pool, type PoolReset } from "./db2.ts";

const A = "POOLTSTA", B = "POOLTSTB";
const results: [string, string, string][] = [];
const record = (scenario: string, check: string, value: unknown) => {
  results.push([scenario, check, String(value)]);
  console.log(`${scenario.padEnd(28)} ${check.padEnd(42)} ${value}`);
};
const cl = (db: Db2, cmd: string) => db.execute("CALL QSYS2.QCMDEXC(?)", [cmd]);
const single = (db: Db2, sql: string) => Object.values(db.query(sql)[0] ?? { v: null })[0];

// --- setup: two libraries, each with a table T holding its own letter
const admin = new Db2();
for (const lib of [A, B]) {
  try { cl(admin, `DLTLIB LIB(${lib})`); } catch { /* absent */ }
  cl(admin, `CRTLIB LIB(${lib}) TEXT('deno-ibmi pool isolation test')`);
  admin.execute(`CREATE TABLE ${lib}.T (V CHAR(1))`);
  admin.execute(`INSERT INTO ${lib}.T VALUES ('${lib.slice(-1)}') WITH NC`);
}

async function leakScenario(reset: PoolReset) {
  const name = `pool reset="${reset}"`;
  const pool = new Db2Pool(1, { systemNaming: true, reset });   // size 1: the same job is reused
  const job1 = await pool.withConnection(async (db) => {
    const job = single(db, "VALUES QSYS2.JOB_NAME");
    await db.executeAsync("CALL QSYS2.QCMDEXC(?)", [`ADDLIBLE LIB(${B})`]);
    await db.executeAsync(`SET SCHEMA ${A}`);
    await db.executeAsync("DECLARE GLOBAL TEMPORARY TABLE SESSION.LEAK (X INT) WITH REPLACE");
    return job;
  });
  await new Promise((r) => setTimeout(r, 300));                  // let the background reset finish
  await pool.withConnection(async (db) => {
    const job2 = single(db, "VALUES QSYS2.JOB_NAME");
    record(name, "same QSQSRVR job reused", job1 === job2 ? "yes" : `no (new job ${job2})`);
    const inLibl = db.query(`SELECT 1 FROM QSYS2.LIBRARY_LIST_INFO WHERE SCHEMA_NAME = '${B}'`).length > 0;
    record(name, `${B} still in library list`, inLibl);
    record(name, "current schema", single(db, "VALUES CURRENT SCHEMA"));
    let temp = "absent";
    try { db.query("SELECT COUNT(*) FROM SESSION.LEAK"); temp = "STILL THERE"; } catch { /* SQL0204 */ }
    record(name, "QTEMP table SESSION.LEAK", temp);
    // a request that needs the same temporary table must still be able to declare it
    try {
      db.execute("DECLARE GLOBAL TEMPORARY TABLE SESSION.LEAK (X INT) WITH REPLACE");
      record(name, "DGTT can be declared again", "yes");
    } catch (e) { record(name, "DGTT can be declared again", `NO: ${(e as Error).message.slice(0, 60)}`); }
  });
  await new Promise((r) => setTimeout(r, 300));
  pool.close();
}

function resolutionScenario() {
  const name = "unqualified name resolution";
  // system naming, B in the library list, no default schema
  const c1 = new Db2({ systemNaming: true });
  cl(c1, `ADDLIBLE LIB(${B})`);
  record(name, `*LIBL contains ${B}, no default schema`, single(c1, "SELECT V FROM T"));
  c1.execute(`SET SCHEMA ${A}`);
  record(name, `SET SCHEMA ${A}, *LIBL contains ${B}`, single(c1, "SELECT V FROM T"));
  cl(c1, `RMVLIBLE LIB(${B})`);
  let r = "not found";
  try { r = String(single(c1, "SELECT V FROM T")); } catch { /* SQL0204 */ }
  record(name, `SET SCHEMA ${A}, ${B} removed from *LIBL`, r);
  c1.close();
  // same thing with the connection attribute SQL_ATTR_DBC_DEFAULT_LIB (option "library")
  const c2 = new Db2({ systemNaming: true, library: A });
  cl(c2, `ADDLIBLE LIB(${B})`);
  record(name, `DEFAULT_LIB=${A}, *LIBL contains ${B}`, single(c2, "SELECT V FROM T"));
  record(name, `DEFAULT_LIB=${A}: CURRENT SCHEMA`, single(c2, "VALUES CURRENT SCHEMA"));
  c2.close();
}

try {
  await leakScenario("none");
  await leakScenario("restore");
  await leakScenario("discard");
  resolutionScenario();
} finally {
  for (const lib of [A, B]) {
    try { cl(admin, `DLTLIB LIB(${lib})`); } catch (e) { console.log(`cleanup ${lib}: ${e}`); }
  }
  admin.close();
}
Deno.exit(0);

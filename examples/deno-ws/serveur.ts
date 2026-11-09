// Deno web service on IBM i (PASE): JSON, outbound HTTPS call, Db2 for i reads
import { Db2Error, Db2Pool } from "../deno-db2/db2.ts";

let requestCount = 0;
const startedAt = new Date();

// pool of 4 Db2 connections (server mode: one QSQSRVR job per connection);
// queries run off the event loop, in parallel
const pool = new Db2Pool(4);

// read-only Db2 routes, always parameterized (never any SQL coming from the client)
async function db2Route(path: string, p: URLSearchParams): Promise<unknown> {
  const limit = Math.min(Math.max(Number(p.get("limite") ?? 20) || 20, 1), 500);
  switch (path) {
    case "/db2/systeme":
      return (await pool.query(`SELECT HOST_NAME, TOTAL_JOBS_IN_SYSTEM, ACTIVE_JOBS_IN_SYSTEM,
                                  ELAPSED_CPU_USED, SYSTEM_ASP_USED, MAIN_STORAGE_SIZE
                           FROM QSYS2.SYSTEM_STATUS_INFO_BASIC`))[0];
    case "/db2/tables":
      return await pool.query(
        `SELECT TABLE_NAME, TABLE_TYPE, TABLE_TEXT FROM QSYS2.SYSTABLES
         WHERE TABLE_SCHEMA = ? ORDER BY TABLE_NAME FETCH FIRST ${limit} ROWS ONLY`,
        [(p.get("schema") ?? "QSYS2").toUpperCase()],
      );
    case "/db2/colonnes":
      return await pool.query(
        `SELECT COLUMN_NAME, DATA_TYPE, LENGTH, NUMERIC_SCALE, IS_NULLABLE, COLUMN_TEXT
         FROM QSYS2.SYSCOLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION`,
        [(p.get("schema") ?? "").toUpperCase(), (p.get("table") ?? "").toUpperCase()],
      );
    case "/db2/travaux":
      return await pool.query(
        `SELECT JOB_NAME, JOB_TYPE, JOB_STATUS, SUBSYSTEM, ELAPSED_CPU_PERCENTAGE
         FROM TABLE(QSYS2.ACTIVE_JOB_INFO(CURRENT_USER_LIST_FILTER => ?))
         ORDER BY JOB_NAME FETCH FIRST ${limit} ROWS ONLY`,
        [(p.get("utilisateur") ?? "QSYS").toUpperCase()],
      );
    case "/db2/attente":
      // non-blocking demo: DLYJOB inside the QSQSRVR job
      await pool.execute(`CALL QSYS2.QCMDEXC('DLYJOB DLY(' CONCAT CAST(? AS VARCHAR(2)) CONCAT ')')`, [Math.min(Math.max(Number(p.get("secondes") ?? 1) || 1, 1), 10)]);
      return { attendu: true };
    case "/db2/pool":
      return pool.stats;
    default:
      return undefined;
  }
}

async function handleRequest(req: Request): Promise<Response> {
  const url = new URL(req.url);
  requestCount++;
  if (url.pathname === "/bonjour") {
    const name = url.searchParams.get("nom") ?? "world";
    return Response.json({ message: `Hello ${name}, from Deno on IBM i` });
  }
  if (url.pathname === "/deno-github") {
    // outbound HTTPS call (certificate verified) from IBM i
    const r = await fetch("https://api.github.com/repos/denoland/deno", {
      headers: { "user-agent": "deno-ibmi" },
    });
    const j = await r.json();
    return Response.json({ depot: j.full_name, etoiles: j.stargazers_count, maj: j.pushed_at });
  }
  if (url.pathname.startsWith("/db2/")) {
    const t0 = performance.now();
    try {
      const result = await db2Route(url.pathname, url.searchParams);
      if (result === undefined) return Response.json({ erreur: "unknown route" }, { status: 404 });
      return Response.json({ duree_ms: Math.round((performance.now() - t0) * 10) / 10, resultat: result });
    } catch (e) {
      const d = e instanceof Db2Error ? { sqlState: e.sqlState, sqlCode: e.sqlCode } : {};
      return Response.json({ erreur: (e as Error).message, ...d }, { status: 500 });
    }
  }
  return Response.json({
    service: "deno-ibmi",
    deno: Deno.version,
    build: Deno.build,
    pid: Deno.pid,
    demarrage: startedAt.toISOString(),
    maintenant: new Date().toISOString(),
    appels: requestCount,
    chemin: url.pathname,
    https: url.protocol === "https:",
    routes: ["/bonjour?nom=", "/deno-github", "/db2/systeme", "/db2/tables?schema=&limite=",
      "/db2/colonnes?schema=&table=", "/db2/travaux?utilisateur=&limite=",
      "/db2/attente?secondes=", "/db2/pool"],
  });
}

// HTTP (3081) and native Deno HTTPS (3444, rustls) with the certificate from
// /QOpenSys/opt/denoibmi/tls (local deno-ibmi CA); behind Apache, only the
// 127.0.0.1 listener will be kept.
const HOST = Deno.env.get("DENOWS_HOTE") ?? "0.0.0.0";
Deno.serve({ hostname: HOST, port: 3081 }, handleRequest);
const TLS = "/QOpenSys/opt/denoibmi/tls";
try {
  Deno.serve({
    hostname: HOST,
    port: 3444,
    cert: Deno.readTextFileSync(`${TLS}/serveur.crt`),
    key: Deno.readTextFileSync(`${TLS}/serveur.key`),
  }, handleRequest);
} catch (e) {
  console.error("ERROR: native HTTPS not started:", (e as Error).message);
}

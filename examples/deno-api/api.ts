// HTTPS CRUD API over Db2 for i, consumed by the React/Carbon application on LINUXBUILD
// (examples/ibmi-carbon). Runs under DENOAPP, port 3091.
//
// One connection PER IBM i USER PROFILE: POST /api/session { utilisateur, motDePasse } opens a
// Db2 connection under THAT profile (SQLConnect with user and password, QSQSRVR job running
// under its name) and returns a token. All reads and writes then go through this connection:
// IBM i security (authorities on DENOCRUD.CLIENTS) makes the decision.
// Only LINUXBUILD and IBMI are served (403 otherwise). Failed sign-ons are rate-limited per
// address (each failure counts towards QMAXSIGN and may disable the profile).
//
//   deno run --allow-net --allow-ffi --allow-sys --allow-read=/QOpenSys/opt/denoibmi/tls \
//            --allow-env=DENOAPI_CLIENTS api.ts
import { Db2, Db2Error } from "/QOpenSys/opt/denoibmi/deno-db2/db2.ts";

const PORT = 3091;
const TLS = "/QOpenSys/opt/denoibmi/tls";
const CLIENTS = new Set((Deno.env.get("DENOAPI_CLIENTS") ?? "192.0.2.16,127.0.0.1,192.0.2.82").split(","));
const IDLE_TIMEOUT_MS = 30 * 60_000; // session closed after 30 min without a request
const MAX_SESSIONS = 20;
const MAX_FAILED_SIGNONS = 3; // failed sign-ons per address per 5-minute window
const TABLE = "DENOCRUD.CLIENTS";

interface Session { db: Db2; user: string; lastSeen: number; openedAt: number }
const sessions = new Map<string, Session>();
const failedSignOns = new Map<string, number[]>();
const startedAt = Date.now();

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });

function closeSession(token: string) {
  const s = sessions.get(token);
  if (!s) return;
  sessions.delete(token);
  try { s.db.close(); } catch { /* already closed */ }
}

// clean up idle sessions
setInterval(() => {
  const cutoff = Date.now() - IDLE_TIMEOUT_MS;
  for (const [j, s] of sessions) if (s.lastSeen < cutoff) closeSession(j);
}, 60_000);

/** Db2 error → readable HTTP response (IBM i authority denied = 403). */
function db2ErrorResponse(e: unknown): Response {
  if (e instanceof Db2Error) {
    const status = ["42501", "42502"].includes(e.sqlState) || [-551, -552].includes(e.sqlCode) ? 403 : 400;
    return json({ erreur: e.message.replace(/^.*?\] /, ""), sqlState: e.sqlState, sqlCode: e.sqlCode }, status);
  }
  return json({ erreur: (e as Error).message }, 500);
}

// --- customer record validation ---
interface CustomerRecord { nom: string; ville: string; email: string; solde: number }
function validateCustomer(body: Record<string, unknown>): CustomerRecord | string {
  const nom = String(body.nom ?? "").trim();
  const ville = String(body.ville ?? "").trim();
  const email = String(body.email ?? "").trim();
  const solde = Number(body.solde ?? 0);
  if (!nom || nom.length > 60) return "name required, 60 characters at most";
  if (ville.length > 40) return "city: 40 characters at most";
  if (email.length > 80 || (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))) return "invalid e-mail address";
  if (!Number.isFinite(solde) || Math.abs(solde) >= 1e9) return "invalid balance";
  return { nom, ville, email, solde: Math.round(solde * 100) / 100 };
}

const COLUMNS = "ID, NOM, VILLE, EMAIL, SOLDE, MAJ_PAR, VARCHAR_FORMAT(MAJ_LE, 'YYYY-MM-DD HH24:MI:SS') AS MAJ_LE";

async function routeSession(req: Request, url: URL, s: Session): Promise<Response> {
  const db = s.db;
  const m = url.pathname.match(/^\/api\/clients\/(\d+)$/);
  const id = m ? Number(m[1]) : null;

  if (url.pathname === "/api/session" && req.method === "GET") {
    return json({ utilisateur: s.user, ouverte: new Date(s.openedAt).toISOString() });
  }
  if (url.pathname === "/api/systeme" && req.method === "GET") {
    const [l] = await db.queryAsync(`SELECT HOST_NAME, TOTAL_JOBS_IN_SYSTEM, ACTIVE_JOBS_IN_SYSTEM,
        ELAPSED_CPU_USED, SYSTEM_ASP_USED, SYSTEM_ASP_STORAGE, CURRENT_TEMPORARY_STORAGE,
        MAIN_STORAGE_SIZE, CONFIGURED_CPUS FROM QSYS2.SYSTEM_STATUS_INFO`);
    const m = Deno.memoryUsage();
    return json({
      ...l,
      deno: Deno.version.deno, v8: Deno.version.v8, hote: Deno.hostname(),
      uptimeSysteme: Deno.osUptime(), uptimeApi: Math.round((Date.now() - startedAt) / 1000),
      memoireApi: m.rss, sessions: sessions.size,
    });
  }

  // --- CRUD on DENOCRUD.CLIENTS ---
  if (url.pathname === "/api/clients" && req.method === "GET") {
    const q = (url.searchParams.get("q") ?? "").trim().toUpperCase();
    return json(await db.queryAsync(
      `SELECT ${COLUMNS} FROM ${TABLE}
        WHERE CAST(? AS VARCHAR(60)) = '' OR UPPER(NOM) LIKE '%' CONCAT CAST(? AS VARCHAR(60)) CONCAT '%'
           OR UPPER(VILLE) LIKE '%' CONCAT CAST(? AS VARCHAR(60)) CONCAT '%'
        ORDER BY NOM FETCH FIRST 500 ROWS ONLY`,
      [q, q, q],
    ));
  }
  if (url.pathname === "/api/clients" && req.method === "POST") {
    const f = validateCustomer(await req.json());
    if (typeof f === "string") return json({ erreur: f }, 400);
    const [l] = await db.queryAsync(
      `SELECT ID FROM FINAL TABLE (INSERT INTO ${TABLE} (NOM, VILLE, EMAIL, SOLDE)
         VALUES (CAST(? AS VARCHAR(60)), CAST(? AS VARCHAR(40)), CAST(? AS VARCHAR(80)), CAST(? AS DECIMAL(11, 2))))`,
      [f.nom, f.ville, f.email, f.solde],
    );
    const [created] = await db.queryAsync(`SELECT ${COLUMNS} FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [l.ID]);
    return json(created, 201);
  }
  if (id !== null && req.method === "GET") {
    const [l] = await db.queryAsync(`SELECT ${COLUMNS} FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [id]);
    return l ? json(l) : json({ erreur: "customer not found" }, 404);
  }
  if (id !== null && req.method === "PUT") {
    const f = validateCustomer(await req.json());
    if (typeof f === "string") return json({ erreur: f }, 400);
    const r = await db.executeAsync(
      `UPDATE ${TABLE} SET NOM = CAST(? AS VARCHAR(60)), VILLE = CAST(? AS VARCHAR(40)),
              EMAIL = CAST(? AS VARCHAR(80)), SOLDE = CAST(? AS DECIMAL(11, 2)), MAJ_PAR = USER
        WHERE ID = CAST(? AS INTEGER)`,
      [f.nom, f.ville, f.email, f.solde, id],
    );
    if (!r.rowsAffected) return json({ erreur: "customer not found" }, 404);
    const [l] = await db.queryAsync(`SELECT ${COLUMNS} FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [id]);
    return json(l);
  }
  if (id !== null && req.method === "DELETE") {
    const r = await db.executeAsync(`DELETE FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [id]);
    return r.rowsAffected ? new Response(null, { status: 204 }) : json({ erreur: "customer not found" }, 404);
  }
  return json({ erreur: "unknown route" }, 404);
}

async function signIn(req: Request, client: string): Promise<Response> {
  const now = Date.now();
  const recentFailures = (failedSignOns.get(client) ?? []).filter((t) => t > now - 5 * 60_000);
  if (recentFailures.length >= MAX_FAILED_SIGNONS) {
    return json({ erreur: "too many failed sign-ons, try again in 5 minutes" }, 429);
  }
  const { utilisateur: user, motDePasse: password } = await req.json().catch(() => ({}));
  const u = String(user ?? "").trim().toUpperCase();
  const p = String(password ?? "");
  if (!/^[A-Z0-9_$#@]{1,10}$/.test(u) || !p) return json({ erreur: "profile and password required" }, 400);
  if (sessions.size >= MAX_SESSIONS) return json({ erreur: "too many open sessions" }, 503);
  try {
    const db = new Db2({ user: u, password: p });
    const token = crypto.randomUUID() + crypto.randomUUID().replaceAll("-", "");
    sessions.set(token, { db, user: u, lastSeen: now, openedAt: now });
    failedSignOns.delete(client);
    console.log(new Date().toISOString(), `sign-on of ${u} from ${client}`);
    return json({ jeton: token, utilisateur: u }, 201);
  } catch (e) {
    recentFailures.push(now);
    failedSignOns.set(client, recentFailures);
    console.log(new Date().toISOString(), `failed sign-on of ${u} from ${client}`);
    // deliberately generic message: do not reveal whether the profile exists
    return json({ erreur: "wrong profile or password, or profile disabled", sqlState: (e as Db2Error).sqlState ?? "" }, 401);
  }
}

Deno.serve({
  port: PORT,
  hostname: "0.0.0.0",
  cert: Deno.readTextFileSync(`${TLS}/serveur.crt`),
  key: Deno.readTextFileSync(`${TLS}/serveur.key`),
}, async (req, info) => {
  const client = (info.remoteAddr as Deno.NetAddr).hostname;
  if (!CLIENTS.has(client)) return json({ erreur: "access denied" }, 403);
  const url = new URL(req.url);
  try {
    if (url.pathname === "/api/sante") return json({ ok: true, deno: Deno.version.deno, hote: Deno.hostname() });
    if (url.pathname === "/api/session" && req.method === "POST") return await signIn(req, client);
    const token = (req.headers.get("authorization") ?? "").replace(/^Bearer /, "");
    const s = sessions.get(token);
    if (!s) return json({ erreur: "missing or expired session" }, 401);
    s.lastSeen = Date.now();
    if (url.pathname === "/api/session" && req.method === "DELETE") {
      closeSession(token);
      return new Response(null, { status: 204 });
    }
    return await routeSession(req, url, s);
  } catch (e) {
    if (!(e instanceof Db2Error)) console.error(new Date().toISOString(), req.method, url.pathname, e);
    return db2ErrorResponse(e);
  }
});

// clean shutdown on SIGTERM: Db2 sessions are closed
Deno.addSignalListener("SIGTERM", () => {
  console.log(new Date().toISOString(), "SIGTERM: stopping,", sessions.size, "session(s) closed");
  for (const j of [...sessions.keys()]) closeSession(j);
  Deno.exit(0);
});

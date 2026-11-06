// HTTPS CRUD API over Db2 for i, consumed by the React/Carbon application on LINUXBUILD
// (essais/ibmi-carbon). Runs under DENOAPP, port 3091.
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
const INACTIVITE_MS = 30 * 60_000; // session closed after 30 min without a request
const MAX_SESSIONS = 20;
const MAX_ECHECS = 3; // failed sign-ons per address per 5-minute window
const TABLE = "DENOCRUD.CLIENTS";

interface Session { db: Db2; utilisateur: string; derniere: number; ouverte: number }
const sessions = new Map<string, Session>();
const echecs = new Map<string, number[]>();
const demarrage = Date.now();

const json = (corps: unknown, statut = 200) =>
  new Response(JSON.stringify(corps), {
    status: statut,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });

function fermer(jeton: string) {
  const s = sessions.get(jeton);
  if (!s) return;
  sessions.delete(jeton);
  try { s.db.close(); } catch { /* already closed */ }
}

// clean up idle sessions
setInterval(() => {
  const limite = Date.now() - INACTIVITE_MS;
  for (const [j, s] of sessions) if (s.derniere < limite) fermer(j);
}, 60_000);

/** Db2 error → readable HTTP response (IBM i authority denied = 403). */
function erreurDb2(e: unknown): Response {
  if (e instanceof Db2Error) {
    const statut = ["42501", "42502"].includes(e.sqlState) || [-551, -552].includes(e.sqlCode) ? 403 : 400;
    return json({ erreur: e.message.replace(/^.*?\] /, ""), sqlState: e.sqlState, sqlCode: e.sqlCode }, statut);
  }
  return json({ erreur: (e as Error).message }, 500);
}

// --- customer record validation ---
interface Fiche { nom: string; ville: string; email: string; solde: number }
function fiche(corps: Record<string, unknown>): Fiche | string {
  const nom = String(corps.nom ?? "").trim();
  const ville = String(corps.ville ?? "").trim();
  const email = String(corps.email ?? "").trim();
  const solde = Number(corps.solde ?? 0);
  if (!nom || nom.length > 60) return "nom obligatoire, 60 caractères au plus";
  if (ville.length > 40) return "ville : 40 caractères au plus";
  if (email.length > 80 || (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))) return "adresse e-mail invalide";
  if (!Number.isFinite(solde) || Math.abs(solde) >= 1e9) return "solde invalide";
  return { nom, ville, email, solde: Math.round(solde * 100) / 100 };
}

const COLONNES = "ID, NOM, VILLE, EMAIL, SOLDE, MAJ_PAR, VARCHAR_FORMAT(MAJ_LE, 'YYYY-MM-DD HH24:MI:SS') AS MAJ_LE";

async function routerSession(req: Request, url: URL, s: Session): Promise<Response> {
  const db = s.db;
  const m = url.pathname.match(/^\/api\/clients\/(\d+)$/);
  const id = m ? Number(m[1]) : null;

  if (url.pathname === "/api/session" && req.method === "GET") {
    return json({ utilisateur: s.utilisateur, ouverte: new Date(s.ouverte).toISOString() });
  }
  if (url.pathname === "/api/systeme" && req.method === "GET") {
    const [l] = await db.queryAsync(`SELECT HOST_NAME, TOTAL_JOBS_IN_SYSTEM, ACTIVE_JOBS_IN_SYSTEM,
        ELAPSED_CPU_USED, SYSTEM_ASP_USED, SYSTEM_ASP_STORAGE, CURRENT_TEMPORARY_STORAGE,
        MAIN_STORAGE_SIZE, CONFIGURED_CPUS FROM QSYS2.SYSTEM_STATUS_INFO`);
    const m = Deno.memoryUsage();
    return json({
      ...l,
      deno: Deno.version.deno, v8: Deno.version.v8, hote: Deno.hostname(),
      uptimeSysteme: Deno.osUptime(), uptimeApi: Math.round((Date.now() - demarrage) / 1000),
      memoireApi: m.rss, sessions: sessions.size,
    });
  }

  // --- CRUD on DENOCRUD.CLIENTS ---
  if (url.pathname === "/api/clients" && req.method === "GET") {
    const q = (url.searchParams.get("q") ?? "").trim().toUpperCase();
    return json(await db.queryAsync(
      `SELECT ${COLONNES} FROM ${TABLE}
        WHERE CAST(? AS VARCHAR(60)) = '' OR UPPER(NOM) LIKE '%' CONCAT CAST(? AS VARCHAR(60)) CONCAT '%'
           OR UPPER(VILLE) LIKE '%' CONCAT CAST(? AS VARCHAR(60)) CONCAT '%'
        ORDER BY NOM FETCH FIRST 500 ROWS ONLY`,
      [q, q, q],
    ));
  }
  if (url.pathname === "/api/clients" && req.method === "POST") {
    const f = fiche(await req.json());
    if (typeof f === "string") return json({ erreur: f }, 400);
    const [l] = await db.queryAsync(
      `SELECT ID FROM FINAL TABLE (INSERT INTO ${TABLE} (NOM, VILLE, EMAIL, SOLDE)
         VALUES (CAST(? AS VARCHAR(60)), CAST(? AS VARCHAR(40)), CAST(? AS VARCHAR(80)), CAST(? AS DECIMAL(11, 2))))`,
      [f.nom, f.ville, f.email, f.solde],
    );
    const [cree] = await db.queryAsync(`SELECT ${COLONNES} FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [l.ID]);
    return json(cree, 201);
  }
  if (id !== null && req.method === "GET") {
    const [l] = await db.queryAsync(`SELECT ${COLONNES} FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [id]);
    return l ? json(l) : json({ erreur: "client introuvable" }, 404);
  }
  if (id !== null && req.method === "PUT") {
    const f = fiche(await req.json());
    if (typeof f === "string") return json({ erreur: f }, 400);
    const r = await db.executeAsync(
      `UPDATE ${TABLE} SET NOM = CAST(? AS VARCHAR(60)), VILLE = CAST(? AS VARCHAR(40)),
              EMAIL = CAST(? AS VARCHAR(80)), SOLDE = CAST(? AS DECIMAL(11, 2)), MAJ_PAR = USER
        WHERE ID = CAST(? AS INTEGER)`,
      [f.nom, f.ville, f.email, f.solde, id],
    );
    if (!r.lignesTouchees) return json({ erreur: "client introuvable" }, 404);
    const [l] = await db.queryAsync(`SELECT ${COLONNES} FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [id]);
    return json(l);
  }
  if (id !== null && req.method === "DELETE") {
    const r = await db.executeAsync(`DELETE FROM ${TABLE} WHERE ID = CAST(? AS INTEGER)`, [id]);
    return r.lignesTouchees ? new Response(null, { status: 204 }) : json({ erreur: "client introuvable" }, 404);
  }
  return json({ erreur: "route inconnue" }, 404);
}

async function connexion(req: Request, client: string): Promise<Response> {
  const maintenant = Date.now();
  const recents = (echecs.get(client) ?? []).filter((t) => t > maintenant - 5 * 60_000);
  if (recents.length >= MAX_ECHECS) {
    return json({ erreur: "trop d'échecs de connexion, réessayez dans 5 minutes" }, 429);
  }
  const { utilisateur, motDePasse } = await req.json().catch(() => ({}));
  const u = String(utilisateur ?? "").trim().toUpperCase();
  const p = String(motDePasse ?? "");
  if (!/^[A-Z0-9_$#@]{1,10}$/.test(u) || !p) return json({ erreur: "profil et mot de passe obligatoires" }, 400);
  if (sessions.size >= MAX_SESSIONS) return json({ erreur: "trop de sessions ouvertes" }, 503);
  try {
    const db = new Db2({ utilisateur: u, motDePasse: p });
    const jeton = crypto.randomUUID() + crypto.randomUUID().replaceAll("-", "");
    sessions.set(jeton, { db, utilisateur: u, derniere: maintenant, ouverte: maintenant });
    echecs.delete(client);
    console.log(new Date().toISOString(), `connexion de ${u} depuis ${client}`);
    return json({ jeton, utilisateur: u }, 201);
  } catch (e) {
    recents.push(maintenant);
    echecs.set(client, recents);
    console.log(new Date().toISOString(), `échec de connexion ${u} depuis ${client}`);
    // deliberately generic message: do not reveal whether the profile exists
    return json({ erreur: "profil ou mot de passe incorrect, ou profil désactivé", sqlState: (e as Db2Error).sqlState ?? "" }, 401);
  }
}

Deno.serve({
  port: PORT,
  hostname: "0.0.0.0",
  cert: Deno.readTextFileSync(`${TLS}/serveur.crt`),
  key: Deno.readTextFileSync(`${TLS}/serveur.key`),
}, async (req, info) => {
  const client = (info.remoteAddr as Deno.NetAddr).hostname;
  if (!CLIENTS.has(client)) return json({ erreur: "accès refusé" }, 403);
  const url = new URL(req.url);
  try {
    if (url.pathname === "/api/sante") return json({ ok: true, deno: Deno.version.deno, hote: Deno.hostname() });
    if (url.pathname === "/api/session" && req.method === "POST") return await connexion(req, client);
    const jeton = (req.headers.get("authorization") ?? "").replace(/^Bearer /, "");
    const s = sessions.get(jeton);
    if (!s) return json({ erreur: "session absente ou expirée" }, 401);
    s.derniere = Date.now();
    if (url.pathname === "/api/session" && req.method === "DELETE") {
      fermer(jeton);
      return new Response(null, { status: 204 });
    }
    return await routerSession(req, url, s);
  } catch (e) {
    if (!(e instanceof Db2Error)) console.error(new Date().toISOString(), req.method, url.pathname, e);
    return erreurDb2(e);
  }
});

// clean shutdown on SIGTERM: Db2 sessions are closed
Deno.addSignalListener("SIGTERM", () => {
  console.log(new Date().toISOString(), "SIGTERM : arrêt,", sessions.size, "session(s) fermée(s)");
  for (const j of [...sessions.keys()]) fermer(j);
  Deno.exit(0);
});

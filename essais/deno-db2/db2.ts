// Db2 for i access from Deno, through the PASE SQL CLI (libdb400.a), via FFI.
// Same approach as idb-connector (the IBM Node.js driver): CLI in UTF-8
// (SQLOverrideCCSID400(1208)), server mode (one connection = one QSQSRVR job),
// columns fetched as characters and then converted.
//
//   import { Db2 } from "./db2.ts";
//   const db = new Db2();                       // *LOCAL, current job user profile
//   const lignes = db.query("SELECT ... WHERE X = ?", ["valeur"]);
//   db.close();
//
// Run with: deno run --allow-ffi ...

const LIB = "/QOpenSys/usr/lib/libdb400.a(shr_64.o)";

// C types of the 64-bit PASE CLI: handles and lengths are int (32 bits)
const cli = Deno.dlopen(LIB, {
  SQLOverrideCCSID400: { parameters: ["i32"], result: "i32" },
  SQLAllocEnv: { parameters: ["buffer"], result: "i32" },
  SQLSetEnvAttr: { parameters: ["i32", "i32", "buffer", "i32"], result: "i32" },
  SQLAllocConnect: { parameters: ["i32", "buffer"], result: "i32" },
  SQLConnect: { parameters: ["i32", "buffer", "i16", "buffer", "i16", "buffer", "i16"], result: "i32" },
  SQLSetConnectAttr: { parameters: ["i32", "i32", "buffer", "i32"], result: "i32" },
  SQLAllocStmt: { parameters: ["i32", "buffer"], result: "i32" },
  SQLPrepare: { parameters: ["i32", "buffer", "i32"], result: "i32" },
  SQLExecute: { parameters: ["i32"], result: "i32" },
  SQLExecDirect: { parameters: ["i32", "buffer", "i32"], result: "i32" },
  SQLNumResultCols: { parameters: ["i32", "buffer"], result: "i32" },
  SQLDescribeCol: {
    parameters: ["i32", "i16", "buffer", "i16", "buffer", "buffer", "buffer", "buffer", "buffer"],
    result: "i32",
  },
  SQLBindCol: { parameters: ["i32", "i16", "i16", "buffer", "i32", "buffer"], result: "i32" },
  SQLGetData: { parameters: ["i32", "i16", "i16", "buffer", "i32", "buffer"], result: "i32" },
  SQLFetch: { parameters: ["i32"], result: "i32" },
  SQLRowCount: { parameters: ["i32", "buffer"], result: "i32" },
  SQLBindParameter: {
    parameters: ["i32", "i16", "i16", "i16", "i16", "i32", "i16", "buffer", "i32", "buffer"],
    result: "i32",
  },
  SQLGetDiagRec: {
    parameters: ["i16", "i32", "i16", "buffer", "buffer", "buffer", "i16", "buffer"],
    result: "i32",
  },
  SQLFreeStmt: { parameters: ["i32", "i16"], result: "i32" },
  SQLEndTran: { parameters: ["i16", "i32", "i16"], result: "i32" },
  SQLDisconnect: { parameters: ["i32"], result: "i32" },
  SQLFreeConnect: { parameters: ["i32"], result: "i32" },
});
const f = cli.symbols;

// same functions in non-blocking mode (run on a Deno worker thread, return a promise)
const cliAsync = Deno.dlopen(LIB, {
  SQLExecDirect: { parameters: ["i32", "buffer", "i32"], result: "i32", nonblocking: true },
  SQLExecute: { parameters: ["i32"], result: "i32", nonblocking: true },
});
const fa = cliAsync.symbols;

// Constants from sqlcli.h (sqlcli-devel)
const SQL_SUCCESS = 0, SQL_SUCCESS_WITH_INFO = 1, SQL_NO_DATA = 100;
const SQL_NTS = -3, SQL_NULL_DATA = -1, SQL_TRUE = 1, SQL_DROP = 1;
const SQL_HANDLE_ENV = 1, SQL_HANDLE_DBC = 2, SQL_HANDLE_STMT = 3;
const SQL_ATTR_SERVER_MODE = 10004, SQL_ATTR_NON_HEXCCSID = 10203;
const SQL_ATTR_DATE_FMT = 10020, SQL_ATTR_TIME_FMT = 10022, SQL_FMT_ISO = 1;
const SQL_ATTR_AUTOCOMMIT = 10003, SQL_ATTR_DBC_SYS_NAMING = 10004;
const SQL_ATTR_DBC_DEFAULT_LIB = 10005, SQL_COMMIT = 0, SQL_ROLLBACK = 1;
const SQL_C_CHAR = 1, SQL_C_BINARY = -2, SQL_PARAM_INPUT = 1, SQL_VARCHAR = 12;
const T = {
  CHAR: 1, NUMERIC: 2, DECIMAL: 3, INTEGER: 4, SMALLINT: 5, FLOAT: 6, REAL: 7,
  DOUBLE: 8, VARCHAR: 12, BLOB: 13, CLOB: 14, DBCLOB: 15, BIGINT: 19,
  GRAPHIC: 95, VARGRAPHIC: 96, BINARY: -2, VARBINARY: -3, DECFLOAT: -360, XML: -370,
} as const;

const enc = new TextEncoder();
const dec = new TextDecoder();
const cz = (s: string) => enc.encode(s + "\0");
// the CLI sometimes returns a length covering the whole buffer: cut at the first \0
const jusquauNul = (b: Uint8Array) => {
  const i = b.indexOf(0);
  return i < 0 ? b : b.subarray(0, i);
};
const i32 = (v = 0) => new Int32Array([v]);

export class Db2Error extends Error {
  constructor(message: string, public sqlState: string, public sqlCode: number) {
    super(message);
    this.name = "Db2Error";
  }
}

function diag(type: number, handle: number, quoi: string): Db2Error {
  const state = new Uint8Array(6), code = i32(), msg = new Uint8Array(1024), len = new Int16Array(1);
  const rc = f.SQLGetDiagRec(type, handle, 1, state, code, msg, msg.length, len);
  if (rc !== SQL_SUCCESS && rc !== SQL_SUCCESS_WITH_INFO) {
    return new Db2Error(`${quoi} : erreur CLI sans diagnostic`, "", 0);
  }
  const etat = dec.decode(state.subarray(0, 5));
  const texte = dec.decode(jusquauNul(msg.subarray(0, Math.min(len[0], msg.length)))).trim();
  return new Db2Error(`${quoi} : [SQLSTATE ${etat}, SQLCODE ${code[0]}] ${texte}`, etat, code[0]);
}

function verifier(rc: number, type: number, handle: number, quoi: string) {
  if (rc !== SQL_SUCCESS && rc !== SQL_SUCCESS_WITH_INFO) throw diag(type, handle, quoi);
}

// CLI environment: one per process (as in idb-connector)
let henv = 0;
function environnement(): number {
  if (henv) return henv;
  f.SQLOverrideCCSID400(1208); // UTF-8, before SQLAllocEnv
  const h = i32();
  const rc = f.SQLAllocEnv(h);
  if (rc !== SQL_SUCCESS) throw new Db2Error(`SQLAllocEnv a échoué (${rc})`, "", rc);
  henv = h[0];
  const vrai = i32(SQL_TRUE), iso = i32(SQL_FMT_ISO);
  verifier(f.SQLSetEnvAttr(henv, SQL_ATTR_SERVER_MODE, vrai, 0), SQL_HANDLE_ENV, henv, "mode serveur");
  f.SQLSetEnvAttr(henv, SQL_ATTR_NON_HEXCCSID, vrai, 0);
  f.SQLSetEnvAttr(henv, SQL_ATTR_DATE_FMT, iso, 0);
  f.SQLSetEnvAttr(henv, SQL_ATTR_TIME_FMT, iso, 0);
  return henv;
}

export type Valeur = string | number | boolean | null | Uint8Array;
export type Ligne = Record<string, Valeur>;
export interface Resultat {
  lignes: Ligne[];
  lignesTouchees: number;
}

export interface Db2Options {
  base?: string; // defaults to "*LOCAL"
  utilisateur?: string;
  motDePasse?: string;
  bibliotheque?: string; // default schema
  nommageSysteme?: boolean; // *SYS naming (LIB/FILE, *LIBL) instead of *SQL
  autocommit?: boolean; // defaults to true
}

interface Colonne {
  nom: string;
  type: number;
  precision: number;
  echelle: number;
  tampon?: Uint8Array;
  longueur: Int32Array;
}

// Size of the read buffer, in UTF-8 characters, for a bound column
function tailleTampon(c: Colonne): number {
  switch (c.type) {
    case T.SMALLINT: case T.INTEGER: case T.BIGINT: return 22;
    case T.REAL: case T.FLOAT: case T.DOUBLE: case T.DECFLOAT: return 64;
    case T.DECIMAL: case T.NUMERIC: return c.precision + 4;
    case T.BINARY: case T.VARBINARY: return c.precision + 1;
    case T.GRAPHIC: case T.VARGRAPHIC: return c.precision * 4 + 1;
    default: return c.precision * 4 + 1; // CHAR/VARCHAR/DATE/TIME/TIMESTAMP (EBCDIC -> UTF-8: up to 3-4 bytes)
  }
}

const estLob = (t: number) => t === T.CLOB || t === T.BLOB || t === T.DBCLOB || t === T.XML;
const estBinaire = (t: number) => t === T.BINARY || t === T.VARBINARY || t === T.BLOB;

function convertir(c: Colonne, octets: Uint8Array): Valeur {
  if (estBinaire(c.type)) return octets.slice();
  const s = dec.decode(jusquauNul(octets));
  switch (c.type) {
    case T.SMALLINT: case T.INTEGER: return Number(s);
    case T.BIGINT: { const n = Number(s); return Number.isSafeInteger(n) ? n : s; }
    case T.REAL: case T.FLOAT: case T.DOUBLE: return Number(s);
    case T.DECIMAL: case T.NUMERIC:
      // exact in JS up to 15 digits, otherwise a string so that nothing is lost
      return c.precision <= 15 ? Number(s) : s.trim();
    case T.CHAR: case T.GRAPHIC: return s.trimEnd();
    default: return s;
  }
}

export class Db2 {
  #hdbc = 0;

  constructor(options: Db2Options = {}) {
    const env = environnement();
    const h = i32();
    verifier(f.SQLAllocConnect(env, h), SQL_HANDLE_ENV, env, "SQLAllocConnect");
    this.#hdbc = h[0];
    if (options.nommageSysteme) {
      f.SQLSetConnectAttr(this.#hdbc, SQL_ATTR_DBC_SYS_NAMING, i32(SQL_TRUE), 0);
    }
    if (options.autocommit !== false) {
      f.SQLSetConnectAttr(this.#hdbc, SQL_ATTR_AUTOCOMMIT, i32(SQL_TRUE), 0);
    }
    if (options.bibliotheque) {
      const lib = cz(options.bibliotheque);
      f.SQLSetConnectAttr(this.#hdbc, SQL_ATTR_DBC_DEFAULT_LIB, lib, SQL_NTS);
    }
    const u = options.utilisateur ? cz(options.utilisateur) : null;
    const p = options.motDePasse ? cz(options.motDePasse) : null;
    const rc = f.SQLConnect(this.#hdbc, cz(options.base ?? "*LOCAL"), SQL_NTS, u, SQL_NTS, p, SQL_NTS);
    if (rc !== SQL_SUCCESS && rc !== SQL_SUCCESS_WITH_INFO) {
      const e = diag(SQL_HANDLE_DBC, this.#hdbc, "SQLConnect");
      f.SQLFreeConnect(this.#hdbc);
      this.#hdbc = 0;
      throw e;
    }
  }

  // queue: a CLI connection runs only one statement at a time
  #file: Promise<unknown> = Promise.resolve();

  /** Runs a statement; returns the rows (SELECT) or { lignesTouchees }. Blocks the event loop. */
  execute(sql: string, params: Valeur[] = []): Resultat {
    const p = this.#preparer(sql, params);
    try {
      verifier(p.direct ? f.SQLExecDirect(p.st, p.texte, SQL_NTS) : f.SQLExecute(p.st),
        SQL_HANDLE_STMT, p.st, p.direct ? "SQLExecDirect" : "SQLExecute");
      return this.#lire(p.st);
    } finally {
      f.SQLFreeStmt(p.st, SQL_DROP);
    }
  }

  /**
   * Non-blocking variant: SQL execution (SQLExecDirect / SQLExecute) runs on a
   * Deno worker thread, so the event loop keeps serving other requests.
   * Fetching the rows stays synchronous (fast, the data is already there).
   */
  executeAsync(sql: string, params: Valeur[] = []): Promise<Resultat> {
    const tache = this.#file.then(async () => {
      const p = this.#preparer(sql, params);
      try {
        const rc = p.direct ? await fa.SQLExecDirect(p.st, p.texte, SQL_NTS) : await fa.SQLExecute(p.st);
        verifier(rc, SQL_HANDLE_STMT, p.st, p.direct ? "SQLExecDirect" : "SQLExecute");
        return this.#lire(p.st);
      } finally {
        f.SQLFreeStmt(p.st, SQL_DROP);
        p.garde.length = 0; // the buffers were kept alive until execution finished
      }
    });
    this.#file = tache.catch(() => {});
    return tache;
  }

  /** Rows of a SELECT, without blocking the event loop. */
  async queryAsync(sql: string, params: Valeur[] = []): Promise<Ligne[]> {
    return (await this.executeAsync(sql, params)).lignes;
  }

  // statement allocation, preparation and parameter binding
  #preparer(sql: string, params: Valeur[]) {
    if (!this.#hdbc) throw new Db2Error("connexion fermée", "08003", 0);
    const hs = i32();
    verifier(f.SQLAllocStmt(this.#hdbc, hs), SQL_HANDLE_DBC, this.#hdbc, "SQLAllocStmt");
    const st = hs[0];
    const texte = cz(sql);
    // parameter buffers must stay alive until execution finishes
    const garde: unknown[] = [texte];
    if (params.length === 0) return { st, texte, garde, direct: true };
    try {
      verifier(f.SQLPrepare(st, texte, SQL_NTS), SQL_HANDLE_STMT, st, "SQLPrepare");
      params.forEach((v, i) => {
        const ind = i32();
        let tampon: Uint8Array;
        if (v === null || v === undefined) {
          tampon = new Uint8Array(1);
          ind[0] = SQL_NULL_DATA;
        } else {
          const t = typeof v === "boolean" ? (v ? "1" : "0") : v instanceof Uint8Array ? dec.decode(v) : String(v);
          tampon = cz(t);
          ind[0] = SQL_NTS;
        }
        garde.push(tampon, ind);
        verifier(
          f.SQLBindParameter(st, i + 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR,
            Math.max(tampon.length - 1, 1), 0, tampon, tampon.length, ind),
          SQL_HANDLE_STMT, st, `SQLBindParameter ${i + 1}`,
        );
      });
    } catch (e) {
      f.SQLFreeStmt(st, SQL_DROP);
      throw e;
    }
    return { st, texte, garde, direct: false };
  }

  // column description and row fetching after execution
  #lire(st: number): Resultat {
    {
      const nb = new Int16Array(1);
      verifier(f.SQLNumResultCols(st, nb), SQL_HANDLE_STMT, st, "SQLNumResultCols");
      if (nb[0] === 0) {
        const n = i32();
        f.SQLRowCount(st, n);
        return { lignes: [], lignesTouchees: n[0] };
      }

      // describe and bind the columns
      const colonnes: Colonne[] = [];
      for (let i = 1; i <= nb[0]; i++) {
        const nom = new Uint8Array(256), lnom = new Int16Array(1), type = new Int16Array(1);
        const prec = i32(), ech = new Int16Array(1), nul = new Int16Array(1);
        verifier(f.SQLDescribeCol(st, i, nom, nom.length, lnom, type, prec, ech, nul),
          SQL_HANDLE_STMT, st, `SQLDescribeCol ${i}`);
        const c: Colonne = {
          nom: dec.decode(jusquauNul(nom.subarray(0, lnom[0]))),
          type: type[0], precision: prec[0], echelle: ech[0], longueur: i32(),
        };
        if (!estLob(c.type)) {
          c.tampon = new Uint8Array(tailleTampon(c));
          verifier(f.SQLBindCol(st, i, estBinaire(c.type) ? SQL_C_BINARY : SQL_C_CHAR, c.tampon, c.tampon.length, c.longueur),
            SQL_HANDLE_STMT, st, `SQLBindCol ${i}`);
        }
        colonnes.push(c);
      }

      const lignes: Ligne[] = [];
      for (;;) {
        const rc = f.SQLFetch(st);
        if (rc === SQL_NO_DATA) break;
        verifier(rc, SQL_HANDLE_STMT, st, "SQLFetch");
        const ligne: Ligne = {};
        colonnes.forEach((c, i) => {
          if (c.tampon) {
            const l = c.longueur[0];
            ligne[c.nom] = l === SQL_NULL_DATA ? null : convertir(c, c.tampon.subarray(0, Math.min(l, c.tampon.length)));
          } else {
            ligne[c.nom] = this.#lireLob(st, i + 1, c);
          }
        });
        lignes.push(ligne);
      }
      return { lignes, lignesTouchees: lignes.length };
    }
  }

  // LOB: read in chunks with SQLGetData
  #lireLob(st: number, col: number, c: Colonne): Valeur {
    const binaire = c.type === T.BLOB;
    const morceaux: Uint8Array[] = [];
    const tampon = new Uint8Array(65536), lg = i32();
    for (;;) {
      const rc = f.SQLGetData(st, col, binaire ? SQL_C_BINARY : SQL_C_CHAR, tampon, tampon.length, lg);
      if (rc === SQL_NO_DATA) break;
      verifier(rc, SQL_HANDLE_STMT, st, `SQLGetData ${col}`);
      if (lg[0] === SQL_NULL_DATA) return null;
      // SUCCESS_WITH_INFO = truncated, more data remains; in character mode the buffer ends with \0
      const utile = rc === SQL_SUCCESS_WITH_INFO ? tampon.length - (binaire ? 0 : 1) : Math.min(lg[0], tampon.length);
      morceaux.push(tampon.slice(0, utile));
      if (rc === SQL_SUCCESS) break;
    }
    const tout = new Uint8Array(morceaux.reduce((n, m) => n + m.length, 0));
    let o = 0;
    for (const m of morceaux) { tout.set(m, o); o += m.length; }
    return binaire ? tout : dec.decode(tout);
  }

  /** Shortcut: rows of a SELECT. */
  query(sql: string, params: Valeur[] = []): Ligne[] {
    return this.execute(sql, params).lignes;
  }

  commit() { verifier(f.SQLEndTran(SQL_HANDLE_DBC, this.#hdbc, SQL_COMMIT), SQL_HANDLE_DBC, this.#hdbc, "COMMIT"); }
  rollback() { verifier(f.SQLEndTran(SQL_HANDLE_DBC, this.#hdbc, SQL_ROLLBACK), SQL_HANDLE_DBC, this.#hdbc, "ROLLBACK"); }

  close() {
    if (!this.#hdbc) return;
    f.SQLDisconnect(this.#hdbc);
    f.SQLFreeConnect(this.#hdbc);
    this.#hdbc = 0;
  }
}

/**
 * Connection pool: concurrent queries run in parallel on several connections
 * (each one in its own QSQSRVR job), without blocking Deno.
 *   const pool = new Db2Pool(4);
 *   const lignes = await pool.query("SELECT ...", [param]);
 */
export class Db2Pool {
  #libres: Db2[] = [];
  #toutes: Db2[] = [];
  #attente: ((db: Db2) => void)[] = [];

  constructor(public taille = 4, private options: Db2Options = {}) {}

  async #prendre(): Promise<Db2> {
    const db = this.#libres.pop();
    if (db) return db;
    if (this.#toutes.length < this.taille) {
      const nouvelle = new Db2(this.options);
      this.#toutes.push(nouvelle);
      return nouvelle;
    }
    return await new Promise<Db2>((ok) => this.#attente.push(ok));
  }

  #rendre(db: Db2) {
    const suivant = this.#attente.shift();
    if (suivant) suivant(db);
    else this.#libres.push(db);
  }

  /** Lends a connection for the duration of fn (multi-statement transactions). */
  async avec<R>(fn: (db: Db2) => Promise<R> | R): Promise<R> {
    const db = await this.#prendre();
    try {
      return await fn(db);
    } finally {
      this.#rendre(db);
    }
  }

  execute(sql: string, params: Valeur[] = []): Promise<Resultat> {
    return this.avec((db) => db.executeAsync(sql, params));
  }

  query(sql: string, params: Valeur[] = []): Promise<Ligne[]> {
    return this.avec((db) => db.queryAsync(sql, params));
  }

  get stats() {
    return { taille: this.taille, ouvertes: this.#toutes.length, libres: this.#libres.length, enAttente: this.#attente.length };
  }

  close() {
    for (const db of this.#toutes) db.close();
    this.#toutes = [];
    this.#libres = [];
  }
}

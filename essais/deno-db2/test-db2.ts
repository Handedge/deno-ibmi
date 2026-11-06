// Test bench for the db2.ts module on IBM i: deno run --allow-ffi test-db2.ts
import { Db2, Db2Error } from "./db2.ts";

const t0 = performance.now();
const db = new Db2();
console.log(`connexion : ${(performance.now() - t0).toFixed(1)} ms`);

function essai(titre: string, fn: () => unknown) {
  const t = performance.now();
  try {
    const r = fn();
    console.log(`== ${titre} (${(performance.now() - t).toFixed(1)} ms)`);
    console.log(JSON.stringify(r, null, 1).slice(0, 900));
  } catch (e) {
    console.log(`== ${titre} : ${e instanceof Db2Error ? "Db2Error" : "ERREUR"} ${(e as Error).message}`);
  }
}

essai("registres spéciaux", () =>
  db.query("VALUES (CURRENT USER, CURRENT SERVER, CURRENT TIMESTAMP, CURRENT DATE, CURRENT TIME)"));

essai("UTF-8 aller-retour", () =>
  db.query("VALUES (CAST(? AS VARCHAR(50) CCSID 1208), CAST('Été à Noël : 10 €' AS VARCHAR(40)))", ["Ça marche : éèàçù €"]));

essai("types numériques", () =>
  db.query(`VALUES (CAST(42 AS SMALLINT), CAST(-123456 AS INTEGER), CAST(9007199254740993 AS BIGINT),
                    CAST(12345.67 AS DECIMAL(9,2)), CAST(1234567890123456789.12 AS DECIMAL(21,2)),
                    CAST(3.14159 AS DOUBLE), CAST(NULL AS INTEGER))`));

essai("paramètres", () =>
  db.query(`SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM QSYS2.SYSTABLES
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME LIKE ? ORDER BY TABLE_NAME FETCH FIRST 3 ROWS ONLY`, ["QSYS2", "SYS%"]));

essai("service SQL IBM i", () =>
  db.query(`SELECT HOST_NAME, TOTAL_JOBS_IN_SYSTEM, ELAPSED_CPU_USED, MAIN_STORAGE_SIZE
            FROM QSYS2.SYSTEM_STATUS_INFO`));

essai("CLOB", () =>
  db.query("VALUES (REPEAT(CAST('abc' AS CLOB(1M)), 30000))").map((l) => Object.values(l).map((v) => String(v).length)));

essai("erreur attendue (table absente)", () => db.query("SELECT * FROM QTEMP.NEXISTEPAS"));

essai("DDL / INSERT / UPDATE / SELECT", () => {
  db.execute("DECLARE GLOBAL TEMPORARY TABLE ESSAI (ID INTEGER, NOM VARCHAR(30), MONTANT DECIMAL(9,2)) WITH REPLACE");
  for (const [id, nom, m] of [[1, "Rémi", "10.50"], [2, "Zoé", "99.99"], [3, null, "0"]]) {
    db.execute("INSERT INTO SESSION.ESSAI VALUES (?, ?, ?)", [id, nom, m]);
  }
  const maj = db.execute("UPDATE SESSION.ESSAI SET MONTANT = MONTANT * 2 WHERE ID <= ?", [2]);
  return { majTouchees: maj.lignesTouchees, lignes: db.query("SELECT * FROM SESSION.ESSAI ORDER BY ID") };
});

const t1 = performance.now();
let n = 0;
for (let i = 0; i < 200; i++) n += db.query("VALUES (CAST(? AS INTEGER))", [i]).length;
console.log(`== 200 requêtes préparées : ${(performance.now() - t1).toFixed(0)} ms (${n} lignes)`);

db.close();
console.log("FIN");

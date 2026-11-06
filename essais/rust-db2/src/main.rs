//! Example of a CL → Rust → Db2 for i flow on IBM i.
//!
//! The program reads the tables of a schema (QSYS2.SYSTABLES) through the PASE SQL CLI
//! (libdb400.a), computes a value in Rust, then writes each row to QTEMP/RUSTTABLES.
//! Called by a CL program through QP2SHELL, it runs in THE SAME JOB as the CL: the *LOCAL
//! connection without server mode therefore shares the QTEMP of the CL, which then shows the result.
//!
//! Usage: rust-db2 <schema> [maximum number of tables]     (defaults: QSYS2 and 10)
//! Exit code: 0 on success, 1 on SQL error (message on standard error).

use std::ffi::CString;
use std::os::raw::{c_char, c_int, c_short};
use std::process::ExitCode;

/// PASE CLI handles: 32-bit integers, even in 64-bit mode.
type Handle = c_int;

const SQL_SUCCESS: c_int = 0;
const SQL_SUCCESS_WITH_INFO: c_int = 1;
const SQL_NO_DATA_FOUND: c_int = 100;
const SQL_NTS: c_int = -3;
const SQL_C_CHAR: c_short = 1;
const SQL_NULL_DATA: c_int = -1;
const SQL_DROP: c_short = 1;

#[link(name = "db400")]
extern "C" {
    fn SQLOverrideCCSID400(ccsid: c_int) -> c_int;
    fn SQLAllocEnv(henv: *mut Handle) -> c_int;
    fn SQLAllocConnect(henv: Handle, hdbc: *mut Handle) -> c_int;
    fn SQLConnect(
        hdbc: Handle,
        base: *const c_char,
        lg_base: c_short,
        utilisateur: *const c_char,
        lg_utilisateur: c_short,
        mot_de_passe: *const c_char,
        lg_mot_de_passe: c_short,
    ) -> c_int;
    fn SQLAllocStmt(hdbc: Handle, hstmt: *mut Handle) -> c_int;
    fn SQLExecDirect(hstmt: Handle, sql: *const c_char, lg: c_int) -> c_int;
    fn SQLFetch(hstmt: Handle) -> c_int;
    fn SQLGetData(
        hstmt: Handle,
        colonne: c_short,
        type_c: c_short,
        tampon: *mut c_char,
        lg_tampon: c_int,
        indicateur: *mut c_int,
    ) -> c_int;
    fn SQLError(
        henv: Handle,
        hdbc: Handle,
        hstmt: Handle,
        etat: *mut c_char,
        code_natif: *mut c_int,
        message: *mut c_char,
        lg_max: c_short,
        lg_message: *mut c_short,
    ) -> c_int;
    fn SQLFreeStmt(hstmt: Handle, option: c_short) -> c_int;
    fn SQLDisconnect(hdbc: Handle) -> c_int;
    fn SQLFreeConnect(hdbc: Handle) -> c_int;
    fn SQLFreeEnv(henv: Handle) -> c_int;
}

/// Minimal Db2 connection: environment, *LOCAL connection under the job user profile.
struct Db2 {
    henv: Handle,
    hdbc: Handle,
}

impl Db2 {
    fn connecter() -> Result<Db2, String> {
        // SAFETY: CLI calls with valid handles and C strings.
        unsafe {
            SQLOverrideCCSID400(1208); // UTF-8 data exchange, before SQLAllocEnv
            let mut henv = 0;
            if SQLAllocEnv(&mut henv) != SQL_SUCCESS {
                return Err("SQLAllocEnv a échoué".into());
            }
            let mut hdbc = 0;
            if SQLAllocConnect(henv, &mut hdbc) != SQL_SUCCESS {
                return Err("SQLAllocConnect a échoué".into());
            }
            let base = CString::new("*LOCAL").unwrap();
            // NULL user and password = job user profile (an empty string would be
            // understood as user "*N": SQL7022)
            let rc = SQLConnect(hdbc, base.as_ptr(), SQL_NTS as c_short, std::ptr::null(), 0,
                                std::ptr::null(), 0);
            let db = Db2 { henv, hdbc };
            if rc != SQL_SUCCESS && rc != SQL_SUCCESS_WITH_INFO {
                return Err(db.erreur(0, "SQLConnect"));
            }
            Ok(db)
        }
    }

    /// SQL error text (SQLSTATE, SQLCODE and message).
    fn erreur(&self, hstmt: Handle, quoi: &str) -> String {
        let mut etat = [0 as c_char; 6];
        let mut code = 0;
        let mut msg = [0 as c_char; 512];
        let mut lg: c_short = 0;
        // SAFETY: buffers sized here, maximum length passed to the CLI.
        unsafe {
            SQLError(self.henv, self.hdbc, hstmt, etat.as_mut_ptr(), &mut code, msg.as_mut_ptr(),
                     msg.len() as c_short, &mut lg);
        }
        format!("{quoi} : SQLSTATE {} SQLCODE {code} : {}", texte(&etat), texte(&msg))
    }

    /// Runs a query and returns all its rows (columns fetched as characters).
    fn lignes(&self, sql: &str, nb_colonnes: usize) -> Result<Vec<Vec<Option<String>>>, String> {
        let requete = CString::new(sql).map_err(|e| e.to_string())?;
        // SAFETY: statement handle allocated and freed here, buffers sized here.
        unsafe {
            let mut st = 0;
            SQLAllocStmt(self.hdbc, &mut st);
            let rc = SQLExecDirect(st, requete.as_ptr(), SQL_NTS);
            if rc != SQL_SUCCESS && rc != SQL_SUCCESS_WITH_INFO {
                let e = self.erreur(st, "SQLExecDirect");
                SQLFreeStmt(st, SQL_DROP);
                return Err(e);
            }
            let mut res = Vec::new();
            while SQLFetch(st) != SQL_NO_DATA_FOUND {
                let mut ligne = Vec::with_capacity(nb_colonnes);
                for col in 1..=nb_colonnes {
                    let mut tampon = [0 as c_char; 1024];
                    let mut ind = 0;
                    SQLGetData(st, col as c_short, SQL_C_CHAR, tampon.as_mut_ptr(), tampon.len() as c_int, &mut ind);
                    ligne.push(if ind == SQL_NULL_DATA { None } else { Some(texte(&tampon)) });
                }
                res.push(ligne);
            }
            SQLFreeStmt(st, SQL_DROP);
            Ok(res)
        }
    }

    /// Runs a statement that returns no result set (INSERT, CREATE…).
    fn executer(&self, sql: &str) -> Result<(), String> {
        let requete = CString::new(sql).map_err(|e| e.to_string())?;
        // SAFETY: statement handle allocated and freed here.
        unsafe {
            let mut st = 0;
            SQLAllocStmt(self.hdbc, &mut st);
            let rc = SQLExecDirect(st, requete.as_ptr(), SQL_NTS);
            let r = if rc == SQL_SUCCESS || rc == SQL_SUCCESS_WITH_INFO { Ok(()) } else { Err(self.erreur(st, "SQLExecDirect")) };
            SQLFreeStmt(st, SQL_DROP);
            r
        }
    }
}

impl Drop for Db2 {
    fn drop(&mut self) {
        // SAFETY: handles allocated by connecter().
        unsafe {
            SQLDisconnect(self.hdbc);
            SQLFreeConnect(self.hdbc);
            SQLFreeEnv(self.henv);
        }
    }
}

/// Null-terminated C string to String, trailing blanks removed.
fn texte(tampon: &[c_char]) -> String {
    let octets: Vec<u8> = tampon.iter().take_while(|&&c| c != 0).map(|&c| c as u8).collect();
    String::from_utf8_lossy(&octets).trim_end().to_string()
}

/// SQL literal: single quotes doubled.
fn litteral(s: &str) -> String {
    format!("'{}'", s.replace('\'', "''"))
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let schema = args.get(1).map(|s| s.trim().to_uppercase()).filter(|s| !s.is_empty()).unwrap_or("QSYS2".into());
    let limite: u32 = args.get(2).and_then(|s| s.trim().parse().ok()).unwrap_or(10);

    let resultat = (|| -> Result<usize, String> {
        let db = Db2::connecter()?;
        let tables = db.lignes(
            &format!(
                "SELECT TABLE_NAME, TABLE_TYPE, COALESCE(TABLE_TEXT, '') FROM QSYS2.SYSTABLES \
                 WHERE TABLE_SCHEMA = {} ORDER BY TABLE_NAME FETCH FIRST {limite} ROWS ONLY",
                litteral(&schema)
            ),
            3,
        )?;
        for t in &tables {
            let nom = t[0].clone().unwrap_or_default();
            let type_t = t[1].clone().unwrap_or_default();
            let libelle = t[2].clone().unwrap_or_default();
            // the "Rust computation": name length in characters, and a readable type
            let genre = match type_t.as_str() {
                "T" | "P" => "table",
                "V" => "vue",
                "L" => "logique",
                "A" => "alias",
                _ => "autre",
            };
            println!("{nom:<30} {genre:<8} {libelle}");
            // WITH NC: QTEMP is not journaled, no commitment control
            db.executer(&format!(
                "INSERT INTO QTEMP.RUSTTABLES (NOM, GENRE, TEXTE, LONGUEUR) VALUES ({}, {}, {}, {}) WITH NC",
                litteral(&nom),
                litteral(genre),
                litteral(&libelle.chars().take(100).collect::<String>()),
                nom.chars().count()
            ))?;
        }
        Ok(tables.len())
    })();

    match resultat {
        Ok(n) => {
            println!("rust-db2 : {n} table(s) de {schema} écrite(s) dans QTEMP/RUSTTABLES");
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("rust-db2 : {e}");
            ExitCode::from(1)
        }
    }
}

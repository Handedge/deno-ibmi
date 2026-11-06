//! Asynchronous read (tokio) of a child process stdout, as Deno.Command does:
//! under PASE, the parent does not see data that arrives while it is waiting in poll().
use std::time::{Duration, Instant};
use tokio::io::AsyncReadExt;
use tokio::process::Command;

async fn essai(nom: &str, prog: &str, args: &[&str]) {
    let t = Instant::now();
    let mut fils = Command::new(prog).args(args).stdout(std::process::Stdio::piped()).spawn().unwrap();
    let mut out = fils.stdout.take().unwrap();
    let mut s = String::new();
    let r = tokio::time::timeout(Duration::from_secs(4), out.read_to_string(&mut s)).await;
    let etat = match r { Ok(Ok(_)) => format!("lu {s:?}"), Ok(Err(e)) => format!("erreur {e}"), Err(_) => "BLOQUÉ (4 s)".into() };
    let _ = fils.kill().await;
    println!("{nom:28} {etat} en {:?}", t.elapsed());
}

fn main() {
    for (nom, rt) in [
        ("current_thread", tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap()),
        ("multi_thread", tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap()),
    ] {
        println!("== runtime {nom}");
        rt.block_on(async {
            essai("echo immédiat", "/QOpenSys/usr/bin/echo", &["hello"]).await;
            essai("printf après 0,3 s", "/QOpenSys/usr/bin/sh", &["-c", "sleep 0.3; printf hello"]).await;
            essai("rien, fin après 0,3 s", "/QOpenSys/usr/bin/sh", &["-c", "sleep 0.3"]).await;
        });
    }
}

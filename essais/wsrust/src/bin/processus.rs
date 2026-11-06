// Asynchronous read (tokio) of a child process output under PASE:
// does `system` (CL command) fail to wake poll() on the pipe?
use std::time::Duration;
use tokio::io::AsyncReadExt;
use tokio::process::Command;

async fn essai(titre: &str, prog: &str, args: &[&str]) {
  let mut fils = Command::new(prog)
    .args(args)
    .stdin(std::process::Stdio::null())
    .stdout(std::process::Stdio::piped())
    .stderr(std::process::Stdio::null())
    .spawn()
    .unwrap();
  let mut sortie = fils.stdout.take().unwrap();
  let mut tampon = Vec::new();
  let lecture = tokio::time::timeout(Duration::from_secs(5), sortie.read_to_end(&mut tampon)).await;
  let etat = tokio::time::timeout(Duration::from_secs(5), fils.wait()).await;
  println!(
    "{titre:<28} lecture : {}  fin : {}",
    match lecture { Ok(Ok(n)) => format!("{n} octets"), Ok(Err(e)) => format!("erreur {e}"), Err(_) => "BLOQUEE 5 s".into() },
    match etat { Ok(Ok(s)) => format!("{s}"), _ => "?".into() },
  );
}

fn main() {
  let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
  rt.block_on(async {
    essai("echo", "/QOpenSys/usr/bin/echo", &["bonjour"]).await;
    essai("system DSPSYSVAL", "/QOpenSys/usr/bin/system", &["DSPSYSVAL QMODEL"]).await;
    essai("sh -c system", "/QOpenSys/usr/bin/sh", &["-c", "system 'DSPSYSVAL QMODEL'"]).await;
    essai("sh -c system | cat", "/QOpenSys/usr/bin/sh", &["-c", "system 'DSPSYSVAL QMODEL' | cat"]).await;
  });
}

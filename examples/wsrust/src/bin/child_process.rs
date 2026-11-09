// Asynchronous read (tokio) of a child process output under PASE:
// does `system` (CL command) fail to wake poll() on the pipe?
use std::time::Duration;
use tokio::io::AsyncReadExt;
use tokio::process::Command;

async fn run_case(title: &str, prog: &str, args: &[&str]) {
  let mut child = Command::new(prog)
    .args(args)
    .stdin(std::process::Stdio::null())
    .stdout(std::process::Stdio::piped())
    .stderr(std::process::Stdio::null())
    .spawn()
    .unwrap();
  let mut output = child.stdout.take().unwrap();
  let mut buffer = Vec::new();
  let read_result = tokio::time::timeout(Duration::from_secs(5), output.read_to_end(&mut buffer)).await;
  let status = tokio::time::timeout(Duration::from_secs(5), child.wait()).await;
  println!(
    "{title:<28} read: {}  exit: {}",
    match read_result { Ok(Ok(n)) => format!("{n} bytes"), Ok(Err(e)) => format!("error {e}"), Err(_) => "BLOCKED 5 s".into() },
    match status { Ok(Ok(s)) => format!("{s}"), _ => "?".into() },
  );
}

fn main() {
  let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
  rt.block_on(async {
    run_case("echo", "/QOpenSys/usr/bin/echo", &["hello"]).await;
    run_case("system DSPSYSVAL", "/QOpenSys/usr/bin/system", &["DSPSYSVAL QMODEL"]).await;
    run_case("sh -c system", "/QOpenSys/usr/bin/sh", &["-c", "system 'DSPSYSVAL QMODEL'"]).await;
    run_case("sh -c system | cat", "/QOpenSys/usr/bin/sh", &["-c", "system 'DSPSYSVAL QMODEL' | cat"]).await;
  });
}

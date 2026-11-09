//! Asynchronous read (tokio) of a child process stdout, as Deno.Command does:
//! under PASE, the parent does not see data that arrives while it is waiting in poll().
use std::time::{Duration, Instant};
use tokio::io::AsyncReadExt;
use tokio::process::Command;

async fn run_case(name: &str, prog: &str, args: &[&str]) {
    let t = Instant::now();
    let mut child = Command::new(prog).args(args).stdout(std::process::Stdio::piped()).spawn().unwrap();
    let mut out = child.stdout.take().unwrap();
    let mut s = String::new();
    let r = tokio::time::timeout(Duration::from_secs(4), out.read_to_string(&mut s)).await;
    let outcome = match r { Ok(Ok(_)) => format!("read {s:?}"), Ok(Err(e)) => format!("error {e}"), Err(_) => "BLOCKED (4 s)".into() };
    let _ = child.kill().await;
    println!("{name:28} {outcome} in {:?}", t.elapsed());
}

fn main() {
    for (name, rt) in [
        ("current_thread", tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap()),
        ("multi_thread", tokio::runtime::Builder::new_multi_thread().enable_all().build().unwrap()),
    ] {
        println!("== runtime {name}");
        rt.block_on(async {
            run_case("immediate echo", "/QOpenSys/usr/bin/echo", &["hello"]).await;
            run_case("printf after 0.3 s", "/QOpenSys/usr/bin/sh", &["-c", "sleep 0.3; printf hello"]).await;
            run_case("nothing, exit after 0.3 s", "/QOpenSys/usr/bin/sh", &["-c", "sleep 0.3"]).await;
        });
    }
}

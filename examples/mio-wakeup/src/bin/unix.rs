//! Unix socket: pending read cancelled, then close (netUnixCloseCancelsPendingReadAndSendsEof).
//! Under PASE, Deno stays stuck in a system call; a watchdog thread reports it.
use std::time::{Duration, Instant};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

macro_rules! step {
    ($name:expr, $e:expr) => {{
        let t = Instant::now();
        eprintln!("-> {}", $name);
        let r = $e;
        println!("{:40} done in {:?}", $name, t.elapsed());
        r
    }};
}

async fn run_case(unix: bool) {
    println!("== {}", if unix { "Unix" } else { "TCP" });
    let path = "/tmp/rustpoc/unix-rs.sock";
    let _ = std::fs::remove_file(path);
    let (server, mut client_r, client_w): (tokio::task::JoinHandle<String>, Box<dyn tokio::io::AsyncRead + Unpin + Send>, Box<dyn tokio::io::AsyncWrite + Unpin + Send>);
    if unix {
        let l = tokio::net::UnixListener::bind(path).unwrap();
        server = tokio::spawn(async move { let (mut s, _) = l.accept().await.unwrap(); let mut b = [0u8; 64]; format!("server reads {:?}", s.read(&mut b).await) });
        let c = tokio::net::UnixStream::connect(path).await.unwrap();
        let (r, w) = c.into_split();
        client_r = Box::new(r); client_w = Box::new(w);
    } else {
        let l = tokio::net::TcpListener::bind("127.0.0.1:4998").await.unwrap();
        server = tokio::spawn(async move { let (mut s, _) = l.accept().await.unwrap(); let mut b = [0u8; 64]; format!("server reads {:?}", s.read(&mut b).await) });
        let c = tokio::net::TcpStream::connect("127.0.0.1:4998").await.unwrap();
        let (r, w) = c.into_split();
        client_r = Box::new(r); client_w = Box::new(w);
    }
    // pending read on the client side, cancelled after 100 ms (like the Deno CancelHandle)
    let mut b = [0u8; 64];
    let _ = step!("client read cancelled", tokio::time::timeout(Duration::from_millis(100), client_r.read(&mut b)).await);
    let mut client_w = client_w;
    let _ = client_w.flush().await;
    step!("drop read half", drop(client_r));
    step!("drop write half (close)", drop(client_w));
    let r = step!("server sees the end?", tokio::time::timeout(Duration::from_secs(3), server).await);
    println!("   result: {:?}", r.map(|x| x.unwrap()));
}

fn main() {
    std::thread::spawn(|| {
        std::thread::sleep(Duration::from_secs(20));
        println!("WATCHDOG: main thread blocked for 20 s");
        std::process::exit(3);
    });
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
    rt.block_on(async { run_case(false).await; run_case(true).await; });
    println!("normal END");
}

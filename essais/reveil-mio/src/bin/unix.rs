//! Unix socket: pending read cancelled, then close (netUnixCloseCancelsPendingReadAndSendsEof).
//! Under PASE, Deno stays stuck in a system call; a watchdog thread reports it.
use std::time::{Duration, Instant};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

macro_rules! etape {
    ($nom:expr, $e:expr) => {{
        let t = Instant::now();
        eprintln!("-> {}", $nom);
        let r = $e;
        println!("{:40} fini en {:?}", $nom, t.elapsed());
        r
    }};
}

async fn essai(unix: bool) {
    println!("== {}", if unix { "Unix" } else { "TCP" });
    let chemin = "/tmp/rustpoc/essai-rs.sock";
    let _ = std::fs::remove_file(chemin);
    let (serveur, mut client_r, client_w): (tokio::task::JoinHandle<String>, Box<dyn tokio::io::AsyncRead + Unpin + Send>, Box<dyn tokio::io::AsyncWrite + Unpin + Send>);
    if unix {
        let l = tokio::net::UnixListener::bind(chemin).unwrap();
        serveur = tokio::spawn(async move { let (mut s, _) = l.accept().await.unwrap(); let mut b = [0u8; 64]; format!("serveur lit {:?}", s.read(&mut b).await) });
        let c = tokio::net::UnixStream::connect(chemin).await.unwrap();
        let (r, w) = c.into_split();
        client_r = Box::new(r); client_w = Box::new(w);
    } else {
        let l = tokio::net::TcpListener::bind("127.0.0.1:4998").await.unwrap();
        serveur = tokio::spawn(async move { let (mut s, _) = l.accept().await.unwrap(); let mut b = [0u8; 64]; format!("serveur lit {:?}", s.read(&mut b).await) });
        let c = tokio::net::TcpStream::connect("127.0.0.1:4998").await.unwrap();
        let (r, w) = c.into_split();
        client_r = Box::new(r); client_w = Box::new(w);
    }
    // pending read on the client side, cancelled after 100 ms (like the Deno CancelHandle)
    let mut b = [0u8; 64];
    let _ = etape!("lecture client annulée", tokio::time::timeout(Duration::from_millis(100), client_r.read(&mut b)).await);
    let mut client_w = client_w;
    let _ = client_w.flush().await;
    etape!("drop moitié lecture", drop(client_r));
    etape!("drop moitié écriture (close)", drop(client_w));
    let r = etape!("serveur voit la fin ?", tokio::time::timeout(Duration::from_secs(3), serveur).await);
    println!("   résultat : {:?}", r.map(|x| x.unwrap()));
}

fn main() {
    std::thread::spawn(|| {
        std::thread::sleep(Duration::from_secs(20));
        println!("GARDE : fil principal bloqué depuis 20 s");
        std::process::exit(3);
    });
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
    rt.block_on(async { essai(false).await; essai(true).await; });
    println!("FIN normale");
}

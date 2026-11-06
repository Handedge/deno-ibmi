// Is the socket accepted by tokio really non-blocking under PASE?
// A timer ticks every 200 ms while we wait for data from a silent
// client: if the thread is blocked in read(), the timer stops.
use std::os::fd::AsRawFd;
use std::time::{Duration, Instant};
use tokio::io::AsyncReadExt;

unsafe extern "C" {
  fn fcntl(fd: i32, cmd: i32, ...) -> i32;
}
const F_GETFL: i32 = 3;
const O_NONBLOCK: i32 = 0o200000 >> 0; // replaced below by the AIX value

fn main() {
  let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
  rt.block_on(async {
    let ecoute = tokio::net::TcpListener::bind("127.0.0.1:3087").await.unwrap();
    println!("ecoute 3087");
    let (mut s, _) = ecoute.accept().await.unwrap();
    let fd = s.as_raw_fd();
    let fl = unsafe { fcntl(fd, F_GETFL) };
    // AIX: O_NONBLOCK = 0x4, O_NDELAY = 0x8000
    println!("fd {fd} F_GETFL = {fl:#x}  O_NONBLOCK(0x4)={}  O_NDELAY(0x8000)={}", fl & 0x4 != 0, fl & 0x8000 != 0);
    let _ = O_NONBLOCK;
    let t0 = Instant::now();
    tokio::spawn(async move {
      for _ in 0..10 {
        tokio::time::sleep(Duration::from_millis(200)).await;
        println!("  tic {:>5} ms", t0.elapsed().as_millis());
      }
    });
    let mut buf = [0u8; 64];
    let n = s.read(&mut buf).await.unwrap();
    println!("read = {n} octets a {} ms", t0.elapsed().as_millis());
  });
}

//! Reproduction of the "Test flush deadlock" of deno test, without Deno.
//!
//! As in cli/tools/test/channel.rs: one thread runs a tokio current_thread runtime that
//! waits both on a channel (woken from another thread) and on a pipe read;
//! another thread sends messages and waits for the acknowledgement. On a healthy
//! system, no wakeup is ever lost. On AIX, mio uses a poll(2) selector and a
//! wakeup pipe: we count the messages left unanswered for more than 2 s.
use std::io::Write;
use std::os::fd::FromRawFd;
use std::sync::mpsc;
use std::time::{Duration, Instant};
use tokio::io::AsyncReadExt;

fn main() {
    let n: usize = std::env::args().nth(1).and_then(|a| a.parse().ok()).unwrap_or(2000);
    let avec_tube = std::env::args().nth(2).as_deref() != Some("sans-tube");
    let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel::<mpsc::Sender<()>>();
    let mut fds = [0; 2];
    assert_eq!(unsafe { libc::pipe(fds.as_mut_ptr()) }, 0);
    let mut ecriture = unsafe { std::fs::File::from_raw_fd(fds[1]) };
    let lecture = fds[0];
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_current_thread().enable_io().build().unwrap();
        rt.block_on(async move {
            unsafe { libc::fcntl(lecture, libc::F_SETFL, libc::O_NONBLOCK) };
            let f = unsafe { std::fs::File::from_raw_fd(lecture) };
            let mut tube = tokio::net::unix::pipe::Receiver::from_file(f).unwrap();
            let mut buf = [0u8; 64];
            loop {
                tokio::select! {
                    biased;
                    m = rx.recv() => match m { Some(ack) => { let _ = ack.send(()); } None => break },
                    r = tube.read(&mut buf), if avec_tube => { if matches!(r, Ok(0) | Err(_)) { break } }
                }
            }
        });
    });
    let (mut perdus, mut pire) = (0, Duration::ZERO);
    let t0 = Instant::now();
    for i in 0..n {
        if avec_tube && i % 7 == 0 {
            let _ = ecriture.write_all(b"x"); // some traffic on the pipe, like the stdout of a test
        }
        let (ack_tx, ack_rx) = mpsc::channel();
        let t = Instant::now();
        tx.send(ack_tx).unwrap();
        match ack_rx.recv_timeout(Duration::from_secs(2)) {
            Ok(()) => pire = pire.max(t.elapsed()),
            Err(_) => {
                perdus += 1;
                // does one byte on the pipe wake the thread? (lost wakeup, not a deadlock)
                if avec_tube { let _ = ecriture.write_all(b"y"); }
                if ack_rx.recv_timeout(Duration::from_secs(10)).is_err() {
                    println!("message {i} : fil définitivement endormi");
                    break;
                }
            }
        }
    }
    println!("{n} messages, {perdus} réveils perdus (> 2 s), pire délai normal {pire:?}, total {:?}", t0.elapsed());
}

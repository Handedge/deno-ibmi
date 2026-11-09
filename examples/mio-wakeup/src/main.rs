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
    let with_pipe = std::env::args().nth(2).as_deref() != Some("no-pipe");
    let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel::<mpsc::Sender<()>>();
    let mut fds = [0; 2];
    assert_eq!(unsafe { libc::pipe(fds.as_mut_ptr()) }, 0);
    let mut pipe_writer = unsafe { std::fs::File::from_raw_fd(fds[1]) };
    let pipe_reader = fds[0];
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_current_thread().enable_io().build().unwrap();
        rt.block_on(async move {
            unsafe { libc::fcntl(pipe_reader, libc::F_SETFL, libc::O_NONBLOCK) };
            let f = unsafe { std::fs::File::from_raw_fd(pipe_reader) };
            let mut pipe = tokio::net::unix::pipe::Receiver::from_file(f).unwrap();
            let mut buf = [0u8; 64];
            loop {
                tokio::select! {
                    biased;
                    m = rx.recv() => match m { Some(ack) => { let _ = ack.send(()); } None => break },
                    r = pipe.read(&mut buf), if with_pipe => { if matches!(r, Ok(0) | Err(_)) { break } }
                }
            }
        });
    });
    let (mut lost, mut worst) = (0, Duration::ZERO);
    let t0 = Instant::now();
    for i in 0..n {
        if with_pipe && i % 7 == 0 {
            let _ = pipe_writer.write_all(b"x"); // some traffic on the pipe, like the stdout of a test
        }
        let (ack_tx, ack_rx) = mpsc::channel();
        let t = Instant::now();
        tx.send(ack_tx).unwrap();
        match ack_rx.recv_timeout(Duration::from_secs(2)) {
            Ok(()) => worst = worst.max(t.elapsed()),
            Err(_) => {
                lost += 1;
                // does one byte on the pipe wake the thread? (lost wakeup, not a deadlock)
                if with_pipe { let _ = pipe_writer.write_all(b"y"); }
                if ack_rx.recv_timeout(Duration::from_secs(10)).is_err() {
                    println!("message {i}: thread asleep for good");
                    break;
                }
            }
        }
    }
    println!("{n} messages, {lost} lost wakeups (> 2 s), worst normal delay {worst:?}, total {:?}", t0.elapsed());
}

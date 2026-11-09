//! Variants of stage 3 (signal-hook iterator), one per process: variantes <a|b|c|d>
//! a: Signals::new([SIGTERM]) + forever() in a thread (without add_signal)
//! b: Signals::new([SIGTERM]) + pending() in a loop (non-blocking read)
//! c: without signal-hook: thread blocked in read() on a std socket pair, raw handler that send()s
//! d: like c, but reading with poll() then read()
use std::io::Read;
use std::os::unix::io::AsRawFd;
use std::os::unix::net::UnixStream;
use std::sync::atomic::{AtomicI32, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

static FD: AtomicI32 = AtomicI32::new(-1);

fn raise_signal(sig: i32) {
    unsafe { libc::kill(libc::getpid(), sig) };
}

fn main() {
    let term = signal_hook::consts::SIGTERM;
    let mode = std::env::args().nth(1).unwrap_or_default();
    let seen = Arc::new(AtomicUsize::new(0));
    let seen2 = seen.clone();
    match mode.as_str() {
        "a" => {
            let mut s = signal_hook::iterator::Signals::new([term]).unwrap();
            std::thread::spawn(move || {
                for x in s.forever() {
                    println!("   received {x}");
                    seen2.fetch_add(1, Ordering::SeqCst);
                }
            });
        }
        "b" => {
            let mut s = signal_hook::iterator::Signals::new([term]).unwrap();
            std::thread::spawn(move || loop {
                for x in s.pending() {
                    println!("   received {x}");
                    seen2.fetch_add(1, Ordering::SeqCst);
                }
                std::thread::sleep(Duration::from_millis(50));
            });
        }
        "c" | "d" => {
            let (mut reader, writer) = UnixStream::pair().unwrap();
            FD.store(writer.as_raw_fd(), Ordering::SeqCst);
            std::mem::forget(writer);
            unsafe {
                signal_hook_registry::register(term, || {
                    let r = libc::send(FD.load(Ordering::SeqCst), b"X".as_ptr() as *const _, 1, libc::MSG_NONBLOCK);
                    if r != 1 {
                        libc::write(2, b"send KO\n".as_ptr() as *const _, 8);
                    }
                })
            }
            .unwrap();
            let poll = mode == "d";
            std::thread::spawn(move || loop {
                if poll {
                    let mut p = libc::pollfd { fd: reader.as_raw_fd(), events: libc::POLLIN, revents: 0 };
                    let r = unsafe { libc::poll(&mut p, 1, -1) };
                    println!("   poll -> {r} revents={:#x}", p.revents);
                }
                let mut b = [0u8; 1];
                match reader.read(&mut b) {
                    Ok(k) => {
                        println!("   read -> {k}");
                        seen2.fetch_add(1, Ordering::SeqCst);
                    }
                    Err(e) => println!("   read -> error {e}"),
                }
            });
        }
        "e" => {
            // iterator + raw handler on the same signal: is the registry called?
            let mut s = signal_hook::iterator::Signals::new([term]).unwrap();
            unsafe {
                signal_hook_registry::register(term, || {
                    libc::write(2, b"   raw called 
".as_ptr() as *const _, 15);
                })
            }
            .unwrap();
            let mut act: libc::sigaction = unsafe { std::mem::zeroed() };
            unsafe { libc::sigaction(term, std::ptr::null(), &mut act) };
            println!("   sigaction : handler={:#x} flags={:#x}", act.sa_sigaction, act.sa_flags);
            std::thread::spawn(move || loop {
                for x in s.pending() {
                    println!("   received {x}");
                    seen2.fetch_add(1, Ordering::SeqCst);
                }
                std::thread::sleep(Duration::from_millis(50));
            });
        }
        _ => {
            eprintln!("mode a|b|c|d|e");
            return;
        }
    }
    std::thread::sleep(Duration::from_millis(300));
    raise_signal(term);
    std::thread::sleep(Duration::from_secs(2));
    println!("{mode}: {} received", seen.load(Ordering::SeqCst));
    std::process::exit(0);
}

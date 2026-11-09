//! Reproduction: Deno.addSignalListener receives nothing under PASE (signal_test hangs).
//! Three stages, from lowest to highest level, as in Deno ext/signals:
//! 1. raw handler (signal_hook_registry::register);
//! 2. handler + byte written to a socket pair (low_level::pipe);
//! 3. Signals::forever iterator in a thread (exactly what Deno does).
use std::io::Read;
use std::os::unix::net::UnixStream;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

fn raise_signal(sig: i32) {
    unsafe { libc::kill(libc::getpid(), sig) };
}

fn main() {
    let usr1 = signal_hook::consts::SIGUSR1;
    let usr2 = signal_hook::consts::SIGUSR2;
    let term = signal_hook::consts::SIGTERM;
    println!("SIGUSR1={usr1} SIGUSR2={usr2} SIGTERM={term}");

    // 1. raw handler
    let n = Arc::new(AtomicUsize::new(0));
    let n2 = n.clone();
    unsafe { signal_hook_registry::register(usr1, move || { n2.fetch_add(1, Ordering::SeqCst); }) }.unwrap();
    raise_signal(usr1);
    std::thread::sleep(Duration::from_millis(300));
    println!("1. raw handler: {} call(s)", n.load(Ordering::SeqCst));

    // 2. socket pair
    let (mut reader, writer) = UnixStream::pair().unwrap();
    signal_hook::low_level::pipe::register(usr2, writer).unwrap();
    reader.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
    raise_signal(usr2);
    let mut b = [0u8; 8];
    match reader.read(&mut b) {
        Ok(k) => println!("2. socket pair: {k} byte(s) received"),
        Err(e) => println!("2. socket pair: NOTHING ({e})"),
    }

    // 3. iterator in a thread, like Deno (SIGHUP, SIGTERM, SIGINT, then add_signal)
    let mut signals = signal_hook::iterator::Signals::new([signal_hook::consts::SIGHUP]).unwrap();
    let handle = signals.handle();
    let seen = Arc::new(AtomicUsize::new(0));
    let seen2 = seen.clone();
    std::thread::spawn(move || {
        for s in signals.forever() {
            println!("   thread: signal {s} received");
            seen2.fetch_add(1, Ordering::SeqCst);
        }
    });
    std::thread::sleep(Duration::from_millis(200));
    handle.add_signal(term).unwrap();
    raise_signal(term);
    std::thread::sleep(Duration::from_secs(2));
    println!("3. Signals iterator (SIGTERM): {} signal(s)", seen.load(Ordering::SeqCst));
    std::process::exit(0);
}

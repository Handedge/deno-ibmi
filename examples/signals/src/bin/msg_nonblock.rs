//! recv(MSG_NONBLOCK) on an empty socket pair: does it return immediately under PASE?
use std::os::unix::io::AsRawFd;
use std::os::unix::net::UnixStream;
use std::time::{Duration, Instant};

fn main() {
    let (reader, _writer) = UnixStream::pair().unwrap();
    let fd = reader.as_raw_fd();
    println!("MSG_NONBLOCK={:#x}", libc::MSG_NONBLOCK);
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_secs(3));
        println!("recv(MSG_NONBLOCK) BLOCKED for 3 s: flag ignored");
        std::process::exit(1);
    });
    let mut b = [0u8; 16];
    let t = Instant::now();
    let r = unsafe { libc::recv(fd, b.as_mut_ptr() as *mut _, 16, libc::MSG_NONBLOCK) };
    let e = std::io::Error::last_os_error();
    println!("recv -> {r} ({e}) in {:?}", t.elapsed());
}

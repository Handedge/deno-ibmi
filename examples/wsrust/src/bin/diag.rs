// Diagnostics of the I/O building blocks under PASE (mio, tokio, threads)
fn t<T: std::fmt::Debug, E: std::fmt::Debug>(name: &str, r: Result<T, E>) {
    match r { Ok(_) => println!("OK     {name}"), Err(e) => println!("FAILED {name}: {e:?}") }
}
fn main() {
    t("mio::Poll::new", mio::Poll::new());
    let p = mio::Poll::new();
    if let Ok(p) = &p { t("mio::Waker::new", mio::Waker::new(p.registry(), mio::Token(0))); }
    t("mio::unix::pipe::new", mio::unix::pipe::new());
    t("std UnixStream::pair", std::os::unix::net::UnixStream::pair());
    t("mio UnixStream::pair", mio::net::UnixStream::pair());
    t("thread pile 2 Mo", std::thread::Builder::new().stack_size(2 * 1024 * 1024).spawn(|| 1).map(|h| h.join()));
    t("tokio current_thread all", tokio::runtime::Builder::new_current_thread().enable_all().build());
    t("tokio multi_thread all", tokio::runtime::Builder::new_multi_thread().enable_all().build());
    let (a, _b) = std::os::unix::net::UnixStream::pair().unwrap();
    t("UnixStream::try_clone (F_DUPFD_CLOEXEC)", a.try_clone());
}

// Reproduces the Deno.serve pattern under PASE: tokio current_thread runtime,
// hyper task waiting for a response supplied later by the root future
// (like the Deno JS event loop), after a timer.
//   /dort   : the handler itself waits 50 ms
//   /racine : the response is completed by the root future after 50 ms
use axum::{Router, extract::State, routing::get};
use std::time::Duration;
use tokio::sync::{mpsc, oneshot};

type Reply = oneshot::Sender<String>;

async fn sleeps() -> &'static str {
    tokio::time::sleep(Duration::from_millis(50)).await;
    "sleep ok\n"
}

async fn root(State(tx): State<mpsc::UnboundedSender<Reply>>) -> String {
    let (reply_tx, reply_rx) = oneshot::channel();
    tx.send(reply_tx).unwrap();
    reply_rx.await.unwrap_or_else(|_| "lost\n".into())
}

fn main() {
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
    let local = tokio::task::LocalSet::new();
    local.block_on(&rt, async {
        let (tx, mut rx) = mpsc::unbounded_channel::<Reply>();
        let app = Router::new()
            .route("/dort", get(sleeps))
            .route("/racine", get(root))
            .with_state(tx);
        let port = std::env::var("PORT").unwrap_or_else(|_| "3085".into());
        let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}")).await.unwrap();
        println!("deferred listening on {port}");
        tokio::task::spawn_local(async move { axum::serve(listener, app).await.unwrap() });
        // root future: completes the requests after a timer, like the JS event loop
        while let Some(reply_tx) = rx.recv().await {
            tokio::time::sleep(Duration::from_millis(50)).await;
            let _ = reply_tx.send("root ok\n".into());
        }
    });
}

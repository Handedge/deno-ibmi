// Reproduces the Deno.serve pattern under PASE: tokio current_thread runtime,
// hyper task waiting for a response supplied later by the root future
// (like the Deno JS event loop), after a timer.
//   /dort   : the handler itself waits 50 ms
//   /racine : the response is completed by the root future after 50 ms
use axum::{Router, extract::State, routing::get};
use std::time::Duration;
use tokio::sync::{mpsc, oneshot};

type Demande = oneshot::Sender<String>;

async fn dort() -> &'static str {
    tokio::time::sleep(Duration::from_millis(50)).await;
    "dort ok\n"
}

async fn racine(State(tx): State<mpsc::UnboundedSender<Demande>>) -> String {
    let (envoi, reception) = oneshot::channel();
    tx.send(envoi).unwrap();
    reception.await.unwrap_or_else(|_| "perdu\n".into())
}

fn main() {
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
    let local = tokio::task::LocalSet::new();
    local.block_on(&rt, async {
        let (tx, mut rx) = mpsc::unbounded_channel::<Demande>();
        let app = Router::new()
            .route("/dort", get(dort))
            .route("/racine", get(racine))
            .with_state(tx);
        let port = std::env::var("PORT").unwrap_or_else(|_| "3085".into());
        let ecoute = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}")).await.unwrap();
        println!("attente ecoute sur {port}");
        tokio::task::spawn_local(async move { axum::serve(ecoute, app).await.unwrap() });
        // root future: completes the requests after a timer, like the JS event loop
        while let Some(envoi) = rx.recv().await {
            tokio::time::sleep(Duration::from_millis(50)).await;
            let _ = envoi.send("racine ok\n".into());
        }
    });
}

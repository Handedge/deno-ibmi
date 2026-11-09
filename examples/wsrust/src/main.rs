// First Rust web service served by IBM i (IBMI, 2026-10-28): GET /bonjour
use axum::{routing::get, Json, Router};
use serde_json::{json, Value};

async fn hello() -> Json<Value> {
    Json(json!({
        "message": "Hello from Rust on IBM i",
        "systeme": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "pid": std::process::id()
    }))
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/bonjour", get(hello));
    let port = std::env::var("PORT").unwrap_or_else(|_| "3080".into());
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}")).await.unwrap();
    println!("wsrust listening on {port}");
    axum::serve(listener, app).await.unwrap();
}

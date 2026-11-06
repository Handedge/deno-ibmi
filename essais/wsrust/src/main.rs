// First Rust web service served by IBM i (IBMI, 2026-10-28): GET /bonjour
use axum::{routing::get, Json, Router};
use serde_json::{json, Value};

async fn bonjour() -> Json<Value> {
    Json(json!({
        "message": "Bonjour depuis Rust sur IBM i",
        "systeme": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "pid": std::process::id()
    }))
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/bonjour", get(bonjour));
    let port = std::env::var("PORT").unwrap_or_else(|_| "3080".into());
    let ecoute = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}")).await.unwrap();
    println!("wsrust ecoute sur {port}");
    axum::serve(ecoute, app).await.unwrap();
}

import hashlib
import os
from pathlib import Path

from flask import Flask, jsonify, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

SECRET_FILE = Path("/vault/secrets/app-secret")

REQUEST_COUNT = Counter(
    "vault_platform_requests_total",
    "Total application requests"
)


@app.before_request
def count_request():
    REQUEST_COUNT.inc()


@app.get("/")
def home():
    return jsonify({
        "application": "kubernetes-vault-secrets-platform",
        "status": "running",
        "environment": os.getenv("APP_ENV", "unknown")
    })


@app.get("/health")
def health():
    return jsonify({"status": "healthy"})


@app.get("/api/v1/secret-status")
def secret_status():
    if not SECRET_FILE.exists():
        return jsonify({
            "secret_loaded": False,
            "message": "Secret not available"
        }), 503

    secret = SECRET_FILE.read_text().strip()

    fingerprint = hashlib.sha256(
        secret.encode()
    ).hexdigest()[:12]

    return jsonify({
        "secret_loaded": bool(secret),
        "secret_source": "hashicorp-vault",
        "fingerprint": fingerprint
    })


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

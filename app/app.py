import os
import random
import time
import threading

from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# --- In-memory, adjustable "chaos" knobs -----------------------------------
# error_rate and latency bounds can be changed at runtime via /chaos/*
# endpoints, so failure injection doesn't require redeploying the app.
state_lock = threading.Lock()
state = {
    "error_rate": float(os.environ.get("ERROR_RATE", "0.0005")),   # 0.05% baseline, under the 0.1% SLO budget
    "latency_min": float(os.environ.get("LATENCY_MIN", "0.05")),
    "latency_max": float(os.environ.get("LATENCY_MAX", "0.35")),
}

# --- Prometheus metrics ------------------------------------------------------
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0],
)


@app.route("/api")
def api():
    with state_lock:
        error_rate = state["error_rate"]
        lo, hi = state["latency_min"], state["latency_max"]

    start = time.time()
    time.sleep(random.uniform(lo, hi))
    duration = time.time() - start
    LATENCY.observe(duration)

    if random.random() < error_rate:
        REQUESTS.labels(status="500").inc()
        return jsonify({"status": "error"}), 500

    REQUESTS.labels(status="200").inc()
    return jsonify({"status": "ok", "duration_s": round(duration, 3)}), 200


@app.route("/healthz")
def healthz():
    return jsonify({"status": "healthy"}), 200


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# --- Chaos endpoints ---------------------------------------------------------
# Used to demonstrate burn-rate alerting: bump error_rate way up, watch the
# SLO burn-rate alert fire, then put it back and watch it resolve.
@app.route("/chaos/error_rate/<float:rate>", methods=["POST"])
def set_error_rate(rate):
    with state_lock:
        state["error_rate"] = rate
    return jsonify({"error_rate": rate}), 200


@app.route("/chaos/status")
def chaos_status():
    with state_lock:
        return jsonify(state), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

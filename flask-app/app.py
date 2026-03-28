import json
import os
import socket
import time

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import redis

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "admin")
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "tasks")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

db = SQLAlchemy(app)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

CACHE_KEY = "tasks_cache"
CACHE_TTL = 30  # seconds

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "done": self.done,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
VISIT_COUNT = Counter("visit_count_total", "Total visits to the home page")

# ---------------------------------------------------------------------------
# Middleware – record metrics for every request
# ---------------------------------------------------------------------------
@app.before_request
def _start_timer():
    request._start_time = time.time()


@app.after_request
def _record_metrics(response):
    if request.path == "/metrics":
        return response
    duration = time.time() - getattr(request, "_start_time", time.time())
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status=response.status_code,
    ).inc()
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.path,
    ).observe(duration)
    return response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def invalidate_cache():
    """Remove the tasks cache so the next GET /tasks fetches fresh data."""
    redis_client.delete(CACHE_KEY)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    VISIT_COUNT.inc()
    visit_number = redis_client.incr("visit_counter")
    return jsonify({
        "app": "Flask TODO API",
        "version": "1.0.0",
        "hostname": socket.gethostname(),
        "visits": visit_number,
    })


@app.route("/tasks", methods=["GET"])
def get_tasks():
    cached = redis_client.get(CACHE_KEY)
    if cached:
        return jsonify(json.loads(cached)), 200

    tasks = Task.query.order_by(Task.id).all()
    data = [t.to_dict() for t in tasks]
    redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(data, default=str))
    return jsonify(data), 200


@app.route("/tasks", methods=["POST"])
def create_task():
    body = request.get_json(force=True)
    if not body or not body.get("title"):
        return jsonify({"error": "title is required"}), 400

    task = Task(
        title=body["title"],
        description=body.get("description", ""),
    )
    db.session.add(task)
    db.session.commit()
    invalidate_cache()
    return jsonify(task.to_dict()), 201


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "task not found"}), 404

    body = request.get_json(force=True)
    if "title" in body:
        task.title = body["title"]
    if "description" in body:
        task.description = body["description"]
    if "done" in body:
        task.done = bool(body["done"])

    db.session.commit()
    invalidate_cache()
    return jsonify(task.to_dict()), 200


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    invalidate_cache()
    return jsonify({"message": f"task {task_id} deleted"}), 200


@app.route("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        redis_client.ping()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

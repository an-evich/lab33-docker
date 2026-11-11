import os, socket, time
from flask import Flask, jsonify
import redis
import psycopg2

app = Flask(__name__)

PORT = int(os.getenv("PORT", "5000"))
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PG = dict(
    host=os.getenv("POSTGRES_HOST", "postgres"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    dbname=os.getenv("POSTGRES_DB", "lab33"),
    user=os.getenv("POSTGRES_USER", "lab33"),
    password=os.getenv("POSTGRES_PASSWORD", "lab33pass"),
)
VERSION = os.getenv("APP_VERSION", "dev")
REPLICA = socket.gethostname()

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def run(sql, params=None, fetch=False):
    conn = psycopg2.connect(connect_timeout=3, **PG)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()


def init_db():
    for _ in range(30):
        try:
            run("CREATE TABLE IF NOT EXISTS visits_log ("
                "id SERIAL PRIMARY KEY, path TEXT, replica TEXT, "
                "visited_at TIMESTAMPTZ DEFAULT now())")
            return
        except Exception as e:
            print("waiting for postgres:", e, flush=True)
            time.sleep(2)


def log_visit(path):
    run("INSERT INTO visits_log (path, replica) VALUES (%s, %s)", (path, REPLICA))


@app.route("/")
def index():
    log_visit("/")
    return f"<h1>Hello, Docker!</h1><p>version {VERSION}, replica {REPLICA}</p>"


@app.route("/health")
def health():
    status = {"status": "ok", "version": VERSION, "replica": REPLICA}
    try:
        status["redis"] = "connected" if r.ping() else "error"
    except Exception as e:
        status["redis"] = f"error: {e}"
        status["status"] = "degraded"
    try:
        run("SELECT 1")
        status["postgres"] = "connected"
    except Exception as e:
        status["postgres"] = f"error: {e}"
        status["status"] = "degraded"
    return jsonify(status)


@app.route("/count")
def count():
    n = r.incr("hits")
    log_visit("/count")
    return f"<h1>Visits: {n}</h1><p>replica {REPLICA}</p>"


@app.route("/history")
def history():
    rows = run("SELECT id, path, replica, visited_at FROM visits_log "
               "ORDER BY id DESC LIMIT 20", fetch=True)
    body = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>"
                   for a, b, c, d in rows)
    return ("<h1>Last 20 visits</h1><table border=1>"
            "<tr><th>id</th><th>path</th><th>replica</th><th>time</th></tr>"
            f"{body}</table>")


init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

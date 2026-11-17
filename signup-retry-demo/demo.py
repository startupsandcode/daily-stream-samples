"""Local-only workshop signup retry demonstration. Python 3.9+, stdlib only."""
import argparse
import json
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / ".demo" / "signup.sqlite3"
SIGNUPS = {"signup-42": "Maya Chen (fake)", "signup-43": "Alex Rivera (fake)"}
MODES = {"naive", "protected"}


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS welcome_tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL CHECK (mode IN ('naive', 'protected')),
                    signup_id TEXT NOT NULL,
                    task TEXT NOT NULL,
                    action_key TEXT UNIQUE
                )
            """)

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def create(self, mode, signup_id):
        if mode not in MODES or signup_id not in SIGNUPS:
            raise ValueError("Use one of the two fake signup IDs and a demo mode.")
        task = "Welcome " + SIGNUPS[signup_id]
        key = f"welcome-task:{signup_id}" if mode == "protected" else None
        with closing(self.connect()) as db, db:
            result = db.execute("""
                INSERT INTO welcome_tasks (mode, signup_id, task, action_key)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(action_key) DO NOTHING
            """, (mode, signup_id, task, key))
            created = result.rowcount == 1
            if created:
                row = db.execute("SELECT * FROM welcome_tasks WHERE task_id = ?",
                                 (result.lastrowid,)).fetchone()
            else:
                row = db.execute("SELECT * FROM welcome_tasks WHERE action_key = ?",
                                 (key,)).fetchone()
        # The transaction is committed before the HTTP handler can simulate failure.
        return dict(row), created

    def rows(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM welcome_tasks ORDER BY task_id")]

    def reset(self):
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM welcome_tasks")
            db.execute("DELETE FROM sqlite_sequence WHERE name = 'welcome_tasks'")


def make_server(path=DEFAULT_DB, port=8000):
    store = Store(path)
    ui = (ROOT / "index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, data, mime="application/json; charset=utf-8"):
            body = json.dumps(data).encode() if isinstance(data, dict) else data
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.reply(200, ui, "text/html; charset=utf-8")
            elif self.path == "/api/tasks":
                self.reply(200, {"table": "welcome_tasks", "rows": store.rows()})
            else:
                self.reply(404, {"error": "Not found"})

        def do_POST(self):
            if self.path not in {"/api/signup", "/api/reset"}:
                self.reply(404, {"error": "Not found"})
                return
            if self.headers.get_content_type() != "application/json":
                self.reply(415, {"error": "Expected JSON"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError()
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError()
                if self.path == "/api/reset":
                    if data != {"confirm": True}:
                        raise ValueError()
                    store.reset()
                    self.reply(200, {"reset": True})
                    return
                mode = data.get("mode")
                signup_id = data.get("signup_id")
                fail = data.get("timeout", False)
                if (not isinstance(mode, str) or not isinstance(signup_id, str)
                        or type(fail) is not bool):
                    raise ValueError()
                row, created = store.create(mode, signup_id)
            except (ValueError, UnicodeError):
                self.reply(400, {"error": "Invalid demo input."})
                return
            if fail:
                # Deliberate fault injection: real HTTP 504 instead of a success response.
                # Only the separate read of the table reveals whether the write committed.
                self.reply(504, {"error": "Simulated gateway timeout. Write outcome unknown to caller."})
            else:
                self.reply(201 if created else 200, {"task": row, "created": created})

    return HTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with make_server(port=args.port) as server:
        print(f"Open http://127.0.0.1:{server.server_port} | Ctrl+C to stop", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

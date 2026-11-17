"""HTTP integration tests against an isolated, real SQLite file."""
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from demo import make_server


class RetryDemoTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "signup.sqlite3"
        self.server = make_server(path=self.path, port=0)
        self.addCleanup(self.server.server_close)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        worker = threading.Thread(target=self.server.serve_forever,
                                  kwargs={"poll_interval": 0.01}, daemon=True)
        worker.start()
        self.addCleanup(worker.join)
        self.addCleanup(self.server.shutdown)

    def request(self, route, data=None):
        request = Request(self.url + route, json.dumps(data).encode() if data is not None else None,
                          {"Content-Type": "application/json"} if data is not None else {})
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            return response.code, json.loads(raw) if response.headers.get_content_type() == "application/json" else raw

    def signup(self, mode, signup_id="signup-42", timeout=False):
        return self.request("/api/signup", {"mode": mode, "signup_id": signup_id, "timeout": timeout})

    def table(self):
        code, data = self.request("/api/tasks")
        self.assertEqual(code, 200)
        self.assertEqual(data["table"], "welcome_tasks")
        return data["rows"]

    def test_blind_insert_duplicates(self):
        self.assertEqual(self.signup("naive")[0], 201)
        self.assertEqual(self.signup("naive")[0], 201)
        self.assertEqual([row["signup_id"] for row in self.table()], ["signup-42"] * 2)

    def test_replay_reuses_and_new_signup_still_creates(self):
        status, first = self.signup("protected")
        self.assertEqual(status, 201)
        retry_status, retry = self.signup("protected")
        self.assertEqual(retry_status, 200)
        self.assertEqual(retry, {"created": False, "task": first["task"]})
        self.assertEqual(self.signup("protected", "signup-43")[0], 201)
        self.assertEqual([row["action_key"] for row in self.table()],
                         ["welcome-task:signup-42", "welcome-task:signup-43"])

    def test_timeout_occurs_after_commit_then_retry_is_safe(self):
        status, error = self.signup("protected", timeout=True)
        self.assertEqual(status, 504)
        self.assertNotIn("task", error)
        with sqlite3.connect(self.path) as db:
            actual = db.execute("SELECT task_id, action_key FROM welcome_tasks").fetchall()
        self.assertEqual(actual, [(1, "welcome-task:signup-42")])
        status, retry = self.signup("protected")
        self.assertEqual(status, 200)
        self.assertEqual(retry["task"]["task_id"], actual[0][0])
        self.assertEqual(len(self.table()), 1)

    def test_reset_and_bad_input(self):
        self.assertEqual(self.signup("protected", "real-user")[0], 400)
        self.assertEqual(self.signup("naive")[0], 201)
        self.assertEqual(self.request("/api/reset", {"confirm": True})[0], 200)
        self.assertEqual(self.table(), [])
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Run It Twice.", page)


if __name__ == "__main__":
    unittest.main()

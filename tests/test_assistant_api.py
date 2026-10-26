import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path

from dataatlas import server as app
from dataatlas.db import initialize


class AssistantApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        cls.old_settings = app.SETTINGS
        app.DB = Path(cls.temp.name) / "assistant-api.sqlite3"
        app.SETTINGS = replace(app.SETTINGS, data_home=Path(cls.temp.name),
                               openai_api_key=None, ai_model=None)
        initialize(app.DB, "assistant-test-password")
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.http.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=2)
        app.SETTINGS = cls.old_settings
        cls.temp.cleanup()

    def setUp(self):
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        status, _ = self.request("/api/auth/login",
            {"username": "demo", "password": "assistant-test-password"}, "POST")
        self.assertEqual(status, 200)

    def request(self, path, body=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
            headers={"Content-Type": "application/json"} if data is not None else {})
        try:
            with self.client.open(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read())
            finally:
                exc.close()

    def upload(self):
        boundary = "----AssistantBoundary"
        content = b"id,amount,note\n1,5,SECRET_RAW_VALUE\n2,,private\n"
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="assistant.csv"\r\n\r\n'.encode()
                + content + f"\r\n--{boundary}--\r\n".encode())
        request = urllib.request.Request(self.base + "/api/ingest/csv", data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                     "Idempotency-Key": "assistant-upload-001"})
        with self.client.open(request) as response:
            return json.loads(response.read())

    def test_assistant_is_workspace_authenticated_and_sql_is_only_a_suggestion(self):
        status, provider = self.request("/api/assistant/status")
        self.assertEqual((status, provider["provider"], provider["configured"]), (200, "local", False))
        dataset = self.upload()
        status, answer = self.request("/api/assistant/ask",
            {"question": "Which columns have missing values?", "dataset_id": dataset["id"]}, "POST")
        self.assertEqual(status, 200)
        self.assertEqual(answer["provider"], "local")
        self.assertIn("amount: 1 nulls", answer["answer"])
        self.assertEqual(answer["sources"][0]["id"], dataset["id"])
        self.assertNotIn("SECRET_RAW_VALUE", json.dumps(answer))

        status, candidate = self.request("/api/assistant/sql-suggest",
            {"question": f"preview 2 rows from {dataset['name']}"}, "POST")
        self.assertEqual(status, 200)
        self.assertTrue(candidate["valid"])
        self.assertIn("LIMIT 2", candidate["sql"])
        self.assertTrue(candidate["plan"])
        self.assertEqual(self.request("/api/queries")[1], [])
        self.assertEqual(self.request("/api/assistant/ask", {"question": "x" * 4001}, "POST")[0], 422)


if __name__ == "__main__":
    unittest.main()

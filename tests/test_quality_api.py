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


class QualityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        app.DB = Path(cls.temp.name) / "quality-api.sqlite3"
        app.SETTINGS = replace(app.SETTINGS, data_home=Path(cls.temp.name))
        initialize(app.DB, "quality-test-password")
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.http.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path, body=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data is not None else {})
        try:
            with client.open(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read())
            finally:
                exc.close()

    def test_rules_execute_persist_samples_alerts_and_auto_run_after_replacement(self):
        demo = self.client()
        self.assertEqual(self.request(demo, "/api/auth/login",
                         {"username": "demo", "password": "quality-test-password"}, "POST")[0], 200)
        boundary = "----QualityBoundary"
        content = b"id,amount\n1,5\n1,-2\n3,\n"
        upload = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="quality.csv"\r\n\r\n'.encode()
                  + content + f"\r\n--{boundary}--\r\n".encode())
        request = urllib.request.Request(self.base + "/api/ingest/csv", data=upload, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Idempotency-Key": "quality-upload-001"})
        with demo.open(request) as response:
            dataset = json.loads(response.read())
        base_rule = {"dataset_id": dataset["id"], "description": "",
                     "severity": "critical", "enabled": True}
        status, null_rule = self.request(demo, "/api/quality/rules", {
            **base_rule, "name": "Amount present", "target_column": "amount",
            "rule_type": "not_null", "config": {}}, "POST")
        self.assertEqual(status, 201)
        status, range_rule = self.request(demo, "/api/quality/rules", {
            **base_rule, "name": "Amount non-negative", "target_column": "amount",
            "rule_type": "numeric_range", "config": {"min": 0}}, "POST")
        self.assertEqual(status, 201)
        self.assertEqual(self.request(demo, "/api/quality/rules", {**base_rule, "name": "Bad",
            "target_column": "missing", "rule_type": "not_null", "config": {}}, "POST")[0], 422)

        status, run = self.request(demo, f"/api/quality/datasets/{dataset['id']}/run", {}, "POST")
        self.assertEqual((status, run["rules_total"], run["rules_passed"], run["rules_failed"]), (201, 2, 0, 2))
        detail = self.request(demo, f"/api/quality/runs/{run['id']}")[1]
        failure = next(result for result in detail["results"] if result["rule_id"] == range_rule["id"])
        self.assertEqual((failure["status"], failure["violations"], failure["samples"][0]["row_number"]),
                         ("failed", 1, 2))
        alerts = self.request(demo, "/api/alerts")[1]
        self.assertEqual(len(alerts), 2)
        self.assertEqual(self.request(demo, f"/api/alerts/{alerts[0]['id']}/read", {}, "POST")[0], 200)
        self.assertEqual(self.request(demo, "/api/alerts/unread-count")[1]["count"], 1)
        self.assertEqual(self.request(demo, f"/api/alerts/{alerts[0]['id']}/acknowledge", {}, "POST")[0], 200)

        updated = self.request(demo, f"/api/quality/rules/{range_rule['id']}", {"enabled": False}, "PATCH")[1]
        self.assertEqual((updated["version"], updated["enabled"]), (2, False))
        versions = self.request(demo, f"/api/quality/rules/{range_rule['id']}/versions")[1]
        self.assertEqual([version["version"] for version in versions], [2, 1])
        original_result = self.request(demo, f"/api/quality/runs/{run['id']}")[1]["results"]
        original_range = next(result for result in original_result if result["rule_id"] == range_rule["id"])
        self.assertEqual((original_range["rule_version"], original_range["config"]), (1, {"min": 0}))

        replacement = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="quality.csv"\r\n\r\n'.encode()
                       + b"id,amount\n4,8\n5,6\n" + f"\r\n--{boundary}--\r\n".encode())
        request = urllib.request.Request(self.base + "/api/ingest/csv", data=replacement, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Idempotency-Key": "quality-replace-001",
                     "DataAtlas-Replace-Dataset": dataset["id"]})
        with demo.open(request) as response:
            replaced = json.loads(response.read())
        self.assertEqual(replaced["id"], dataset["id"])
        runs = self.request(demo, "/api/quality/runs")[1]
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["rules_total"], 1)
        self.assertEqual(runs[0]["rules_failed"], 0)


if __name__ == "__main__":
    unittest.main()

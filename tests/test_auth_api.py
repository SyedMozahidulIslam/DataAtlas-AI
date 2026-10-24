import http.cookiejar
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from dataatlas import server as app
from dataatlas.db import initialize
from dataatlas.storage import LocalFileStorage


class AuthWorkspaceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        app.DB = Path(cls.temp.name) / "auth-api.sqlite3"
        app.SETTINGS = replace(app.SETTINGS, data_home=Path(cls.temp.name))
        initialize(app.DB, "test-demo-password")
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
        cookies = http.cookiejar.CookieJar()
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

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

    def test_authentication_and_workspace_isolation(self):
        anonymous = self.client()
        self.assertEqual(self.request(anonymous, "/api/datasets")[0], 401)

        demo = self.client()
        self.assertEqual(self.request(demo, "/api/auth/login", {"username": "demo", "password": "wrong-password"}, "POST")[0], 401)
        status, login = self.request(demo, "/api/auth/login", {"username": "demo", "password": "test-demo-password"}, "POST")
        self.assertEqual(status, 200)
        self.assertEqual(self.request(demo, "/api/auth/me")[1]["user"]["username"], "demo")

        boundary = "----AuthTestBoundary"
        payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="private.csv"\r\n\r\n'
                   .encode() + b"id,value\n1,17\n" + f"\r\n--{boundary}--\r\n".encode())
        req = urllib.request.Request(self.base + "/api/ingest/csv", data=payload, method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                              "Idempotency-Key": "private-upload-001"})
        with demo.open(req) as response:
            dataset = json.loads(response.read())
        self.assertEqual(dataset["row_count"], 1)
        self.assertEqual(dataset["status"], "succeeded")
        self.assertTrue(LocalFileStorage(app.DB.parent).read(dataset["storage_uri"]).endswith(b"id,value\n1,17\n"))
        job = self.request(demo, f"/api/jobs/{dataset['job_id']}")[1]
        self.assertEqual((job["status"], job["records_written"]), ("succeeded", 1))
        retry = urllib.request.Request(self.base + "/api/ingest/csv", data=payload, method="POST",
                                       headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                                "Idempotency-Key": "private-upload-001"})
        with demo.open(retry) as response:
            replay = json.loads(response.read())
            self.assertEqual(response.status, 200)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["id"], dataset["id"])
        different_file = payload.replace(b"17", b"18")
        conflict = urllib.request.Request(self.base + "/api/ingest/csv", data=different_file, method="POST",
                                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                                   "Idempotency-Key": "private-upload-001"})
        try:
            demo.open(conflict)
            self.fail("Idempotency key accepted a different upload")
        except urllib.error.HTTPError as exc:
            try:
                self.assertEqual(exc.code, 409)
            finally:
                exc.close()

        metadata_status, metadata = self.request(demo, f"/api/datasets/{dataset['id']}/metadata",
                                                 {"description": "Private sales sample", "tags": ["sales", "Sales", "demo"]},
                                                 "PATCH")
        self.assertEqual(metadata_status, 200)
        self.assertEqual(metadata["tags"], ["sales", "demo"])

        replacement_boundary = "----ReplaceDatasetBoundary"
        replacement_payload = (f'--{replacement_boundary}\r\nContent-Disposition: form-data; name="file"; filename="private.csv"\r\n\r\n'
                               .encode() + b"id,value,channel\n1,high,web\n" + f"\r\n--{replacement_boundary}--\r\n".encode())
        replacement_req = urllib.request.Request(self.base + "/api/ingest/csv", data=replacement_payload, method="POST",
                                                 headers={"Content-Type": f"multipart/form-data; boundary={replacement_boundary}",
                                                          "Idempotency-Key": "private-replace-0001",
                                                          "DataAtlas-Replace-Dataset": dataset["id"]})
        with demo.open(replacement_req) as response:
            replaced = json.loads(response.read())
        self.assertEqual(replaced["id"], dataset["id"])
        self.assertEqual((replaced["schema_version"], replaced["schema_change_count"], replaced["replaced"]), (2, 2, True))
        versions = self.request(demo, f"/api/datasets/{dataset['id']}/schemas")[1]
        self.assertEqual([version["version"] for version in versions], [2, 1])
        changes = self.request(demo, f"/api/datasets/{dataset['id']}/schema-changes")[1]
        self.assertEqual({change["change_type"] for change in changes}, {"column_added", "data_type_changed"})
        self.assertEqual(self.request(demo, f"/api/schema-changes/{changes[0]['id']}/acknowledge", {}, "POST")[0], 200)
        self.assertTrue(self.request(demo, f"/api/datasets/{dataset['id']}/schema-changes")[1][0]["acknowledged"])
        catalog = self.request(demo, "/api/datasets?q=Private%20sales")[1]
        self.assertEqual(catalog[0]["description"], "Private sales sample")
        profile = self.request(demo, f"/api/datasets/{dataset['id']}/profile")[1]
        self.assertEqual(profile["columns"][1]["type"], "string")
        self.assertEqual(profile["columns"][1]["top_values"][0]["value"], "high")
        table = next(item for item in self.request(demo, "/api/sql/tables")[1]
                     if item["dataset_id"] == dataset["id"])
        query_status, query = self.request(demo, "/api/queries",
                                           {"sql": f'SELECT id, value FROM "{table["table_name"]}"'}, "POST")
        self.assertEqual((query_status, query["row_count"], query["rows"][0]["value"]), (200, 1, "high"))
        failed_status, failed = self.request(demo, "/api/queries",
                                             {"sql": f'DROP TABLE "{table["table_name"]}"'}, "POST")
        self.assertEqual(failed_status, 422)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(len(self.request(demo, "/api/queries")[1]), 2)
        transform_status, transform = self.request(demo, "/api/transformations", {
            "name": "Normalize values", "description": "Uppercase the value field",
            "source_dataset_id": dataset["id"], "output_layer": "silver",
            "steps": [{"type": "derive", "column": "normalized", "source_column": "value", "operation": "upper"},
                      {"type": "select", "columns": ["id", "normalized"]}],
        }, "POST")
        self.assertEqual(transform_status, 201)
        quality_status, _ = self.request(demo, "/api/quality/rules", {
            "dataset_id": dataset["id"], "name": "Identifier present", "description": "",
            "target_column": "id", "rule_type": "not_null", "config": {},
            "severity": "warning", "enabled": True,
        }, "POST")
        self.assertEqual(quality_status, 201)
        transform_run_status, transform_run = self.request(
            demo, f"/api/transformations/{transform['id']}/run", {}, "POST")
        self.assertEqual((transform_run_status, transform_run["status"], transform_run["output_rows"]),
                         (201, "succeeded", 1))
        self.assertIsNotNone(transform_run["quality_run_id"])
        quality_run = self.request(demo, f"/api/quality/runs/{transform_run['quality_run_id']}")[1]
        self.assertEqual(quality_run["dataset_id"], dataset["id"])
        transformed = self.request(demo, f"/api/datasets/{transform_run['dataset_id']}")[1]
        self.assertEqual(transformed["layer"], "silver")
        self.assertEqual(transformed["sample"][0], {"id": "1", "normalized": "HIGH"})
        self.assertEqual(self.request(demo, f"/api/datasets/{transform_run['dataset_id']}/lineage")[1][0]["event_type"],
                         "transformation_run")
        upstream_graph = self.request(demo, f"/api/lineage/graph?dataset_id={transform_run['dataset_id']}&direction=upstream")[1]
        self.assertEqual({node["id"] for node in upstream_graph["nodes"]},
                         {dataset["id"], transform_run["dataset_id"]})
        self.assertEqual(upstream_graph["edges"][0]["source_dataset_id"], dataset["id"])
        downstream_graph = self.request(demo, f"/api/lineage/graph?dataset_id={dataset['id']}&direction=downstream")[1]
        self.assertIn(transform_run["dataset_id"], {node["id"] for node in downstream_graph["nodes"]})
        self.assertEqual(len(self.request(demo, "/api/transformation-runs")[1]), 1)
        update_status, updated_transform = self.request(demo, f"/api/transformations/{transform['id']}", {
            "name": "Normalize values", "description": "Updated recipe description",
            "source_dataset_id": dataset["id"], "output_layer": "silver", "steps": transform["config"]["steps"],
        }, "PATCH")
        self.assertEqual((update_status, updated_transform["revision"]), (200, 2))
        revisions = self.request(demo, f"/api/transformations/{transform['id']}/revisions")[1]
        self.assertEqual([row["revision"] for row in revisions], [2, 1])
        self.assertEqual(LocalFileStorage(app.DB.parent).read(dataset["storage_uri"]), b"id,value\n1,17\n")
        self.assertEqual(LocalFileStorage(app.DB.parent).read(replaced["storage_uri"]), b"id,value,channel\n1,high,web\n")

        invalid_boundary = "----InvalidJobBoundary"
        invalid_payload = (f'--{invalid_boundary}\r\nContent-Disposition: form-data; name="file"; filename="empty.csv"\r\n\r\n'
                           .encode() + b"id,value\n" + f"\r\n--{invalid_boundary}--\r\n".encode())
        invalid_req = urllib.request.Request(self.base + "/api/ingest/csv", data=invalid_payload, method="POST",
                                             headers={"Content-Type": f"multipart/form-data; boundary={invalid_boundary}",
                                                      "Idempotency-Key": "invalid-upload-01"})
        try:
            demo.open(invalid_req)
            self.fail("Invalid CSV unexpectedly succeeded")
        except urllib.error.HTTPError as exc:
            try:
                self.assertEqual(exc.code, 422)
                failed = json.loads(exc.read())
            finally:
                exc.close()
        self.assertEqual(self.request(demo, f"/api/jobs/{failed['job_id']}")[1]["status"], "failed")

        transient_boundary = "----TransientRetryBoundary"
        transient_payload = (f'--{transient_boundary}\r\nContent-Disposition: form-data; name="file"; filename="retryable.csv"\r\n\r\n'
                             .encode() + b"id,value\n1,ok\n" + f"\r\n--{transient_boundary}--\r\n".encode())
        transient_req = urllib.request.Request(self.base + "/api/ingest/csv", data=transient_payload, method="POST",
                                               headers={"Content-Type": f"multipart/form-data; boundary={transient_boundary}",
                                                        "Idempotency-Key": "transient-upload-001"})
        with patch("dataatlas.jobs.LocalFileStorage.write_bronze_csv", side_effect=OSError("simulated storage outage")):
            try:
                demo.open(transient_req)
                self.fail("Expected the simulated transient storage failure")
            except urllib.error.HTTPError as exc:
                try:
                    self.assertEqual(exc.code, 500)
                    transient_failure = json.loads(exc.read())
                finally:
                    exc.close()
        failed_job = self.request(demo, f"/api/jobs/{transient_failure['job_id']}")[1]
        self.assertEqual((failed_job["failure_type"], failed_job["retry_available"]), ("transient", 1))
        failed_events = self.request(demo, f"/api/jobs/{transient_failure['job_id']}/events")[1]
        self.assertEqual([event["event_type"] for event in failed_events], ["queued", "started", "execution_failed"])
        retry_req = urllib.request.Request(self.base + "/api/ingest/csv", data=transient_payload, method="POST",
                                           headers={"Content-Type": f"multipart/form-data; boundary={transient_boundary}",
                                                    "Idempotency-Key": "transient-retry-0001",
                                                    "DataAtlas-Retry-Of": transient_failure["job_id"]})
        with demo.open(retry_req) as response:
            retried = json.loads(response.read())
        retry_replay_req = urllib.request.Request(self.base + "/api/ingest/csv", data=transient_payload, method="POST",
                                                  headers={"Content-Type": f"multipart/form-data; boundary={transient_boundary}",
                                                           "Idempotency-Key": "transient-retry-0001",
                                                           "DataAtlas-Retry-Of": transient_failure["job_id"]})
        with demo.open(retry_replay_req) as response:
            retry_replay = json.loads(response.read())
            self.assertEqual(response.status, 200)
        self.assertTrue(retry_replay["replayed"])
        retry_job = self.request(demo, f"/api/jobs/{retried['job_id']}")[1]
        self.assertEqual((retry_job["status"], retry_job["attempt_number"], retry_job["retry_of_job_id"]),
                         ("succeeded", 2, transient_failure["job_id"]))
        self.assertEqual(self.request(demo, f"/api/jobs/{transient_failure['job_id']}")[1]["retry_available"], 0)
        invalid_retry = urllib.request.Request(self.base + "/api/ingest/csv", data=invalid_payload, method="POST",
                                               headers={"Content-Type": f"multipart/form-data; boundary={invalid_boundary}",
                                                        "Idempotency-Key": "invalid-retry-key-0001",
                                                        "DataAtlas-Retry-Of": failed["job_id"]})
        try:
            demo.open(invalid_retry)
            self.fail("A validation failure was incorrectly made retryable")
        except urllib.error.HTTPError as exc:
            try:
                self.assertEqual(exc.code, 409)
            finally:
                exc.close()

        alice = self.client()
        status, registered = self.request(alice, "/api/auth/register",
                                          {"username": "alice", "password": "correct-horse-12"}, "POST")
        self.assertEqual(status, 201)
        self.assertEqual(self.request(alice, "/api/auth/register",
                                      {"username": "alice", "password": "correct-horse-12"}, "POST")[0], 409)
        self.assertEqual(self.request(alice, "/api/datasets")[1], [])
        self.assertEqual(self.request(alice, "/api/jobs")[1], [])
        self.assertEqual(self.request(alice, "/api/sql/tables")[1], [])
        self.assertEqual(self.request(alice, "/api/queries")[1], [])
        self.assertEqual(self.request(alice, "/api/transformations")[1], [])
        self.assertEqual(self.request(alice, f"/api/transformations/{transform['id']}/run", {}, "POST")[0], 404)
        self.assertEqual(self.request(alice, f"/api/lineage/graph?dataset_id={dataset['id']}")[0], 404)
        self.assertEqual(self.request(alice, f"/api/datasets/{dataset['id']}")[0], 404)

        status, _ = self.request(alice, "/api/workspaces/select",
                                 {"workspace_id": login["workspace"]["id"]}, "POST")
        self.assertEqual(status, 403)
        status, _ = self.request(demo, f"/api/workspaces/{login['workspace']['id']}/members",
                                 {"username": "alice"}, "POST")
        self.assertEqual(status, 201)
        status, _ = self.request(alice, "/api/workspaces/select",
                                 {"workspace_id": login["workspace"]["id"]}, "POST")
        self.assertEqual(status, 200)
        self.assertEqual(len(self.request(alice, "/api/datasets")[1]), 3)
        self.assertEqual(self.request(alice, "/api/auth/logout", {}, "POST")[0], 200)
        self.assertEqual(self.request(alice, "/api/auth/me")[0], 401)

    def test_rejects_cross_origin_mutation(self):
        req = urllib.request.Request(self.base + "/api/auth/login", data=b'{"username":"demo","password":"test-demo-password"}',
                                     method="POST", headers={"Content-Type": "application/json", "Origin": "https://attacker.example"})
        try:
            urllib.request.urlopen(req)
            self.fail("Cross-origin mutation unexpectedly succeeded")
        except urllib.error.HTTPError as exc:
            try:
                self.assertEqual(exc.code, 403)
            finally:
                exc.close()

    def test_demo_seed_uses_authenticated_ingestion(self):
        from dataatlas import seed

        with patch.dict(os.environ, {"DATAATLAS_HOST": "127.0.0.1",
                                     "DATAATLAS_PORT": str(self.http.server_address[1]),
                                     "DATAATLAS_DEMO_PASSWORD": "test-demo-password"}):
            with redirect_stdout(io.StringIO()):
                seed.main()
        demo = self.client()
        self.request(demo, "/api/auth/login", {"username": "demo", "password": "test-demo-password"}, "POST")
        datasets = self.request(demo, "/api/datasets")[1]
        sample = next((dataset for dataset in datasets if dataset["source_name"] == "sample_orders.csv"), None)
        self.assertIsNotNone(sample)
        self.assertEqual(sample["row_count"], 5)


if __name__ == "__main__":
    unittest.main()

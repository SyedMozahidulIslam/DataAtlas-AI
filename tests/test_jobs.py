import tempfile
import unittest
import uuid
from pathlib import Path

from dataatlas.db import initialize, session
from dataatlas.jobs import recover_interrupted_jobs


class JobRecoveryTests(unittest.TestCase):
    def test_restart_marks_running_jobs_failed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.sqlite3"
            initialize(path, "job-recovery-password")
            with session(path) as db:
                user = db.execute("SELECT id FROM users WHERE username='demo'").fetchone()["id"]
                workspace = db.execute("SELECT workspace_id FROM memberships WHERE user_id=?", (user,)).fetchone()[0]
                db.execute("""INSERT INTO ingestion_jobs
                    (id,workspace_id,user_id,source_name,status,idempotency_key,upload_sha256,created_at,started_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                           (uuid.uuid4().hex, workspace, user, "unfinished.csv", "running", "unfinished-job-001",
                            "0" * 64, "2026-10-24T00:00:00+00:00", "2026-10-24T00:00:01+00:00"))
            recover_interrupted_jobs(path)
            with session(path) as db:
                job = db.execute("SELECT status,error_message,completed_at FROM ingestion_jobs WHERE source_name='unfinished.csv'").fetchone()
                self.assertEqual(job["status"], "failed")
                self.assertIn("stopped", job["error_message"])
                self.assertIsNotNone(job["completed_at"])
                retryable = db.execute("SELECT failure_type FROM ingestion_jobs WHERE source_name='unfinished.csv'").fetchone()
                self.assertEqual(retryable["failure_type"], "transient")
                event = db.execute("SELECT event_type FROM ingestion_job_events WHERE job_id=(SELECT id FROM ingestion_jobs WHERE source_name='unfinished.csv')").fetchone()
                self.assertEqual(event["event_type"], "recovered_after_restart")


if __name__ == "__main__":
    unittest.main()

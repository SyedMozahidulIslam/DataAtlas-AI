"""Persistent, idempotent CSV ingestion job orchestration."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .catalog import compare_schemas, schema_change_row
from .config import Settings
from .db import session
from .ingestion import parse_csv
from .storage import LocalFileStorage
from .quality import record_alert, run_dataset_rules


class IngestionFailure(Exception):
    def __init__(self, message: str, *, status: int, job_id: str):
        super().__init__(message)
        self.status = status
        self.job_id = job_id


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_job_event(db, job_id: str, workspace_id: str, event_type: str, status: str,
                 details: dict | None = None, created_at: str | None = None):
    db.execute("INSERT INTO ingestion_job_events(id,job_id,workspace_id,event_type,status,details_json,created_at) "
               "VALUES(?,?,?,?,?,?,?)",
               (uuid.uuid4().hex, job_id, workspace_id, event_type, status,
                json.dumps(details or {}), created_at or utc_now()))


def create_job(db_path: Path, workspace_id: str, user_id: str, filename: str, raw: bytes,
               idempotency_key: str, target_dataset_id: str | None,
               retry_of_job_id: str | None = None):
    upload_hash = hashlib.sha256(raw).hexdigest()
    job_id, created = uuid.uuid4().hex, utc_now()
    with session(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("""SELECT id,status,source_name,upload_sha256,target_dataset_id,retry_of_job_id,result_json,error_message,
            dataset_id,records_read,records_written,rejected_records,storage_uri,created_at,started_at,completed_at
            FROM ingestion_jobs WHERE workspace_id=? AND idempotency_key=?""",
                             (workspace_id, idempotency_key)).fetchone()
        if existing:
            if (existing["upload_sha256"] != upload_hash or existing["target_dataset_id"] != target_dataset_id
                    or existing["source_name"] != filename or existing["retry_of_job_id"] != retry_of_job_id):
                raise IngestionFailure("This idempotency key was already used for a different request.",
                                        status=409, job_id=existing["id"])
            return dict(existing), True
        attempt = 1
        if retry_of_job_id:
            parent = db.execute("SELECT attempt_number FROM ingestion_jobs WHERE id=? AND workspace_id=?",
                                (retry_of_job_id, workspace_id)).fetchone()
            if not parent:
                raise IngestionFailure("Retry source job not found.", status=404, job_id="")
            attempt = parent["attempt_number"] + 1
        db.execute("""INSERT INTO ingestion_jobs
            (id,workspace_id,user_id,source_name,status,idempotency_key,upload_sha256,target_dataset_id,
             retry_of_job_id,attempt_number,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                   (job_id, workspace_id, user_id, filename, "queued", idempotency_key, upload_hash,
                    target_dataset_id, retry_of_job_id, attempt, created))
        add_job_event(db, job_id, workspace_id, "queued", "queued",
                      {"attempt_number": attempt, "retry_of_job_id": retry_of_job_id}, created)
    return {"id": job_id, "status": "queued", "upload_sha256": upload_hash,
            "attempt_number": attempt, "retry_of_job_id": retry_of_job_id}, False


def ingest_csv(db_path: Path, settings: Settings, workspace_id: str, user_id: str,
               filename: str, raw: bytes, idempotency_key: str,
               target_dataset_id: str | None = None, retry_of_job_id: str | None = None):
    filename = Path(filename).name
    if target_dataset_id:
        with session(db_path) as db:
            exists = db.execute("SELECT 1 FROM datasets WHERE id=? AND workspace_id=?",
                                (target_dataset_id, workspace_id)).fetchone()
        if not exists:
            raise IngestionFailure("Dataset not found in the active workspace.", status=404, job_id="")
    job, replay = create_job(db_path, workspace_id, user_id, filename, raw,
                             idempotency_key, target_dataset_id, retry_of_job_id)
    if replay:
        if job["status"] == "succeeded" and job["result_json"]:
            return json.loads(job["result_json"]), 200, True
        if job["status"] == "failed":
            raise IngestionFailure(job["error_message"] or "Ingestion failed.", status=422, job_id=job["id"])
        return {"job_id": job["id"], "status": job["status"]}, 202, True

    job_id, started, started_clock = job["id"], utc_now(), time.perf_counter()
    with session(db_path) as db:
        db.execute("UPDATE ingestion_jobs SET status='running',started_at=? WHERE id=?", (started, job_id))
        add_job_event(db, job_id, workspace_id, "started", "running",
                      {"attempt_number": job["attempt_number"]}, started)
    try:
        columns, records, schema = parse_csv(filename, raw, settings)
    except ValueError as exc:
        completed, duration = utc_now(), round((time.perf_counter() - started_clock) * 1000)
        with session(db_path) as db:
            db.execute("""UPDATE ingestion_jobs SET status='failed',error_message=?,failure_type='validation',
                completed_at=?,duration_ms=? WHERE id=?""", (str(exc), completed, duration, job_id))
            add_job_event(db, job_id, workspace_id, "validation_failed", "failed", {"error": str(exc)}, completed)
        raise IngestionFailure(str(exc), status=422, job_id=job_id) from exc

    with session(db_path) as db:
        db.execute("UPDATE ingestion_jobs SET records_read=? WHERE id=?", (len(records), job_id))

    dataset_id = target_dataset_id or uuid.uuid4().hex
    timestamp = utc_now()
    storage = LocalFileStorage(settings.data_home)
    try:
        stored = storage.write_bronze_csv(workspace_id, dataset_id, raw, version_id=job_id)
        with session(db_path) as db:
            if target_dataset_id:
                old = db.execute("SELECT * FROM datasets WHERE id=? AND workspace_id=?",
                                 (target_dataset_id, workspace_id)).fetchone()
                if not old:
                    raise IngestionFailure("Dataset disappeared from the active workspace.", status=404, job_id=job_id)
                previous_schema = json.loads(old["schema_json"])
                changes = compare_schemas(previous_schema, schema)
                version = old["schema_version"] + (1 if changes else 0)
                db.execute("""UPDATE datasets SET source_name=?,updated_at=?,row_count=?,columns_json=?,
                    schema_json=?,records_json=?,layer='bronze',storage_uri=?,storage_format='csv',
                    storage_bytes=?,content_sha256=?,schema_version=? WHERE id=? AND workspace_id=?""",
                           (filename, timestamp, len(records), json.dumps(columns), json.dumps(schema),
                            json.dumps(records), stored.uri, stored.byte_count, stored.sha256, version,
                            target_dataset_id, workspace_id))
                name = old["name"]
                if changes:
                    db.execute("""INSERT INTO dataset_schema_versions
                        (dataset_id,version,schema_json,recorded_at,ingestion_job_id) VALUES(?,?,?,?,?)""",
                               (dataset_id, version, json.dumps(schema), timestamp, job_id))
                    for change in changes:
                        previous_json, current_json = schema_change_row(change)
                        db.execute("""INSERT INTO schema_changes
                            (id,dataset_id,from_version,to_version,column_name,change_type,previous_json,current_json,
                             severity,detected_at,ingestion_job_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                   (uuid.uuid4().hex, dataset_id, old["schema_version"], version,
                                    change["column_name"], change["change_type"], previous_json, current_json,
                                    change["severity"], timestamp, job_id))
            else:
                base = re.sub(r"[^a-zA-Z0-9_]+", "_", Path(filename).stem).strip("_").lower() or "dataset"
                name, suffix = base, 2
                while db.execute("SELECT 1 FROM datasets WHERE name=?", (name,)).fetchone():
                    name, suffix = f"{base}_{suffix}", suffix + 1
                version, changes = 1, []
                db.execute("""INSERT INTO datasets
                    (id,name,source_name,created_at,updated_at,row_count,columns_json,schema_json,records_json,layer,
                     workspace_id,storage_uri,storage_format,storage_bytes,content_sha256,schema_version)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (dataset_id, name, filename, timestamp, timestamp, len(records), json.dumps(columns),
                            json.dumps(schema), json.dumps(records), "bronze", workspace_id, stored.uri, "csv",
                            stored.byte_count, stored.sha256, version))
                db.execute("""INSERT INTO dataset_schema_versions
                    (dataset_id,version,schema_json,recorded_at,ingestion_job_id) VALUES(?,?,?,?,?)""",
                           (dataset_id, version, json.dumps(schema), timestamp, job_id))

            if changes:
                severity = "critical" if any(change["severity"] == "breaking" for change in changes) else (
                    "warning" if any(change["severity"] == "warning" for change in changes) else "info")
                changed_columns = ", ".join(change["column_name"] for change in changes[:5])
                record_alert(db, workspace_id, f"schema:{job_id}:{version}", "schema_change", dataset_id,
                             severity, f"Schema changed: {name}",
                             f"Schema v{version} recorded {len(changes)} change(s): {changed_columns}.",
                             "dataset", dataset_id, timestamp)

            details = {"source_file": filename, "rows_written": len(records), "layer": "bronze",
                       "job_id": job_id, "storage_uri": stored.uri, "sha256": stored.sha256,
                       "schema_version": version, "schema_change_count": len(changes)}
            db.execute("INSERT INTO lineage VALUES(?,?,?,?,?)",
                       (uuid.uuid4().hex, dataset_id, "csv_ingestion", json.dumps(details), timestamp))
            result = {"id": dataset_id, "name": name, "row_count": len(records), "columns": schema,
                      "layer": "bronze", "created_at": timestamp, "updated_at": timestamp,
                      "job_id": job_id, "status": "succeeded", "storage_uri": stored.uri,
                      "schema_version": version, "schema_change_count": len(changes), "replaced": bool(target_dataset_id)}
            completed, duration = utc_now(), round((time.perf_counter() - started_clock) * 1000)
            db.execute("""UPDATE ingestion_jobs SET status='succeeded',dataset_id=?,schema_version=?,records_read=?,
                records_written=?,storage_uri=?,completed_at=?,duration_ms=?,result_json=? WHERE id=?""",
                       (dataset_id, version, len(records), len(records), stored.uri, completed, duration,
                        json.dumps(result), job_id))
            add_job_event(db, job_id, workspace_id, "completed", "succeeded",
                          {"dataset_id": dataset_id, "records_written": len(records), "duration_ms": duration}, completed)
            try:
                run_dataset_rules(db, workspace_id, dataset_id)
            except (ValueError, TypeError, KeyError):
                # Quality is observational: a bad rule must not roll back a valid ingestion.
                pass
        return result, 201, False
    except Exception as exc:
        try:
            storage.delete(workspace_id, dataset_id, version_id=job_id)
        except OSError:
            pass
        completed, duration = utc_now(), round((time.perf_counter() - started_clock) * 1000)
        with session(db_path) as db:
            if isinstance(exc, IngestionFailure):
                message = str(exc)
            else:
                message = "Storage or catalog write failed."
            retryable = not isinstance(exc, IngestionFailure) or exc.status >= 500
            failure_type = "transient" if retryable else "permanent"
            db.execute("""UPDATE ingestion_jobs SET status='failed',error_message=?,failure_type=?,completed_at=?,
                duration_ms=? WHERE id=?""", (message, failure_type, completed, duration, job_id))
            add_job_event(db, job_id, workspace_id, "execution_failed", "failed",
                          {"error": message, "failure_type": failure_type, "duration_ms": duration}, completed)
        if isinstance(exc, IngestionFailure):
            raise
        if isinstance(exc, sqlite3.Error):
            raise IngestionFailure("Could not persist the ingested dataset.", status=500, job_id=job_id) from exc
        if isinstance(exc, OSError):
            raise IngestionFailure("Could not write the Bronze data file.", status=500, job_id=job_id) from exc
        raise


def recover_interrupted_jobs(db_path: Path):
    """Mark interrupted executions retryable and record recovery events."""
    with session(db_path) as db:
        interrupted = db.execute("SELECT id,workspace_id FROM ingestion_jobs WHERE status IN ('queued','running')").fetchall()
        completed = utc_now()
        for job in interrupted:
            db.execute("""UPDATE ingestion_jobs SET status='failed',failure_type='transient',
                error_message='Server stopped before the job completed.',completed_at=? WHERE id=?""",
                       (completed, job["id"]))
            add_job_event(db, job["id"], job["workspace_id"], "recovered_after_restart", "failed",
                          {"failure_type": "transient"}, completed)

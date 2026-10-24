"""Dependency-free DataAtlas local API and static web server."""
from __future__ import annotations

import json
import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .accounts import authenticate, change_workspace, create_account, create_session, resolve_session
from .catalog import validate_metadata
from .config import Settings
from .db import LATEST_SCHEMA_VERSION, initialize, session
from .jobs import IngestionFailure, ingest_csv as run_ingestion, recover_interrupted_jobs
from .lineage import build_lineage_graph
from .profiling import profile_dataset
from .quality import record_alert, run_dataset_rules, validate_rule
from .security import token_digest
from .sql_workspace import execute_readonly, table_catalog
from .transformations import run_steps, validate_definition

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
SETTINGS = Settings.from_env()
DB = SETTINGS.data_home / "dataatlas.sqlite3"
SESSION_COOKIE = "dataatlas_session"
SESSION_MAX_AGE = 12 * 60 * 60


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Handler(BaseHTTPRequestHandler):
    server_version = "DataAtlas/0.3"

    def log_message(self, fmt, *args):
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")

    def send_json(self, status, value, headers=None):
        data = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def send_cookie(self, token: str, *, clear=False):
        age = 0 if clear else SESSION_MAX_AGE
        value = "" if clear else token
        return {"Set-Cookie": f"{SESSION_COOKIE}={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={age}"}

    def read_bytes(self, maximum: int):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid Content-Length header.")
        if length <= 0:
            raise ValueError("Request body is empty.")
        if length > maximum:
            raise OverflowError(f"Request body exceeds the {maximum:,} byte limit.")
        return self.rfile.read(length)

    def read_json(self):
        try:
            raw = self.read_bytes(64 * 1024)
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid UTF-8 JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object.")
        return value

    def same_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlparse(origin)
        return parsed.netloc.lower() == self.headers.get("Host", "").lower() and parsed.scheme in ("http", "https")

    def session_token(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        return cookie[SESSION_COOKIE].value if SESSION_COOKIE in cookie else None

    def principal(self):
        with session(DB) as db:
            return resolve_session(db, self.session_token())

    def require_user(self):
        identity = self.principal()
        if not identity:
            self.send_json(401, {"error": "Sign in to access this resource."})
            return None
        return identity

    def serve_static(self, path: str):
        if path in ("/", "/index.html"):
            target = STATIC / "index.html"
        elif path.startswith("/static/"):
            target = (STATIC / path.removeprefix("/static/")).resolve()
            if STATIC.resolve() not in target.parents:
                return self.send_json(404, {"error": "Not found"})
        else:
            return False
        if not target.is_file():
            return self.send_json(404, {"error": "Not found"})
        data = target.read_bytes()
        mime = "text/html; charset=utf-8" if target.suffix == ".html" else "text/css; charset=utf-8" if target.suffix == ".css" else "text/javascript; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json(200, {"status": "ok", "storage": "sqlite", "schema_version": LATEST_SCHEMA_VERSION,
                                        "slice": "csv-catalog-profile-workspaces"})
        if path == "/" or path == "/index.html" or path.startswith("/static/"):
            return self.serve_static(path)
        if not path.startswith("/api/"):
            return self.send_json(404, {"error": "Not found"})
        identity = self.require_user()
        if not identity:
            return
        if path == "/api/auth/me":
            with session(DB) as db:
                workspaces = db.execute("""SELECT w.id,w.name,m.role FROM memberships m JOIN workspaces w
                    ON w.id=m.workspace_id WHERE m.user_id=? ORDER BY w.created_at""", (identity["user_id"],)).fetchall()
            return self.send_json(200, {
                "user": {"id": identity["user_id"], "username": identity["username"]},
                "workspace": {"id": identity["active_workspace_id"], "name": identity["workspace_name"], "role": identity["role"]},
                "workspaces": [dict(row) for row in workspaces],
            })
        if path == "/api/workspaces":
            with session(DB) as db:
                rows = db.execute("""SELECT w.id,w.name,m.role FROM memberships m JOIN workspaces w
                    ON w.id=m.workspace_id WHERE m.user_id=? ORDER BY w.created_at""", (identity["user_id"],)).fetchall()
            return self.send_json(200, [dict(row) for row in rows])
        if path == "/api/jobs":
            with session(DB) as db:
                rows = db.execute("""SELECT id,source_name,status,dataset_id,records_read,records_written,
                    rejected_records,error_message,created_at,started_at,completed_at,storage_uri,schema_version,
                    duration_ms,failure_type,retry_of_job_id,attempt_number,target_dataset_id,
                    CASE WHEN failure_type='transient' AND attempt_number<3 AND NOT EXISTS(
                        SELECT 1 FROM ingestion_jobs child WHERE child.retry_of_job_id=ingestion_jobs.id
                    ) THEN 1 ELSE 0 END AS retry_available
                    FROM ingestion_jobs WHERE workspace_id=? ORDER BY created_at DESC LIMIT 100""",
                                  (identity["active_workspace_id"],)).fetchall()
            return self.send_json(200, [dict(row) for row in rows])
        if path == "/api/sql/tables":
            with session(DB) as db:
                rows = db.execute("""SELECT id,name,row_count,schema_json,records_json,storage_bytes FROM datasets
                    WHERE workspace_id=? ORDER BY name COLLATE NOCASE""",
                                  (identity["active_workspace_id"],)).fetchall()
            return self.send_json(200, table_catalog([dict(row) for row in rows]))
        if path == "/api/lineage/graph":
            query = parse_qs(urlparse(self.path).query)
            focus_id = query.get("dataset_id", [""])[0]
            direction = query.get("direction", ["both"])[0]
            try:
                depth = int(query.get("depth", ["4"])[0])
                with session(DB) as db:
                    graph = build_lineage_graph(db, identity["active_workspace_id"], focus_id, direction, depth)
            except LookupError as exc:
                return self.send_json(404, {"error": str(exc)})
            except ValueError as exc:
                return self.send_json(422, {"error": str(exc)})
            return self.send_json(200, graph)
        if path == "/api/queries":
            with session(DB) as db:
                rows = db.execute("""SELECT id,sql_text,status,columns_json,result_json,row_count,duration_ms,
                    error_message,created_at FROM query_history WHERE workspace_id=?
                    ORDER BY created_at DESC LIMIT 50""", (identity["active_workspace_id"],)).fetchall()
            return self.send_json(200, [{**dict(row), "columns": json.loads(row["columns_json"]),
                                         "rows": json.loads(row["result_json"])} for row in rows])
        if path == "/api/transformations":
            with session(DB) as db:
                rows = db.execute("""SELECT id,name,description,config_json,revision,created_at,updated_at
                    FROM transformations WHERE workspace_id=? ORDER BY updated_at DESC""",
                                  (identity["active_workspace_id"],)).fetchall()
            return self.send_json(200, [{**dict(row), "config": json.loads(row["config_json"])} for row in rows])
        if path.startswith("/api/transformations/") and path.endswith("/revisions"):
            transformation_id = path.strip("/").split("/")[2]
            with session(DB) as db:
                rows = db.execute("""SELECT r.revision,r.config_json,r.created_by,r.created_at
                    FROM transformation_revisions r JOIN transformations t ON t.id=r.transformation_id
                    WHERE r.transformation_id=? AND t.workspace_id=? ORDER BY r.revision DESC""",
                                  (transformation_id, identity["active_workspace_id"])).fetchall()
            if not rows:
                return self.send_json(404, {"error": "Transformation revisions not found."})
            return self.send_json(200, [{**dict(row), "config": json.loads(row["config_json"])} for row in rows])
        if path == "/api/transformation-runs":
            with session(DB) as db:
                rows = db.execute("""SELECT id,transformation_id,revision,source_dataset_id,output_dataset_id,
                    status,input_rows,output_rows,duration_ms,error_message,created_at,completed_at
                    FROM transformation_runs WHERE workspace_id=? ORDER BY created_at DESC LIMIT 100""",
                                  (identity["active_workspace_id"],)).fetchall()
            return self.send_json(200, [dict(row) for row in rows])
        if path == "/api/quality/rules":
            dataset_id = parse_qs(urlparse(self.path).query).get("dataset_id", [""])[0]
            with session(DB) as db:
                query = """SELECT r.*,d.name AS dataset_name FROM quality_rules r JOIN datasets d ON d.id=r.dataset_id
                    WHERE r.workspace_id=?"""
                params = [identity["active_workspace_id"]]
                if dataset_id:
                    query += " AND r.dataset_id=?"
                    params.append(dataset_id)
                query += " ORDER BY r.updated_at DESC"
                rows = db.execute(query, params).fetchall()
            return self.send_json(200, [{**dict(row), "config": json.loads(row["config_json"]),
                                         "enabled": bool(row["enabled"])} for row in rows])
        if path.startswith("/api/quality/rules/") and path.endswith("/versions"):
            rule_id = path.strip("/").split("/")[3]
            with session(DB) as db:
                rows = db.execute("""SELECT v.* FROM quality_rule_versions v JOIN quality_rules r ON r.id=v.rule_id
                    WHERE v.rule_id=? AND r.workspace_id=? ORDER BY v.version DESC""",
                                  (rule_id, identity["active_workspace_id"])).fetchall()
            if not rows:
                return self.send_json(404, {"error": "Quality rule versions not found."})
            return self.send_json(200, [{**dict(row), "config": json.loads(row["config_json"]),
                                         "enabled": bool(row["enabled"])} for row in rows])
        if path == "/api/quality/runs":
            with session(DB) as db:
                rows = db.execute("""SELECT q.*,d.name AS dataset_name FROM quality_runs q JOIN datasets d ON d.id=q.dataset_id
                    WHERE q.workspace_id=? ORDER BY q.completed_at DESC LIMIT 100""",
                                  (identity["active_workspace_id"],)).fetchall()
            return self.send_json(200, [dict(row) for row in rows])
        if path.startswith("/api/quality/runs/"):
            run_id = path.strip("/").split("/")[3]
            with session(DB) as db:
                run = db.execute("""SELECT q.*,d.name AS dataset_name FROM quality_runs q JOIN datasets d ON d.id=q.dataset_id
                    WHERE q.id=? AND q.workspace_id=?""", (run_id, identity["active_workspace_id"])).fetchone()
                results = db.execute("""SELECT r.*,q.name AS rule_name,q.severity,q.rule_type,q.target_column,q.config_json
                    FROM quality_results r JOIN quality_rule_versions q
                      ON q.rule_id=r.rule_id AND q.version=r.rule_version
                    WHERE r.run_id=? ORDER BY q.created_at,q.rule_id""", (run_id,)).fetchall() if run else []
            if not run:
                return self.send_json(404, {"error": "Quality run not found."})
            return self.send_json(200, {**dict(run), "results": [
                {**dict(item), "samples": json.loads(item["samples_json"]),
                 "config": json.loads(item["config_json"])} for item in results]})
        if path == "/api/alerts":
            with session(DB) as db:
                rows = db.execute("""SELECT * FROM alerts WHERE workspace_id=? ORDER BY
                    CASE WHEN read_at IS NULL THEN 0 ELSE 1 END,created_at DESC LIMIT 100""",
                                  (identity["active_workspace_id"],)).fetchall()
            return self.send_json(200, [dict(row) for row in rows])
        if path == "/api/alerts/unread-count":
            with session(DB) as db:
                count = db.execute("SELECT COUNT(*) FROM alerts WHERE workspace_id=? AND read_at IS NULL",
                                   (identity["active_workspace_id"],)).fetchone()[0]
            return self.send_json(200, {"count": count})
        if path.startswith("/api/jobs/"):
            parts = path.strip("/").split("/")
            job_id = parts[2]
            with session(DB) as db:
                row = db.execute("""SELECT id,source_name,status,dataset_id,records_read,records_written,
                    rejected_records,error_message,created_at,started_at,completed_at,storage_uri,schema_version,
                    duration_ms,failure_type,retry_of_job_id,attempt_number,target_dataset_id,
                    CASE WHEN failure_type='transient' AND attempt_number<3 AND NOT EXISTS(
                        SELECT 1 FROM ingestion_jobs child WHERE child.retry_of_job_id=ingestion_jobs.id
                    ) THEN 1 ELSE 0 END AS retry_available
                    FROM ingestion_jobs WHERE id=? AND workspace_id=?""",
                                  (job_id, identity["active_workspace_id"])).fetchone()
            if not row:
                return self.send_json(404, {"error": "Job not found."})
            if len(parts) == 4 and parts[3] == "events":
                with session(DB) as db:
                    events = db.execute("""SELECT event_type,status,details_json,created_at
                        FROM ingestion_job_events WHERE job_id=? AND workspace_id=? ORDER BY created_at,id""",
                                        (job_id, identity["active_workspace_id"])).fetchall()
                return self.send_json(200, [{**dict(event), "details": json.loads(event["details_json"])}
                                            for event in events])
            if len(parts) != 3:
                return self.send_json(404, {"error": "Not found"})
            return self.send_json(200, dict(row))
        if path == "/api/datasets":
            query = parse_qs(urlparse(self.path).query)
            search = query.get("q", [""])[0].strip()[:120]
            layer = query.get("layer", [""])[0].strip().lower()
            source = query.get("source", [""])[0].strip()[:120]
            sort = query.get("sort", ["updated"])[0]
            order = {"updated": "updated_at DESC", "name": "name COLLATE NOCASE ASC",
                     "rows": "row_count DESC"}.get(sort, "updated_at DESC")
            clauses, params = ["workspace_id=?"], [identity["active_workspace_id"]]
            if search:
                clauses.append("(name LIKE ? OR source_name LIKE ? OR description LIKE ? OR tags_json LIKE ?)")
                pattern = f"%{search}%"
                params.extend([pattern] * 4)
            if layer in ("bronze", "silver", "gold"):
                clauses.append("layer=?")
                params.append(layer)
            if source:
                clauses.append("source_name LIKE ?")
                params.append(f"%{source}%")
            with session(DB) as db:
                rows = db.execute(f"""SELECT id,name,description,tags_json,source_name,created_at,updated_at,
                    row_count,columns_json,layer,schema_version FROM datasets WHERE {' AND '.join(clauses)} ORDER BY {order}""",
                                  params).fetchall()
            return self.send_json(200, [{**dict(row), "columns": json.loads(row["columns_json"])} for row in rows])
        if path.startswith("/api/datasets/"):
            return self.get_dataset(path, identity)
        return self.send_json(404, {"error": "Not found"})

    def get_dataset(self, path: str, identity):
        parts = path.strip("/").split("/")
        if len(parts) not in (3, 4):
            return self.send_json(404, {"error": "Not found"})
        dataset_id = parts[2]
        with session(DB) as db:
            row = db.execute("SELECT * FROM datasets WHERE id=? AND workspace_id=?",
                             (dataset_id, identity["active_workspace_id"])).fetchone()
            if not row:
                return self.send_json(404, {"error": "Dataset not found."})
            if len(parts) == 4 and parts[3] == "lineage":
                events = db.execute("SELECT event_type,details,created_at FROM lineage WHERE dataset_id=? ORDER BY created_at",
                                    (dataset_id,)).fetchall()
                result = [{**dict(event), "details": json.loads(event["details"])} for event in events]
                return self.send_json(200, result)
            if len(parts) == 4 and parts[3] == "profile":
                return self.send_json(200, {"dataset_id": dataset_id, **profile_dataset(row)})
            if len(parts) == 4 and parts[3] == "schemas":
                with session(DB) as db:
                    versions = db.execute("""SELECT version,schema_json,recorded_at,ingestion_job_id
                        FROM dataset_schema_versions WHERE dataset_id=? ORDER BY version DESC""", (dataset_id,)).fetchall()
                return self.send_json(200, [{**dict(item), "schema": json.loads(item["schema_json"])} for item in versions])
            if len(parts) == 4 and parts[3] == "schema-changes":
                with session(DB) as db:
                    changes = db.execute("""SELECT id,from_version,to_version,column_name,change_type,previous_json,
                        current_json,severity,detected_at,acknowledged,ingestion_job_id FROM schema_changes
                        WHERE dataset_id=? ORDER BY to_version DESC,detected_at DESC""", (dataset_id,)).fetchall()
                return self.send_json(200, [{**dict(item), "previous": json.loads(item["previous_json"]) if item["previous_json"] else None,
                                             "current": json.loads(item["current_json"]) if item["current_json"] else None}
                                            for item in changes])
            if len(parts) == 4:
                return self.send_json(404, {"error": "Not found"})
            return self.send_json(200, {"id": row["id"], "name": row["name"], "source_name": row["source_name"],
                                        "created_at": row["created_at"], "row_count": row["row_count"],
                                        "layer": row["layer"], "schema": json.loads(row["schema_json"]),
                                        "description": row["description"], "tags": json.loads(row["tags_json"]),
                                        "schema_version": row["schema_version"], "updated_at": row["updated_at"],
                                        "storage_uri": row["storage_uri"], "storage_format": row["storage_format"],
                                        "storage_bytes": row["storage_bytes"], "content_sha256": row["content_sha256"],
                                        "sample": json.loads(row["records_json"])[:20]})

    def do_POST(self):
        path = urlparse(self.path).path
        if not self.same_origin():
            return self.send_json(403, {"error": "Cross-origin requests are not allowed."})
        if path in ("/api/auth/login", "/api/auth/register"):
            return self.auth_action(path)
        if not path.startswith("/api/"):
            return self.send_json(404, {"error": "Not found"})
        identity = self.require_user()
        if not identity:
            return
        if path == "/api/auth/logout":
            with session(DB) as db:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (identity["token_hash"],))
            return self.send_json(200, {"ok": True}, self.send_cookie("", clear=True))
        if path == "/api/workspaces":
            return self.create_workspace(identity)
        if path == "/api/workspaces/select":
            return self.select_workspace(identity)
        if path.startswith("/api/workspaces/") and path.endswith("/members"):
            return self.add_member(path, identity)
        if path.startswith("/api/schema-changes/") and path.endswith("/acknowledge"):
            return self.acknowledge_schema_change(path, identity)
        if path == "/api/ingest/csv":
            return self.ingest_csv(identity)
        if path == "/api/queries":
            return self.run_query(identity)
        if path == "/api/transformations":
            return self.save_transformation(identity)
        if path == "/api/quality/rules":
            return self.save_quality_rule(identity)
        if path.startswith("/api/quality/datasets/") and path.endswith("/run"):
            dataset_id = path.strip("/").split("/")[3]
            with session(DB) as db:
                try:
                    result = run_dataset_rules(db, identity["active_workspace_id"], dataset_id)
                except LookupError as exc:
                    return self.send_json(404, {"error": str(exc)})
            return self.send_json(201, result)
        if path.startswith("/api/alerts/") and path.endswith(("/read", "/acknowledge")):
            return self.update_alert(path, identity)
        if path.startswith("/api/transformations/") and path.endswith("/run"):
            return self.run_transformation(path, identity)
        return self.send_json(404, {"error": "Not found"})

    def run_query(self, identity):
        try:
            body = self.read_json()
        except OverflowError as exc:
            return self.send_json(413, {"error": str(exc)})
        except ValueError as exc:
            return self.send_json(400, {"error": str(exc)})
        sql = body.get("sql")
        query_id, created = uuid.uuid4().hex, now()
        columns, rows, count, duration, error = [], [], 0, 0, None
        try:
            with session(DB) as db:
                datasets = [dict(row) for row in db.execute("""SELECT id,name,row_count,schema_json,records_json,storage_bytes
                    FROM datasets WHERE workspace_id=? ORDER BY name COLLATE NOCASE""",
                    (identity["active_workspace_id"],)).fetchall()]
            result = execute_readonly(datasets, sql)
            columns, rows = result["columns"], result["rows"]
            count, duration = result["row_count"], result["duration_ms"]
            status = "succeeded"
        except ValueError as exc:
            error, status = str(exc), "failed"
        with session(DB) as db:
            db.execute("""INSERT INTO query_history(id,workspace_id,user_id,sql_text,status,columns_json,
                result_json,row_count,duration_ms,error_message,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (query_id, identity["active_workspace_id"], identity["user_id"],
                 sql if isinstance(sql, str) else "", status, json.dumps(columns), "[]",
                 count, duration, error, created))
        value = {"id": query_id, "sql_text": sql if isinstance(sql, str) else "", "status": status,
                 "columns": columns, "rows": rows, "row_count": count, "duration_ms": duration,
                 "error_message": error, "created_at": created}
        return self.send_json(200 if status == "succeeded" else 422, value)

    def save_quality_rule(self, identity, rule_id=None):
        try:
            body = self.read_json()
        except OverflowError as exc:
            return self.send_json(413, {"error": str(exc)})
        except ValueError as exc:
            return self.send_json(400, {"error": str(exc)})
        workspace_id = identity["active_workspace_id"]
        with session(DB) as db:
            current = db.execute("SELECT * FROM quality_rules WHERE id=? AND workspace_id=?",
                                 (rule_id, workspace_id)).fetchone() if rule_id else None
            if rule_id and not current:
                return self.send_json(404, {"error": "Quality rule not found."})
            dataset_id = body.get("dataset_id", current["dataset_id"] if current else None)
            dataset = db.execute("SELECT id,schema_json FROM datasets WHERE id=? AND workspace_id=?",
                                 (dataset_id, workspace_id)).fetchone()
            if not dataset:
                return self.send_json(404, {"error": "Target dataset not found in the active workspace."})
            all_datasets = db.execute("SELECT id,schema_json FROM datasets WHERE workspace_id=?", (workspace_id,)).fetchall()
            ids = {row["id"] for row in all_datasets}
            schemas = {row["id"]: json.loads(row["schema_json"]) for row in all_datasets}
            try:
                values = validate_rule(
                    body.get("name", current["name"] if current else None),
                    body.get("description", current["description"] if current else ""),
                    dataset_id,
                    body.get("target_column", current["target_column"] if current else None),
                    body.get("rule_type", current["rule_type"] if current else None),
                    body.get("config", json.loads(current["config_json"]) if current else {}),
                    body.get("severity", current["severity"] if current else "warning"),
                    schemas[dataset_id], ids, schemas)
            except ValueError as exc:
                return self.send_json(422, {"error": str(exc)})
            name, description, column, rule_type, config, severity = values
            enabled = body.get("enabled", bool(current["enabled"]) if current else True)
            if not isinstance(enabled, bool):
                return self.send_json(422, {"error": "Enabled must be true or false."})
            timestamp = now()
            if current:
                version = current["version"] + 1
                db.execute("""UPDATE quality_rules SET dataset_id=?,name=?,description=?,target_column=?,rule_type=?,
                    config_json=?,severity=?,enabled=?,version=?,updated_at=? WHERE id=? AND workspace_id=?""",
                    (dataset_id, name, description, column, rule_type, json.dumps(config), severity,
                     int(enabled), version, timestamp, rule_id, workspace_id))
            else:
                rule_id, version = uuid.uuid4().hex, 1
                db.execute("""INSERT INTO quality_rules
                    (id,workspace_id,dataset_id,name,description,target_column,rule_type,config_json,severity,enabled,
                     version,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (rule_id, workspace_id, dataset_id, name, description, column, rule_type,
                     json.dumps(config), severity, int(enabled), version, identity["user_id"], timestamp, timestamp))
            db.execute("""INSERT INTO quality_rule_versions
                (rule_id,version,name,description,target_column,rule_type,config_json,severity,enabled,created_by,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (rule_id, version, name, description, column, rule_type, json.dumps(config), severity,
                 int(enabled), identity["user_id"], timestamp))
        return self.send_json(200 if current else 201, {"id": rule_id, "dataset_id": dataset_id,
            "name": name, "description": description, "target_column": column, "rule_type": rule_type,
            "config": config, "severity": severity, "enabled": enabled, "version": version,
            "updated_at": timestamp})

    def update_alert(self, path, identity):
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[2] == "unread-count":
            return self.send_json(404, {"error": "Alert not found."})
        action, alert_id = parts[3], parts[2]
        if action not in ("read", "acknowledge"):
            return self.send_json(404, {"error": "Not found."})
        field = "read_at" if action == "read" else "acknowledged_at"
        with session(DB) as db:
            changed = db.execute(f"UPDATE alerts SET {field}=COALESCE({field},?) WHERE id=? AND workspace_id=?",
                                 (now(), alert_id, identity["active_workspace_id"])).rowcount
        if not changed:
            return self.send_json(404, {"error": "Alert not found."})
        return self.send_json(200, {"id": alert_id, action: True})

    def save_transformation(self, identity, transformation_id=None):
        try:
            body = self.read_json()
        except OverflowError as exc:
            return self.send_json(413, {"error": str(exc)})
        except ValueError as exc:
            return self.send_json(400, {"error": str(exc)})
        workspace_id = identity["active_workspace_id"]
        with session(DB) as db:
            current = None
            if transformation_id:
                current = db.execute("SELECT * FROM transformations WHERE id=? AND workspace_id=?",
                                     (transformation_id, workspace_id)).fetchone()
                if not current:
                    return self.send_json(404, {"error": "Transformation not found."})
            source_id = body.get("source_dataset_id")
            source = db.execute("SELECT schema_json FROM datasets WHERE id=? AND workspace_id=?",
                                (source_id, workspace_id)).fetchone()
            if not source:
                return self.send_json(404, {"error": "Source dataset not found in the active workspace."})
            output_layer = body.get("output_layer", "silver")
            try:
                name, description, steps = validate_definition(
                    body.get("name"), body.get("description", ""), source_id, output_layer,
                    body.get("steps"), json.loads(source["schema_json"]))
            except ValueError as exc:
                return self.send_json(422, {"error": str(exc)})
            config = {"source_dataset_id": source_id, "output_layer": output_layer, "steps": steps}
            config_json, timestamp = json.dumps(config), now()
            if current:
                revision = current["revision"] + 1
                db.execute("""UPDATE transformations SET name=?,description=?,config_json=?,revision=?,updated_at=?
                    WHERE id=? AND workspace_id=?""",
                    (name, description, config_json, revision, timestamp, transformation_id, workspace_id))
            else:
                transformation_id, revision = uuid.uuid4().hex, 1
                db.execute("""INSERT INTO transformations
                    (id,workspace_id,created_by,name,description,config_json,revision,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (transformation_id, workspace_id, identity["user_id"], name, description, config_json,
                     revision, timestamp, timestamp))
            db.execute("""INSERT INTO transformation_revisions
                (transformation_id,revision,config_json,created_by,created_at) VALUES(?,?,?,?,?)""",
                (transformation_id, revision, config_json, identity["user_id"], timestamp))
        return self.send_json(200 if current else 201, {"id": transformation_id, "name": name,
                                                        "description": description, "revision": revision,
                                                        "config": config})

    def run_transformation(self, path, identity):
        parts = path.strip("/").split("/")
        if len(parts) != 4:
            return self.send_json(404, {"error": "Not found"})
        transformation_id = parts[2]
        workspace_id, user_id = identity["active_workspace_id"], identity["user_id"]
        with session(DB) as db:
            transform = db.execute("SELECT * FROM transformations WHERE id=? AND workspace_id=?",
                                   (transformation_id, workspace_id)).fetchone()
            if not transform:
                return self.send_json(404, {"error": "Transformation not found."})
            config = json.loads(transform["config_json"])
            source = db.execute("SELECT * FROM datasets WHERE id=? AND workspace_id=?",
                                (config["source_dataset_id"], workspace_id)).fetchone()
            if not source:
                return self.send_json(404, {"error": "Source dataset not found in the active workspace."})
            source = dict(source)
        run_id, started = uuid.uuid4().hex, time.perf_counter()
        input_rows = source["row_count"]
        try:
            name, description, steps = validate_definition(
                transform["name"], transform["description"], config["source_dataset_id"],
                config["output_layer"], config["steps"], json.loads(source["schema_json"]))
            columns, schema, records = run_steps(json.loads(source["records_json"]),
                                                 json.loads(source["schema_json"]), steps)
            if not columns:
                raise ValueError("Transformation produced no output columns.")
        except (ValueError, TypeError, KeyError, ZeroDivisionError) as exc:
            elapsed = round((time.perf_counter() - started) * 1000)
            completed = now()
            with session(DB) as db:
                db.execute("""INSERT INTO transformation_runs
                    (id,workspace_id,transformation_id,revision,user_id,source_dataset_id,status,input_rows,
                     output_rows,duration_ms,error_message,created_at,completed_at)
                    VALUES(?,?,?,?,?,?,?,?,0,?,?,?,?)""",
                    (run_id, workspace_id, transformation_id, transform["revision"], user_id,
                     source["id"], "failed", input_rows, elapsed, str(exc)[:300], completed, completed))
                record_alert(db, workspace_id, f"transformation:{run_id}:failed", "transformation_run", run_id,
                             "critical", f"Transformation failed: {transform['name']}", str(exc)[:300],
                             "dataset", source["id"], completed)
            return self.send_json(422, {"id": run_id, "status": "failed", "error_message": str(exc)[:300]})

        completed = now()
        elapsed = round((time.perf_counter() - started) * 1000)
        output_id = uuid.uuid4().hex
        base = re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower() or "transform"
        output_name, suffix = f"{base}_output", 2
        with session(DB) as db:
            while db.execute("SELECT 1 FROM datasets WHERE name=?", (output_name,)).fetchone():
                output_name, suffix = f"{base}_output_{suffix}", suffix + 1
            db.execute("""INSERT INTO datasets
                (id,name,source_name,created_at,updated_at,row_count,columns_json,schema_json,records_json,
                 layer,workspace_id,description,tags_json,schema_version,storage_format)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (output_id, output_name, f"transformation:{name}", completed, completed, len(records),
                 json.dumps(columns), json.dumps(schema), json.dumps(records), config["output_layer"], workspace_id,
                 description or f"Output of {name}", json.dumps(["transformed"]), 1, "sqlite_json"))
            db.execute("""INSERT INTO dataset_schema_versions
                (dataset_id,version,schema_json,recorded_at) VALUES(?,?,?,?)""",
                (output_id, 1, json.dumps(schema), completed))
            details = {"transformation_id": transformation_id, "transformation_name": name,
                       "revision": transform["revision"], "run_id": run_id,
                       "source_dataset_id": source["id"], "output_dataset_id": output_id,
                       "input_rows": input_rows, "output_rows": len(records), "steps": len(steps)}
            lineage_id = uuid.uuid4().hex
            db.execute("INSERT INTO lineage VALUES(?,?,?,?,?)",
                       (lineage_id, output_id, "transformation_run", json.dumps(details), completed))
            db.execute("""INSERT INTO dataset_edges
                (id,workspace_id,source_dataset_id,target_dataset_id,lineage_id,created_at)
                VALUES(?,?,?,?,?,?)""",
                (uuid.uuid4().hex, workspace_id, source["id"], output_id, lineage_id, completed))
            db.execute("""INSERT INTO transformation_runs
                (id,workspace_id,transformation_id,revision,user_id,source_dataset_id,output_dataset_id,
                 status,input_rows,output_rows,duration_ms,created_at,completed_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, workspace_id, transformation_id, transform["revision"], user_id, source["id"],
                 output_id, "succeeded", input_rows, len(records), elapsed, completed, completed))
        quality_run = None
        try:
            with session(DB) as db:
                quality_run = run_dataset_rules(db, workspace_id, output_id)
                if quality_run["status"] == "skipped":
                    quality_run = run_dataset_rules(db, workspace_id, source["id"])
        except (ValueError, TypeError, KeyError):
            pass
        return self.send_json(201, {"id": run_id, "status": "succeeded", "transformation_id": transformation_id,
                                    "revision": transform["revision"], "dataset_id": output_id,
                                    "dataset_name": output_name, "input_rows": input_rows,
                                    "output_rows": len(records), "duration_ms": elapsed,
                                    "quality_run_id": quality_run.get("id") if quality_run else None})

    def do_PATCH(self):
        if not self.same_origin():
            return self.send_json(403, {"error": "Cross-origin requests are not allowed."})
        identity = self.require_user()
        if not identity:
            return
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 4 and parts[:3] == ["api", "quality", "rules"]:
            return self.save_quality_rule(identity, parts[3])
        if len(parts) == 3 and parts[:2] == ["api", "transformations"]:
            return self.save_transformation(identity, parts[2])
        if len(parts) != 4 or parts[:2] != ["api", "datasets"] or parts[3] != "metadata":
            return self.send_json(404, {"error": "Not found"})
        dataset_id = parts[2]
        try:
            body = self.read_json()
        except (ValueError, OverflowError) as exc:
            return self.send_json(400, {"error": str(exc)})
        with session(DB) as db:
            existing = db.execute("SELECT description,tags_json FROM datasets WHERE id=? AND workspace_id=?",
                                  (dataset_id, identity["active_workspace_id"])).fetchone()
            if not existing:
                return self.send_json(404, {"error": "Dataset not found."})
            try:
                description, tags = validate_metadata(body.get("description", existing["description"]),
                                                       body.get("tags", json.loads(existing["tags_json"])))
            except ValueError as exc:
                return self.send_json(422, {"error": str(exc)})
            db.execute("UPDATE datasets SET description=?,tags_json=?,updated_at=? WHERE id=?",
                       (description, json.dumps(tags), now(), dataset_id))
        return self.send_json(200, {"id": dataset_id, "description": description, "tags": tags})

    def acknowledge_schema_change(self, path: str, identity):
        change_id = path.strip("/").split("/")[2]
        with session(DB) as db:
            row = db.execute("""SELECT c.id FROM schema_changes c JOIN datasets d ON d.id=c.dataset_id
                WHERE c.id=? AND d.workspace_id=?""", (change_id, identity["active_workspace_id"])).fetchone()
            if not row:
                return self.send_json(404, {"error": "Schema change not found."})
            db.execute("UPDATE schema_changes SET acknowledged=1 WHERE id=?", (change_id,))
        return self.send_json(200, {"id": change_id, "acknowledged": True})

    def auth_action(self, path: str):
        try:
            body = self.read_json()
        except OverflowError as exc:
            return self.send_json(413, {"error": str(exc)})
        except ValueError as exc:
            return self.send_json(400, {"error": str(exc)})
        username, password = body.get("username"), body.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return self.send_json(400, {"error": "Username and password are required."})
        try:
            with session(DB) as db:
                if path.endswith("/register"):
                    user = create_account(db, username, password)
                else:
                    user = authenticate(db, username, password)
                    if not user:
                        return self.send_json(401, {"error": "Username or password is incorrect."})
                token, workspace_id, expires = create_session(db, user["id"])
                workspace = db.execute("SELECT name FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
            response = {"user": {"id": user["id"], "username": user["username"]},
                        "workspace": {"id": workspace_id, "name": workspace["name"]}, "expires_at": expires}
            return self.send_json(201 if path.endswith("/register") else 200, response, self.send_cookie(token))
        except ValueError as exc:
            return self.send_json(422, {"error": str(exc)})
        except Exception as exc:
            # Do not return database details or password hashes to the browser.
            if path.endswith("/register") and "UNIQUE constraint failed: users.username" in str(exc):
                return self.send_json(409, {"error": "That username is already registered."})
            print(f"Account request failed: {type(exc).__name__}")
            return self.send_json(500, {"error": "Could not complete the account request."})

    def create_workspace(self, identity):
        try:
            body = self.read_json()
        except (ValueError, OverflowError) as exc:
            return self.send_json(400, {"error": str(exc)})
        name = body.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            return self.send_json(422, {"error": "Workspace name must contain 1–80 characters."})
        workspace_id, created = uuid.uuid4().hex, now()
        with session(DB) as db:
            db.execute("INSERT INTO workspaces(id,name,created_at) VALUES(?,?,?)", (workspace_id, name.strip(), created))
            db.execute("INSERT INTO memberships(user_id,workspace_id,role,created_at) VALUES(?,?,?,?)",
                       (identity["user_id"], workspace_id, "owner", created))
            db.execute("UPDATE sessions SET active_workspace_id=? WHERE token_hash=?",
                       (workspace_id, identity["token_hash"]))
        return self.send_json(201, {"id": workspace_id, "name": name.strip(), "role": "owner"})

    def select_workspace(self, identity):
        try:
            body = self.read_json()
        except (ValueError, OverflowError) as exc:
            return self.send_json(400, {"error": str(exc)})
        workspace_id = body.get("workspace_id")
        if not isinstance(workspace_id, str):
            return self.send_json(422, {"error": "workspace_id is required."})
        with session(DB) as db:
            allowed = change_workspace(db, identity["token_hash"], identity["user_id"], workspace_id)
            workspace = db.execute("SELECT name FROM workspaces WHERE id=?", (workspace_id,)).fetchone() if allowed else None
        if not allowed:
            return self.send_json(403, {"error": "You are not a member of that workspace."})
        return self.send_json(200, {"id": workspace_id, "name": workspace["name"]})

    def add_member(self, path, identity):
        workspace_id = path.strip("/").split("/")[2]
        try:
            body = self.read_json()
        except (ValueError, OverflowError) as exc:
            return self.send_json(400, {"error": str(exc)})
        username = body.get("username")
        if not isinstance(username, str):
            return self.send_json(422, {"error": "username is required."})
        with session(DB) as db:
            owner = db.execute("SELECT role FROM memberships WHERE user_id=? AND workspace_id=?",
                               (identity["user_id"], workspace_id)).fetchone()
            user = db.execute("SELECT id,username FROM users WHERE username=? COLLATE NOCASE", (username.strip(),)).fetchone()
            if not owner or owner["role"] != "owner":
                return self.send_json(403, {"error": "Workspace owner role is required."})
            if not user:
                return self.send_json(404, {"error": "User not found."})
            db.execute("INSERT OR IGNORE INTO memberships(user_id,workspace_id,role,created_at) VALUES(?,?,?,?)",
                       (user["id"], workspace_id, "member", now()))
        return self.send_json(201, {"username": user["username"], "workspace_id": workspace_id, "role": "member"})

    def ingest_csv(self, identity):
        ctype = self.headers.get("Content-Type", "")
        if not ctype.lower().startswith("multipart/form-data;"):
            return self.send_json(400, {"error": "Upload a CSV using multipart form field 'file'."})
        try:
            raw = self.read_bytes(SETTINGS.max_upload_bytes + 65536)
        except OverflowError as exc:
            return self.send_json(413, {"error": str(exc)})
        except ValueError as exc:
            return self.send_json(400, {"error": str(exc)})
        boundary = ctype.split("boundary=", 1)[-1].strip().strip('"').encode()
        payload = filename = None
        for chunk in raw.split(b"--" + boundary):
            head, separator, body = chunk.partition(b"\r\n\r\n")
            if separator and b'name="file"' in head:
                match = re.search(rb'filename="([^"]+)"', head)
                filename = match.group(1).decode("utf-8", "replace") if match else "upload.csv"
                payload = body.removesuffix(b"\r\n")
                break
        if payload is None:
            return self.send_json(400, {"error": "Missing multipart file field."})
        filename = Path(filename).name
        idempotency_key = self.headers.get("Idempotency-Key", "")
        if len(idempotency_key) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", idempotency_key):
            return self.send_json(400, {"error": "Idempotency-Key must be 8–128 letters, numbers, dots, underscores, colons, or hyphens."})
        retry_of_job_id = self.headers.get("DataAtlas-Retry-Of") or None
        if retry_of_job_id:
            if not re.fullmatch(r"[a-fA-F0-9]{32}", retry_of_job_id):
                return self.send_json(400, {"error": "Retry-Of must identify an ingestion job."})
            with session(DB) as db:
                parent = db.execute("""SELECT source_name,upload_sha256,target_dataset_id,status,failure_type,
                    attempt_number FROM ingestion_jobs WHERE id=? AND workspace_id=?""",
                                    (retry_of_job_id, identity["active_workspace_id"])).fetchone()
                retry_count = db.execute("SELECT COUNT(*) FROM ingestion_jobs WHERE retry_of_job_id=?",
                                         (retry_of_job_id,)).fetchone()[0]
                replay = db.execute("""SELECT retry_of_job_id,source_name,upload_sha256,target_dataset_id
                    FROM ingestion_jobs WHERE workspace_id=? AND idempotency_key=?""",
                                    (identity["active_workspace_id"], idempotency_key)).fetchone()
            if not parent:
                return self.send_json(404, {"error": "Retry source job not found."})
            upload_hash = hashlib.sha256(payload).hexdigest()
            target_id = self.headers.get("DataAtlas-Replace-Dataset") or None
            if (parent["source_name"] != filename or parent["upload_sha256"] != upload_hash
                    or parent["target_dataset_id"] != target_id):
                return self.send_json(409, {"error": "Retry must use the original filename, file bytes, and replacement target."})
            retry_replay = bool(replay and replay["retry_of_job_id"] == retry_of_job_id
                                and replay["source_name"] == filename and replay["upload_sha256"] == upload_hash
                                and replay["target_dataset_id"] == target_id)
            if replay and not retry_replay:
                return self.send_json(409, {"error": "This idempotency key was already used for a different request."})
            if not retry_replay:
                if parent["status"] != "failed" or parent["failure_type"] != "transient":
                    return self.send_json(409, {"error": "Only transiently failed jobs can be retried."})
                if parent["attempt_number"] >= 3 or retry_count:
                    return self.send_json(409, {"error": "This job has already used its retry attempt limit."})
        try:
            result, status, replay = run_ingestion(DB, SETTINGS, identity["active_workspace_id"],
                                                   identity["user_id"], filename, payload, idempotency_key,
                                                   self.headers.get("DataAtlas-Replace-Dataset") or None,
                                                   retry_of_job_id)
        except IngestionFailure as exc:
            if exc.job_id:
                with session(DB) as db:
                    job = db.execute("SELECT failure_type FROM ingestion_jobs WHERE id=? AND workspace_id=?",
                                     (exc.job_id, identity["active_workspace_id"])).fetchone()
                    if job and job["failure_type"]:
                        record_alert(db, identity["active_workspace_id"], f"ingestion:{exc.job_id}:failed",
                                     "ingestion_job", exc.job_id,
                                     "critical" if job["failure_type"] == "transient" else "warning",
                                     "Ingestion failed", str(exc), "ingestion_job", exc.job_id)
            state = "failed" if exc.status == 422 else "conflict" if exc.status == 409 else "error"
            return self.send_json(exc.status, {"error": str(exc), "job_id": exc.job_id, "status": state})
        if replay:
            result["replayed"] = True
        return self.send_json(status, result)


def main():
    version = initialize(DB, SETTINGS.demo_password)
    recover_interrupted_jobs(DB)
    server = ThreadingHTTPServer((SETTINGS.host, SETTINGS.port), Handler)
    print(f"DataAtlas listening at http://{server.server_address[0]}:{server.server_address[1]} (database: {DB}; schema: {version})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

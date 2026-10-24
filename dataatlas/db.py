"""SQLite connection management and schema migrations."""
from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


MIGRATIONS = (
    (1, "initial_catalog", (
        """CREATE TABLE IF NOT EXISTS datasets(
            id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, source_name TEXT NOT NULL,
            created_at TEXT NOT NULL, row_count INTEGER NOT NULL, columns_json TEXT NOT NULL,
            schema_json TEXT NOT NULL, records_json TEXT NOT NULL, layer TEXT NOT NULL DEFAULT 'bronze'
        )""",
        """CREATE TABLE IF NOT EXISTS lineage(
            id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL
        )""",
    )),
    (2, "catalog_indexes", (
        "CREATE INDEX IF NOT EXISTS ix_datasets_created_at ON datasets(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_lineage_dataset_created ON lineage(dataset_id, created_at)",
    )),
    (3, "users_workspaces_and_sessions", (
        """CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS workspaces(
            id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS memberships(
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('owner','member')),
            created_at TEXT NOT NULL, PRIMARY KEY(user_id, workspace_id)
        )""",
        """CREATE TABLE IF NOT EXISTS sessions(
            token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            active_workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL, expires_at TEXT NOT NULL
        )""",
        "ALTER TABLE datasets ADD COLUMN workspace_id TEXT REFERENCES workspaces(id)",
        "CREATE INDEX IF NOT EXISTS ix_datasets_workspace_created ON datasets(workspace_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_memberships_workspace ON memberships(workspace_id, user_id)",
        "CREATE INDEX IF NOT EXISTS ix_sessions_expiry ON sessions(expires_at)",
    )),
    (4, "persistent_ingestion_jobs", (
        """CREATE TABLE IF NOT EXISTS ingestion_jobs(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            user_id TEXT NOT NULL REFERENCES users(id), dataset_id TEXT REFERENCES datasets(id),
            source_name TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed')),
            idempotency_key TEXT NOT NULL, upload_sha256 TEXT NOT NULL,
            records_read INTEGER NOT NULL DEFAULT 0, records_written INTEGER NOT NULL DEFAULT 0,
            rejected_records INTEGER NOT NULL DEFAULT 0, error_message TEXT,
            result_json TEXT, created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT,
            UNIQUE(workspace_id,idempotency_key)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_jobs_workspace_created ON ingestion_jobs(workspace_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_status ON ingestion_jobs(status, created_at)",
    )),
    (5, "bronze_storage_metadata", (
        "ALTER TABLE datasets ADD COLUMN storage_uri TEXT",
        "ALTER TABLE datasets ADD COLUMN storage_format TEXT",
        "ALTER TABLE datasets ADD COLUMN storage_bytes INTEGER",
        "ALTER TABLE datasets ADD COLUMN content_sha256 TEXT",
        "ALTER TABLE ingestion_jobs ADD COLUMN storage_uri TEXT",
    )),
    (6, "catalog_metadata_and_schema_registry", (
        "ALTER TABLE datasets ADD COLUMN description TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE datasets ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE datasets ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE datasets ADD COLUMN updated_at TEXT",
        "ALTER TABLE ingestion_jobs ADD COLUMN target_dataset_id TEXT",
        "ALTER TABLE ingestion_jobs ADD COLUMN schema_version INTEGER",
        "UPDATE datasets SET updated_at=created_at WHERE updated_at IS NULL",
        """CREATE TABLE IF NOT EXISTS dataset_schema_versions(
            dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            version INTEGER NOT NULL, schema_json TEXT NOT NULL, recorded_at TEXT NOT NULL,
            ingestion_job_id TEXT REFERENCES ingestion_jobs(id),
            PRIMARY KEY(dataset_id,version)
        )""",
        """CREATE TABLE IF NOT EXISTS schema_changes(
            id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            from_version INTEGER NOT NULL, to_version INTEGER NOT NULL, column_name TEXT NOT NULL,
            change_type TEXT NOT NULL, previous_json TEXT, current_json TEXT,
            severity TEXT NOT NULL CHECK(severity IN ('info','warning','breaking')),
            detected_at TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0,
            ingestion_job_id TEXT REFERENCES ingestion_jobs(id)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_schema_versions_dataset ON dataset_schema_versions(dataset_id,version)",
        "CREATE INDEX IF NOT EXISTS ix_schema_changes_dataset ON schema_changes(dataset_id,to_version)",
        "INSERT OR IGNORE INTO dataset_schema_versions(dataset_id,version,schema_json,recorded_at) SELECT id,1,schema_json,created_at FROM datasets",
    )),
    (7, "workspace_sql_query_history", (
        """CREATE TABLE IF NOT EXISTS query_history(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id), sql_text TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('succeeded','failed')),
            columns_json TEXT NOT NULL DEFAULT '[]', result_json TEXT NOT NULL DEFAULT '[]',
            row_count INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0,
            error_message TEXT, created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_query_history_workspace_created ON query_history(workspace_id,created_at)",
    )),
    (8, "transformations_and_runs", (
        """CREATE TABLE IF NOT EXISTS transformations(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            created_by TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            config_json TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_transformations_workspace_updated ON transformations(workspace_id,updated_at)",
        """CREATE TABLE IF NOT EXISTS transformation_revisions(
            transformation_id TEXT NOT NULL REFERENCES transformations(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL, config_json TEXT NOT NULL, created_by TEXT NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL, PRIMARY KEY(transformation_id,revision)
        )""",
        """CREATE TABLE IF NOT EXISTS transformation_runs(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            transformation_id TEXT NOT NULL REFERENCES transformations(id), revision INTEGER NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(id), source_dataset_id TEXT NOT NULL REFERENCES datasets(id),
            output_dataset_id TEXT REFERENCES datasets(id), status TEXT NOT NULL CHECK(status IN ('succeeded','failed')),
            input_rows INTEGER NOT NULL DEFAULT 0, output_rows INTEGER NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL DEFAULT 0, error_message TEXT,
            created_at TEXT NOT NULL, completed_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_transform_runs_workspace_created ON transformation_runs(workspace_id,created_at)",
    )),
    (9, "ingestion_job_events_and_retries", (
        "ALTER TABLE ingestion_jobs ADD COLUMN duration_ms INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE ingestion_jobs ADD COLUMN failure_type TEXT",
        "ALTER TABLE ingestion_jobs ADD COLUMN retry_of_job_id TEXT REFERENCES ingestion_jobs(id)",
        "ALTER TABLE ingestion_jobs ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 1",
        "CREATE INDEX IF NOT EXISTS ix_jobs_retry_parent ON ingestion_jobs(retry_of_job_id)",
        """CREATE TABLE IF NOT EXISTS ingestion_job_events(
            id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL, status TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_job_events_job_created ON ingestion_job_events(job_id,created_at)",
    )),
    (10, "persisted_dataset_lineage_edges", (
        """CREATE TABLE IF NOT EXISTS dataset_edges(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            source_dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            target_dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            lineage_id TEXT NOT NULL UNIQUE REFERENCES lineage(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL, CHECK(source_dataset_id<>target_dataset_id)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_dataset_edges_workspace_source ON dataset_edges(workspace_id,source_dataset_id)",
        "CREATE INDEX IF NOT EXISTS ix_dataset_edges_workspace_target ON dataset_edges(workspace_id,target_dataset_id)",
    )),
    (11, "quality_rules_runs_and_alerts", (
        "ALTER TABLE datasets ADD COLUMN quality_checked_at TEXT",
        """CREATE TABLE IF NOT EXISTS quality_rules(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', target_column TEXT,
            rule_type TEXT NOT NULL, config_json TEXT NOT NULL, severity TEXT NOT NULL
                CHECK(severity IN ('info','warning','critical')),
            enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)), version INTEGER NOT NULL DEFAULT 1,
            created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_quality_rules_workspace_dataset ON quality_rules(workspace_id,dataset_id,enabled)",
        """CREATE TABLE IF NOT EXISTS quality_rule_versions(
            rule_id TEXT NOT NULL REFERENCES quality_rules(id) ON DELETE CASCADE,
            version INTEGER NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', target_column TEXT,
            rule_type TEXT NOT NULL, config_json TEXT NOT NULL, severity TEXT NOT NULL,
            enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), created_by TEXT NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL, PRIMARY KEY(rule_id,version)
        )""",
        """CREATE TABLE IF NOT EXISTS quality_runs(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
            schema_version INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('succeeded','failed')),
            rules_total INTEGER NOT NULL, rules_passed INTEGER NOT NULL, rules_failed INTEGER NOT NULL,
            started_at TEXT NOT NULL, completed_at TEXT NOT NULL, duration_ms INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS ix_quality_runs_workspace_created ON quality_runs(workspace_id,completed_at)",
        """CREATE TABLE IF NOT EXISTS quality_results(
            id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES quality_runs(id) ON DELETE CASCADE,
            rule_id TEXT NOT NULL REFERENCES quality_rules(id) ON DELETE CASCADE, rule_version INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('passed','failed','error')),
            rows_evaluated INTEGER NOT NULL, violations INTEGER NOT NULL,
            samples_json TEXT NOT NULL DEFAULT '[]', error_message TEXT, created_at TEXT NOT NULL,
            UNIQUE(run_id,rule_id)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_quality_results_rule_created ON quality_results(rule_id,created_at)",
        """CREATE TABLE IF NOT EXISTS alerts(
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_key TEXT NOT NULL UNIQUE, source_type TEXT NOT NULL, source_id TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('info','warning','critical')),
            title TEXT NOT NULL, message TEXT NOT NULL, related_type TEXT, related_id TEXT,
            created_at TEXT NOT NULL, read_at TEXT, acknowledged_at TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS ix_alerts_workspace_created ON alerts(workspace_id,created_at)",
    )),
)
LATEST_SCHEMA_VERSION = MIGRATIONS[-1][0]


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    return db


@contextmanager
def session(path: Path):
    """Open a short-lived connection and always commit/rollback and close it."""
    db = connect(path)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(path: Path, demo_password: str = "dataatlas-demo") -> int:
    """Apply every pending migration once; return the current schema version."""
    with session(path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS schema_migrations(
            version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL
        )""")
        current = db.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
        for version, name, statements in MIGRATIONS:
            if version <= current:
                continue
            # The explicit transaction above makes the DDL and version record atomic.
            for statement in statements:
                db.execute(statement)
            db.execute(
                "INSERT INTO schema_migrations(version, name, applied_at) VALUES(?,?,?)",
                (version, name, datetime.now(timezone.utc).isoformat()),
            )
        # Recover graph edges from transformation lineage written before this migration.
        for event in db.execute("""SELECT l.id,l.dataset_id,l.details,l.created_at,d.workspace_id
            FROM lineage l JOIN datasets d ON d.id=l.dataset_id
            WHERE l.event_type='transformation_run'""").fetchall():
            try:
                source_id = json.loads(event["details"]).get("source_dataset_id")
            except (TypeError, json.JSONDecodeError):
                continue
            if source_id and source_id != event["dataset_id"]:
                db.execute("""INSERT OR IGNORE INTO dataset_edges
                    (id,workspace_id,source_dataset_id,target_dataset_id,lineage_id,created_at)
                    SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM datasets WHERE id=? AND workspace_id=?)""",
                    (uuid_hex(), event["workspace_id"], source_id, event["dataset_id"], event["id"],
                     event["created_at"], source_id, event["workspace_id"]))
        from .accounts import ensure_demo_account
        ensure_demo_account(db, demo_password)
        return db.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]


def uuid_hex():
    import uuid
    return uuid.uuid4().hex

import sqlite3
import json
import tempfile
import unittest
from pathlib import Path

from dataatlas.db import initialize, session


class MigrationTests(unittest.TestCase):
    def test_migrations_are_versioned_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.sqlite3"
            self.assertEqual(initialize(path), 11)
            self.assertEqual(initialize(path), 11)
            with session(path) as db:
                applied = db.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
                indexes = {row[1] for row in db.execute("PRAGMA index_list(datasets)")}
            self.assertEqual([row[0] for row in applied], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
            self.assertIn("ix_datasets_created_at", indexes)

    def test_migrates_existing_catalog_without_losing_data(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.sqlite3"
            db = sqlite3.connect(path)
            try:
                db.executescript("""
                    CREATE TABLE datasets(
                      id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, source_name TEXT NOT NULL,
                      created_at TEXT NOT NULL, row_count INTEGER NOT NULL, columns_json TEXT NOT NULL,
                      schema_json TEXT NOT NULL, records_json TEXT NOT NULL, layer TEXT NOT NULL DEFAULT 'bronze'
                    );
                    CREATE TABLE lineage(
                      id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
                      event_type TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL
                    );
                    INSERT INTO datasets VALUES('d1','orders','orders.csv','2026-01-01T00:00:00+00:00',1,'[]','[]','[]','bronze');
                """)
                db.commit()
            finally:
                db.close()
            self.assertEqual(initialize(path), 11)
            with session(path) as db:
                row = db.execute("SELECT name,row_count FROM datasets WHERE id='d1'").fetchone()
                self.assertEqual((row["name"], row["row_count"]), ("orders", 1))
                self.assertIsNotNone(db.execute("SELECT workspace_id FROM datasets WHERE id='d1'").fetchone()[0])

    def test_lineage_migration_backfills_transformation_edges(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lineage.sqlite3"
            initialize(path)
            with session(path) as db:
                owner = db.execute("SELECT id FROM users WHERE username='demo'").fetchone()["id"]
                workspace = db.execute("SELECT workspace_id FROM memberships WHERE user_id=?", (owner,)).fetchone()[0]
                for dataset_id, name in (("source-lineage", "source"), ("target-lineage", "target")):
                    db.execute("""INSERT INTO datasets
                        (id,name,source_name,created_at,updated_at,row_count,columns_json,schema_json,records_json,
                         layer,workspace_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (dataset_id, name, f"{name}.csv", "2026-01-01", "2026-01-01", 0, "[]", "[]", "[]",
                         "bronze", workspace))
                lineage_id = "lineage-backfill-event"
                db.execute("INSERT INTO lineage VALUES(?,?,?,?,?)",
                           (lineage_id, "target-lineage", "transformation_run",
                            json.dumps({"source_dataset_id": "source-lineage"}), "2026-01-02"))
            initialize(path)
            with session(path) as db:
                edge = db.execute("SELECT source_dataset_id,target_dataset_id FROM dataset_edges WHERE lineage_id=?",
                                  (lineage_id,)).fetchone()
                self.assertEqual((edge["source_dataset_id"], edge["target_dataset_id"]),
                                 ("source-lineage", "target-lineage"))


if __name__ == "__main__":
    unittest.main()

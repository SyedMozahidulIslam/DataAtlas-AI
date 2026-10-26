"""Bounded read-only SQL execution over a workspace's catalog datasets."""
from __future__ import annotations

import json
import re
import sqlite3
import time


MAX_SQL_LENGTH = 10_000
MAX_DATASETS = 50
MAX_LOADED_ROWS = 100_000
MAX_LOADED_BYTES = 25 * 1024 * 1024
MAX_RESULT_ROWS = 500
MAX_VM_STEPS = 500_000


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_name(dataset: dict) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", dataset["name"]).strip("_").lower() or "dataset"
    return f"{slug[:40]}_{dataset['id'][:8]}"


def table_catalog(datasets: list[dict]) -> list[dict]:
    return [{"dataset_id": d["id"], "dataset_name": d["name"], "table_name": table_name(d),
             "row_count": d["row_count"],
             "columns": [{"name": c["name"], "type": c["type"], "nullable": c["nullable"]}
                         for c in json.loads(d["schema_json"])]}
            for d in datasets]



def _require_select_statement(sql: str) -> None:
    without_leading_comments = re.sub(
        r"\A(?:(?:\s+)|--[^\r\n]*(?:\r?\n|$)|/\*.*?\*/)*", "", sql, flags=re.DOTALL)
    if not re.match(r"(?:SELECT|WITH)\b", without_leading_comments, flags=re.IGNORECASE):
        raise ValueError("Only read-only SELECT queries over listed workspace tables are allowed.")


def execute_readonly(datasets: list[dict], sql: str) -> dict:
    """Run one SELECT against in-memory tables; never opens the catalog DB for SQL."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("Enter a SQL query.")
    if len(sql) > MAX_SQL_LENGTH:
        raise ValueError(f"Query must be {MAX_SQL_LENGTH:,} characters or fewer.")
    _require_select_statement(sql)
    if len(datasets) > MAX_DATASETS:
        raise ValueError(f"The SQL workspace supports up to {MAX_DATASETS} datasets at a time.")
    if sum(int(d["row_count"]) for d in datasets) > MAX_LOADED_ROWS:
        raise ValueError(f"The SQL workspace is limited to {MAX_LOADED_ROWS:,} loaded rows per query.")
    if sum(len(d["records_json"].encode("utf-8")) for d in datasets) > MAX_LOADED_BYTES:
        raise ValueError("The SQL workspace is limited to 25 MB of loaded dataset records per query.")

    allowed_tables = {table_name(d) for d in datasets}
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    for limit_name, limit_value in (("SQLITE_LIMIT_LENGTH", 1_000_000),
                                    ("SQLITE_LIMIT_SQL_LENGTH", MAX_SQL_LENGTH),
                                    ("SQLITE_LIMIT_COLUMN", 200)):
        limit = getattr(sqlite3, limit_name, None)
        if limit is not None and hasattr(connection, "setlimit"):
            connection.setlimit(limit, limit_value)
    try:
        for dataset in datasets:
            schema = json.loads(dataset["schema_json"])
            columns = [c["name"] for c in schema]
            if not columns:
                continue
            affinities = {"integer": "INTEGER", "number": "REAL", "boolean": "INTEGER",
                          "string": "TEXT", "date": "TEXT", "timestamp": "TEXT"}
            definitions = ",".join(
                f"{quote_identifier(c['name'])} {affinities.get(str(c.get('type', '')).lower(), 'TEXT')}"
                for c in schema
            )
            name = table_name(dataset)
            connection.execute(f"CREATE TABLE {quote_identifier(name)} ({definitions})")
            rows = json.loads(dataset["records_json"])
            placeholders = ",".join("?" for _ in columns)
            connection.executemany(
                f"INSERT INTO {quote_identifier(name)} VALUES ({placeholders})",
                [[row.get(column) for column in columns] for row in rows],
            )

        def authorize(action, arg1, arg2, database, trigger):
            if action == sqlite3.SQLITE_SELECT or action == sqlite3.SQLITE_RECURSIVE:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ and arg1 in allowed_tables:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in {
                "count", "sum", "total", "avg", "min", "max", "group_concat", "string_agg",
                "lower", "upper", "length", "substr", "substring", "trim", "ltrim", "rtrim",
                "replace", "round", "abs", "coalesce", "ifnull", "nullif", "typeof", "quote",
                "hex", "unhex", "unicode", "char", "printf", "format", "date", "time", "datetime",
                "julianday", "unixepoch", "strftime", "json", "json_array", "json_object",
                "json_extract", "json_type", "json_valid", "json_array_length", "json_quote",
            }:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)
        steps = [0]

        def limit_work():
            steps[0] += 1
            return 1 if steps[0] * 1_000 > MAX_VM_STEPS else 0

        connection.set_progress_handler(limit_work, 1_000)
        started = time.perf_counter()
        cursor = connection.execute(sql)
        rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
        if len(rows) > MAX_RESULT_ROWS:
            raise ValueError(f"Query returned more than {MAX_RESULT_ROWS:,} rows; add a LIMIT clause.")
        elapsed = round((time.perf_counter() - started) * 1000)
        return {"columns": [item[0] for item in cursor.description or []],
                "rows": [dict(row) for row in rows], "row_count": len(rows), "duration_ms": elapsed}
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc).lower():
            raise ValueError("Query exceeded the local execution limit.") from exc
        message = str(exc)
        if "not authorized" in message.lower():
            message = "Only read-only SELECT queries over the listed workspace tables are allowed."
        raise ValueError(message[:300]) from exc
    except sqlite3.Error as exc:
        message = str(exc)
        if "not authorized" in message.lower():
            message = "Only read-only SELECT queries over the listed workspace tables are allowed."
        raise ValueError(message[:300]) from exc
    finally:
        connection.close()

def validate_readonly_candidate(datasets: list[dict], sql: str) -> dict:
    """Parse/authorize a candidate against empty workspace tables without executing it."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("The SQL candidate is empty.")
    if len(sql) > MAX_SQL_LENGTH:
        raise ValueError(f"Query must be {MAX_SQL_LENGTH:,} characters or fewer.")
    _require_select_statement(sql)
    if len(datasets) > MAX_DATASETS:
        raise ValueError(f"The SQL workspace supports up to {MAX_DATASETS} datasets at a time.")

    allowed_tables = {table_name(dataset) for dataset in datasets}
    connection = sqlite3.connect(":memory:")
    try:
        for limit_name, limit_value in (("SQLITE_LIMIT_LENGTH", 1_000_000),
                                        ("SQLITE_LIMIT_SQL_LENGTH", MAX_SQL_LENGTH),
                                        ("SQLITE_LIMIT_COLUMN", 200)):
            limit = getattr(sqlite3, limit_name, None)
            if limit is not None and hasattr(connection, "setlimit"):
                connection.setlimit(limit, limit_value)
        affinities = {"integer": "INTEGER", "number": "REAL", "boolean": "INTEGER",
                      "string": "TEXT", "date": "TEXT", "timestamp": "TEXT"}
        for dataset in datasets:
            schema = json.loads(dataset["schema_json"]) if isinstance(dataset["schema_json"], str) else dataset["schema_json"]
            if not schema:
                continue
            definitions = ",".join(
                f"{quote_identifier(column['name'])} {affinities.get(str(column.get('type', '')).lower(), 'TEXT')}"
                for column in schema
            )
            connection.execute(f"CREATE TABLE {quote_identifier(table_name(dataset))} ({definitions})")

        safe_functions = {
            "count", "sum", "total", "avg", "min", "max", "group_concat", "string_agg",
            "lower", "upper", "length", "substr", "substring", "trim", "ltrim", "rtrim",
            "replace", "round", "abs", "coalesce", "ifnull", "nullif", "typeof", "quote",
            "hex", "unhex", "unicode", "char", "printf", "format", "date", "time", "datetime",
            "julianday", "unixepoch", "strftime", "json", "json_array", "json_object",
            "json_extract", "json_type", "json_valid", "json_array_length", "json_quote",
        }

        def authorize(action, arg1, arg2, database, trigger):
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ and arg1 in allowed_tables:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in safe_functions:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)
        # EXPLAIN QUERY PLAN compiles and authorizes the statement but reads no rows.
        plan = connection.execute("EXPLAIN QUERY PLAN " + sql).fetchall()
        return {"valid": True, "plan": [row[3] for row in plan[:20]]}
    except sqlite3.OperationalError as exc:
        if "not authorized" in str(exc).lower():
            raise ValueError("Only read-only SELECT queries over listed workspace tables are allowed.") from None
        raise ValueError(str(exc)[:300]) from None
    except sqlite3.Error as exc:
        if "not authorized" in str(exc).lower():
            raise ValueError("Only read-only SELECT queries over listed workspace tables are allowed.") from None
        raise ValueError(str(exc)[:300]) from None
    finally:
        connection.close()

"""Validated, bounded data-quality rule definitions and evaluation."""
from __future__ import annotations

import json
import math
import re
import time
import uuid
from datetime import datetime, timezone


RULE_TYPES = {
    "not_null", "unique", "expected_type", "numeric_range", "regex",
    "allowed_values", "min_value", "max_value", "row_count", "referential_integrity",
}
SEVERITIES = {"info", "warning", "critical"}
EXPECTED_TYPES = {"string", "integer", "number", "boolean", "date", "timestamp"}
MAX_RULE_NAME = 100
MAX_SAMPLES = 20


def validate_rule(name: Any, description: Any, dataset_id: Any, target_column: Any,
                  rule_type: Any, config: Any, severity: Any, schema: list[dict],
                  dataset_ids: set[str] | None = None,
                  schemas_by_dataset: dict[str, list[dict]] | None = None) -> tuple:
    """Normalize a rule and validate its fields against a dataset schema."""
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > MAX_RULE_NAME:
        raise ValueError(f"Rule name must contain 1 to {MAX_RULE_NAME} characters.")
    if not isinstance(description, str) or len(description) > 500:
        raise ValueError("Rule description must be at most 500 characters.")
    if not isinstance(dataset_id, str) or not dataset_id:
        raise ValueError("A target dataset is required.")
    if not isinstance(rule_type, str) or rule_type not in RULE_TYPES:
        raise ValueError("Unsupported quality rule type.")
    if not isinstance(severity, str) or severity not in SEVERITIES:
        raise ValueError("Severity must be info, warning, or critical.")
    if not isinstance(config, dict) or len(json.dumps(config, ensure_ascii=False)) > 4096:
        raise ValueError("Rule configuration must be a JSON object of at most 4 KB.")

    column_required = rule_type not in ("row_count",)
    if rule_type == "referential_integrity":
        column_required = True
    names = {item.get("name") for item in schema if isinstance(item, dict)}
    column = target_column.strip() if isinstance(target_column, str) else ""
    if column_required and column not in names:
        raise ValueError("Choose a column from the target dataset schema.")
    if not column_required and column:
        raise ValueError("Row-count rules do not use a target column.")

    cfg = dict(config)
    if rule_type == "expected_type":
        _only_fields(cfg, {"expected_type"})
        if not isinstance(cfg.get("expected_type"), str) or cfg.get("expected_type") not in EXPECTED_TYPES:
            raise ValueError("Expected type must be one of: " + ", ".join(sorted(EXPECTED_TYPES)) + ".")
    elif rule_type == "numeric_range":
        _only_fields(cfg, {"min", "max"})
        _validate_bounds(cfg, require_one=True)
    elif rule_type in ("min_value", "max_value"):
        _only_fields(cfg, {"value"})
        value = cfg.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Threshold value must be a finite number.")
    elif rule_type == "regex":
        _only_fields(cfg, {"pattern"})
        pattern = cfg.get("pattern")
        if not isinstance(pattern, str) or len(pattern) > 128:
            raise ValueError("Pattern must be a string of at most 128 characters.")
        if re.search(r"\([^)]*[+*][^)]*\)[+*{]", pattern):
            raise ValueError("Nested repeating patterns are not supported.")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regular expression: {exc}") from exc
    elif rule_type == "allowed_values":
        _only_fields(cfg, {"values"})
        values = cfg.get("values")
        if not isinstance(values, list) or not values or len(values) > 100:
            raise ValueError("Allowed values must be a non-empty list of at most 100 values.")
        if any(not isinstance(value, (str, int, float, bool)) and value is not None for value in values):
            raise ValueError("Allowed values must be scalar values.")
    elif rule_type == "row_count":
        _only_fields(cfg, {"min", "max"})
        _validate_bounds(cfg, require_one=True)
        for key, value in cfg.items():
            if key in ("min", "max") and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError("Row-count limits must be non-negative whole numbers.")
        if "min" in cfg and "max" in cfg and cfg["min"] > cfg["max"]:
            raise ValueError("Minimum row count cannot exceed maximum row count.")
    elif rule_type == "referential_integrity":
        _only_fields(cfg, {"reference_dataset_id", "reference_column"})
        ref_dataset = cfg.get("reference_dataset_id")
        ref_column = cfg.get("reference_column")
        if not isinstance(ref_dataset, str) or not ref_dataset or ref_dataset == dataset_id:
            raise ValueError("Choose a different reference dataset.")
        if dataset_ids is not None and ref_dataset not in dataset_ids:
            raise ValueError("Reference dataset was not found in the active workspace.")
        ref_schema = (schemas_by_dataset or {}).get(ref_dataset, [])
        if not isinstance(ref_column, str) or ref_column not in {x.get("name") for x in ref_schema}:
            raise ValueError("Choose a column from the reference dataset schema.")
    elif rule_type in ("not_null", "unique"):
        _only_fields(cfg, set())
    return name.strip(), description.strip(), column or None, rule_type, cfg, severity


def _validate_bounds(config: dict, require_one: bool):
    if require_one and "min" not in config and "max" not in config:
        raise ValueError("Set at least one of the minimum or maximum thresholds.")
    for key in ("min", "max"):
        if key in config:
            value = config[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Thresholds must be finite numbers.")
    if "min" in config and "max" in config and config["min"] > config["max"]:
        raise ValueError("Minimum threshold cannot exceed maximum threshold.")


def _only_fields(config: dict, allowed: set[str]):
    if config.keys() - allowed:
        raise ValueError("Unsupported configuration field(s): " + ", ".join(sorted(config.keys() - allowed)) + ".")


def _typed(value, kind: str) -> bool:
    if value is None:
        return False
    text = str(value)
    if kind == "string":
        return True
    if kind == "integer":
        try:
            return str(int(text)) == text or (text.startswith("+") and str(int(text)) == text[1:])
        except ValueError:
            return False
    if kind == "number":
        try:
            return math.isfinite(float(text))
        except ValueError:
            return False
    if kind == "boolean":
        return text.strip().lower() in ("true", "false", "1", "0")
    if kind == "date":
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", text)) and _valid_iso(text, date_only=True)
    if kind == "timestamp":
        return _valid_iso(text.replace("Z", "+00:00"), date_only=False)
    return False


def _valid_iso(value: str, date_only: bool) -> bool:
    from datetime import date, datetime
    try:
        date.fromisoformat(value) if date_only else datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def evaluate_rule(rule: dict, records: list[dict], reference_records: list[dict] | None = None) -> dict:
    """Evaluate one persisted rule against actual records; keep bounded failure samples."""
    rule_type, config, column = rule["rule_type"], rule["config"], rule.get("target_column")
    if rule_type == "row_count":
        count = len(records)
        failed = (("min" in config and count < config["min"]) or
                  ("max" in config and count > config["max"]))
        violations = abs((config.get("min", count) if count < config.get("min", count)
                          else config.get("max", count) if count > config.get("max", count) else count) - count) if failed else 0
        return {"status": "failed" if failed else "passed", "rows_evaluated": count,
                "violations": violations, "samples": ([{"actual_rows": count, "thresholds": config}] if failed else [])}

    if rule_type == "referential_integrity":
        references = set()
        for record in reference_records or []:
            value = record.get(config["reference_column"])
            if value is not None:
                references.add(str(value))
        predicate = lambda value: value is None or str(value) in references
    elif rule_type == "not_null":
        predicate = lambda value: value is not None
    elif rule_type == "unique":
        seen = set()
        def predicate(value):
            if value is None:
                return True
            token = json.dumps(value, sort_keys=True, ensure_ascii=False)
            if token in seen:
                return False
            seen.add(token)
            return True
    elif rule_type == "expected_type":
        predicate = lambda value: value is None or _typed(value, config["expected_type"])
    elif rule_type == "numeric_range":
        def predicate(value):
            if value is None:
                return True
            try:
                number = float(value)
                return math.isfinite(number) and ("min" not in config or number >= config["min"]) and ("max" not in config or number <= config["max"])
            except (TypeError, ValueError):
                return False
    elif rule_type == "min_value":
        def predicate(value):
            if value is None:
                return True
            try:
                return math.isfinite(float(value)) and float(value) >= config["value"]
            except (TypeError, ValueError):
                return False
    elif rule_type == "max_value":
        def predicate(value):
            if value is None:
                return True
            try:
                return math.isfinite(float(value)) and float(value) <= config["value"]
            except (TypeError, ValueError):
                return False
    elif rule_type == "regex":
        compiled = re.compile(config["pattern"])
        predicate = lambda value: value is None or (len(str(value)) <= 4096 and compiled.fullmatch(str(value)) is not None)
    elif rule_type == "allowed_values":
        allowed = {json.dumps(value, sort_keys=True, ensure_ascii=False) for value in config["values"]}
        predicate = lambda value: value is None or json.dumps(value, sort_keys=True, ensure_ascii=False) in allowed
    else:
        raise ValueError("Unsupported rule type.")

    violations, samples = 0, []
    for index, record in enumerate(records):
        value = record.get(column)
        if not predicate(value):
            violations += 1
            if len(samples) < MAX_SAMPLES:
                samples.append({"row_number": index + 1, "value": value})
    return {"status": "failed" if violations else "passed", "rows_evaluated": len(records),
            "violations": violations, "samples": samples}


def run_dataset_rules(db, workspace_id: str, dataset_id: str) -> dict:
    """Evaluate enabled rules for one workspace dataset and persist immutable results."""
    dataset = db.execute("SELECT * FROM datasets WHERE id=? AND workspace_id=?", (dataset_id, workspace_id)).fetchone()
    if not dataset:
        raise LookupError("Dataset not found in the active workspace.")
    rules = db.execute("""SELECT * FROM quality_rules WHERE workspace_id=? AND dataset_id=? AND enabled=1
        ORDER BY created_at,id""", (workspace_id, dataset_id)).fetchall()
    if not rules:
        return {"dataset_id": dataset_id, "status": "skipped", "rules_total": 0,
                "rules_passed": 0, "rules_failed": 0, "results": []}
    run_id, started, timer = uuid.uuid4().hex, datetime.now(timezone.utc).isoformat(), time.perf_counter()
    records, schema = json.loads(dataset["records_json"]), json.loads(dataset["schema_json"])
    results, errors = [], []
    for item in rules:
        rule = {**dict(item), "config": json.loads(item["config_json"])}
        reference_records = None
        if rule["rule_type"] == "referential_integrity":
            ref_id = rule["config"]["reference_dataset_id"]
            reference = db.execute("SELECT records_json FROM datasets WHERE id=? AND workspace_id=?",
                                   (ref_id, workspace_id)).fetchone()
            if not reference:
                outcome = {"status": "error", "rows_evaluated": 0, "violations": 0,
                           "samples": [], "error_message": "Reference dataset is no longer available."}
            else:
                reference_records = json.loads(reference["records_json"])
                outcome = evaluate_rule(rule, records, reference_records)
        else:
            try:
                outcome = evaluate_rule(rule, records)
            except (ValueError, TypeError, re.error, KeyError) as exc:
                outcome = {"status": "error", "rows_evaluated": 0, "violations": 0,
                           "samples": [], "error_message": str(exc)[:300]}
        results.append((item, outcome))
        if outcome.get("status") != "passed":
            errors.append(outcome.get("error_message")) if outcome.get("status") == "error" else None

    completed = datetime.now(timezone.utc).isoformat()
    duration_ms = round((time.perf_counter() - timer) * 1000)
    passed = sum(1 for _, result in results if result["status"] == "passed")
    failed = sum(1 for _, result in results if result["status"] in ("failed", "error"))
    status = "failed" if failed else "succeeded"
    db.execute("""INSERT INTO quality_runs
        (id,workspace_id,dataset_id,schema_version,status,rules_total,rules_passed,rules_failed,
         started_at,completed_at,duration_ms,error_message) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, workspace_id, dataset_id, dataset["schema_version"], status, len(results), passed, failed,
         started, completed, duration_ms, "; ".join(errors)[:300] or None))
    for item, result in results:
        result_id = uuid.uuid4().hex
        db.execute("""INSERT INTO quality_results
            (id,run_id,rule_id,rule_version,status,rows_evaluated,violations,samples_json,error_message,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (result_id, run_id, item["id"], item["version"], result["status"], result["rows_evaluated"],
             result["violations"], json.dumps(result["samples"], ensure_ascii=False),
             result.get("error_message"), completed))
        if result["status"] == "failed":
            db.execute("""INSERT OR IGNORE INTO alerts
                (id,workspace_id,event_key,source_type,source_id,severity,title,message,related_type,related_id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (uuid.uuid4().hex, workspace_id, f"quality:{run_id}:{item['id']}", "quality_rule", item["id"],
                 item["severity"], f"Quality rule failed: {item['name']}",
                 f"{result['violations']:,} violation(s) in {dataset['name']}; "
                 f"{result['rows_evaluated']:,} row(s) evaluated.", "dataset", dataset_id, completed))
    db.execute("UPDATE datasets SET quality_checked_at=? WHERE id=? AND workspace_id=?",
               (completed, dataset_id, workspace_id))
    return {"id": run_id, "dataset_id": dataset_id, "dataset_name": dataset["name"],
            "schema_version": dataset["schema_version"], "status": status,
            "rules_total": len(results), "rules_passed": passed, "rules_failed": failed,
            "started_at": started, "completed_at": completed,
            "duration_ms": duration_ms,
            "results": [{"rule_id": item["id"], "rule_name": item["name"], "severity": item["severity"],
                         **result} for item, result in results]}


def record_alert(db, workspace_id: str, event_key: str, source_type: str, source_id: str,
                 severity: str, title: str, message: str, related_type: str | None,
                 related_id: str | None, created_at: str | None = None) -> None:
    db.execute("""INSERT OR IGNORE INTO alerts
        (id,workspace_id,event_key,source_type,source_id,severity,title,message,related_type,related_id,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (uuid.uuid4().hex, workspace_id, event_key, source_type, source_id, severity,
         title[:160], message[:500], related_type, related_id, created_at or datetime.now(timezone.utc).isoformat()))

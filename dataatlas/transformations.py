"""Validated linear transformations over parsed workspace datasets."""
from __future__ import annotations

import math
import json


MAX_STEPS = 25
MAX_OUTPUT_ROWS = 100_000
MAX_OUTPUT_BYTES = 25 * 1024 * 1024
MAX_COLUMNS = 200


def validate_definition(name, description, source_dataset_id, output_layer, steps, schema):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        raise ValueError("Transformation name must contain 1–80 characters.")
    if not isinstance(description, str) or len(description) > 500:
        raise ValueError("Description must be 500 characters or fewer.")
    if not isinstance(source_dataset_id, str) or not source_dataset_id:
        raise ValueError("Choose a source dataset.")
    if output_layer not in ("silver", "gold"):
        raise ValueError("Output layer must be silver or gold.")
    if not isinstance(steps, list) or len(steps) > MAX_STEPS:
        raise ValueError(f"Steps must be a list with at most {MAX_STEPS} operations.")
    available = {column["name"]: column for column in schema}
    if len(available) > MAX_COLUMNS:
        raise ValueError(f"Transformations support up to {MAX_COLUMNS} columns.")
    normalized = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Step {index} must be an object.")
        operation = step.get("type")
        if not isinstance(operation, str):
            raise ValueError(f"Step {index} needs a supported operation type.")
        if operation == "filter":
            column, operator = step.get("column"), step.get("operator")
            if not isinstance(column, str) or column not in available:
                raise ValueError(f"Step {index} references an unknown column.")
            if not isinstance(operator, str):
                raise ValueError(f"Step {index} has an unsupported filter operator.")
            if operator not in {"eq", "ne", "contains", "gt", "gte", "lt", "lte", "is_null", "not_null"}:
                raise ValueError(f"Step {index} has an unsupported filter operator.")
            if operator in {"gt", "gte", "lt", "lte"} and available[column]["type"] not in {"integer", "number"}:
                raise ValueError(f"Step {index} comparison requires a numeric column.")
            if operator == "contains" and available[column]["type"] != "string":
                raise ValueError(f"Step {index} contains filter requires a string column.")
            if operator not in {"is_null", "not_null"} and not isinstance(step.get("value"), (str, int, float)):
                raise ValueError(f"Step {index} requires a filter value.")
            filter_value = step.get("value")
            if operator in {"gt", "gte", "lt", "lte"} or (
                    available[column]["type"] in {"integer", "number"} and operator in {"eq", "ne"}):
                try:
                    filter_value = float(filter_value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Step {index} requires a numeric filter value.") from exc
                if not math.isfinite(filter_value):
                    raise ValueError(f"Step {index} filter value must be finite.")
            normalized.append({"type": "filter", "column": column, "operator": operator,
                               **({} if operator in {"is_null", "not_null"} else {"value": filter_value})})
        elif operation == "select":
            columns = step.get("columns")
            if (not isinstance(columns, list) or not columns or any(not isinstance(c, str) for c in columns)
                    or len(set(columns)) != len(columns)
                    or any(column not in available for column in columns)):
                raise ValueError(f"Step {index} must list unique columns currently in the pipeline.")
            normalized.append({"type": "select", "columns": columns})
            available = {column: available[column] for column in columns}
        elif operation == "derive":
            target, source, op = step.get("column"), step.get("source_column"), step.get("operation")
            if (not isinstance(target, str) or not target.strip() or target in available or len(target) > 100
                    or not isinstance(source, str)):
                raise ValueError(f"Step {index} needs a new, unique output column name.")
            if source not in available:
                raise ValueError(f"Step {index} references an unknown source column.")
            numeric_ops = {"add", "subtract", "multiply", "divide"}
            string_ops = {"upper", "lower", "concat"}
            if op in numeric_ops:
                if available[source]["type"] not in {"integer", "number"}:
                    raise ValueError(f"Step {index} numeric derivation requires a numeric source column.")
                try:
                    value = float(step.get("value"))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Step {index} numeric derivation requires a numeric value.") from exc
                if not math.isfinite(value):
                    raise ValueError(f"Step {index} value must be finite.")
                if op == "divide" and value == 0:
                    raise ValueError(f"Step {index} cannot divide by zero.")
                normalized_step = {"type": "derive", "column": target, "source_column": source,
                                   "operation": op, "value": value}
                result_type = "number"
            elif op in string_ops:
                if available[source]["type"] not in {"string", "boolean", "date", "timestamp"}:
                    raise ValueError(f"Step {index} string derivation requires a text-like source column.")
                if op == "concat" and not isinstance(step.get("value"), str):
                    raise ValueError(f"Step {index} concat requires a text value.")
                if op == "concat" and len(step["value"]) > 500:
                    raise ValueError(f"Step {index} concat value must be 500 characters or fewer.")
                normalized_step = {"type": "derive", "column": target, "source_column": source,
                                   "operation": op}
                if op == "concat":
                    normalized_step["value"] = step["value"]
                result_type = "string"
            else:
                raise ValueError(f"Step {index} has an unsupported derivation operation.")
            normalized.append(normalized_step)
            available[target] = {"name": target, "type": result_type, "nullable": True}
            if len(available) > MAX_COLUMNS:
                raise ValueError(f"Transformations support up to {MAX_COLUMNS} output columns.")
        else:
            raise ValueError(f"Step {index} has an unsupported operation type.")
    return name.strip(), description.strip(), normalized


def run_steps(records: list[dict], schema: list[dict], steps: list[dict]):
    current_schema = [dict(column) for column in schema]
    rows = [dict(row) for row in records]
    for step in steps:
        kind = step["type"]
        if kind == "filter":
            column, operator = step["column"], step["operator"]
            value = step.get("value")
            column_type = next(c["type"] for c in current_schema if c["name"] == column)
            if column_type in {"integer", "number"} and operator not in {"is_null", "not_null"}:
                value = float(value)
            def matches(row):
                actual = row.get(column)
                if operator == "is_null": return actual is None or actual == ""
                if operator == "not_null": return actual is not None and actual != ""
                if actual is None: return False
                comparable = float(actual) if column_type in {"integer", "number"} else str(actual)
                if operator == "eq": return comparable == value
                if operator == "ne": return comparable != value
                if operator == "contains": return str(value).casefold() in str(actual).casefold()
                if operator == "gt": return comparable > value
                if operator == "gte": return comparable >= value
                if operator == "lt": return comparable < value
                return comparable <= value
            rows = [row for row in rows if matches(row)]
        elif kind == "select":
            columns = step["columns"]
            rows = [{column: row.get(column) for column in columns} for row in rows]
            current_schema = [column for column in current_schema if column["name"] in columns]
            current_schema.sort(key=lambda column: columns.index(column["name"]))
        elif kind == "derive":
            source, target, operation = step["source_column"], step["column"], step["operation"]
            value = step.get("value")
            for row in rows:
                actual = row.get(source)
                if actual is None:
                    row[target] = None
                elif operation in {"add", "subtract", "multiply", "divide"}:
                    left, right = float(actual), float(value)
                    if operation == "add": row[target] = left + right
                    elif operation == "subtract": row[target] = left - right
                    elif operation == "multiply": row[target] = left * right
                    else:
                        if right == 0: raise ValueError("Cannot divide by zero in a derive step.")
                        row[target] = left / right
                    if not math.isfinite(row[target]):
                        raise ValueError("Numeric derivation produced a non-finite value.")
                elif operation == "upper": row[target] = str(actual).upper()
                elif operation == "lower": row[target] = str(actual).lower()
                else: row[target] = str(actual) + value
            current_schema.append({"name": target, "type": "number" if operation in {"add", "subtract", "multiply", "divide"} else "string",
                                   "nullable": True, "inferred": True})
    if len(rows) > MAX_OUTPUT_ROWS:
        raise ValueError(f"Transformation output exceeds {MAX_OUTPUT_ROWS:,} rows.")
    if len(json.dumps(rows, ensure_ascii=False).encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("Transformation output exceeds the 25 MB local limit.")
    return [column["name"] for column in current_schema], current_schema, rows

"""CSV validation and conservative schema inference."""
import csv
import io
import re
from datetime import date, datetime

from .config import Settings


def parse_csv(filename: str, raw: bytes, settings: Settings | None = None):
    settings = settings or Settings.from_env()
    if len(raw) > settings.max_upload_bytes:
        raise ValueError(f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB upload limit.")
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported in this checkpoint.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding.") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames or any(not h or not h.strip() for h in reader.fieldnames):
        raise ValueError("CSV needs a header row with non-empty column names.")
    headers = [h.strip() for h in reader.fieldnames]
    if len(set(headers)) != len(headers):
        raise ValueError("CSV column names must be unique.")
    rows = []
    for i, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f"Row {i} has more cells than the header.")
        rows.append({k.strip(): (v if v != "" else None) for k, v in row.items()})
        if len(rows) > settings.max_csv_rows:
            raise ValueError(f"CSV exceeds the {settings.max_csv_rows:,} row learning-scale limit.")
    if not rows:
        raise ValueError("CSV contains a header but no data rows.")
    schema = []
    for col in headers:
        values = [row[col] for row in rows if row[col] is not None]
        is_integer = values and all(re.fullmatch(r"[+-]?\d+", value) for value in values)
        is_number = values and all(re.fullmatch(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", value) for value in values)
        is_boolean = values and all(value.casefold() in ("true", "false") for value in values)
        is_timestamp = values and all(("T" in value or " " in value) and _is_timestamp(value) for value in values)
        is_date = values and all(_is_date(value) for value in values)
        kind = ("integer" if is_integer else "number" if is_number else "boolean" if is_boolean
                else "timestamp" if is_timestamp else "date" if is_date else "string")
        schema.append({"name": col, "type": kind, "nullable": len(values) < len(rows)})
    return headers, rows, schema


def _is_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _is_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False

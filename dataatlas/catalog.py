"""Catalog metadata validation and deterministic schema-change detection."""
from __future__ import annotations

import json
import re


def validate_metadata(description, tags):
    if description is None:
        description = ""
    if not isinstance(description, str) or len(description.strip()) > 500:
        raise ValueError("Description must be text with at most 500 characters.")
    if tags is None:
        tags = []
    if not isinstance(tags, list) or len(tags) > 20:
        raise ValueError("Tags must be a list of at most 20 labels.")
    normalized = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 40:
            raise ValueError("Each tag must contain 1–40 characters.")
        value = re.sub(r"\s+", " ", tag.strip())
        if value.casefold() not in {item.casefold() for item in normalized}:
            normalized.append(value)
    return description.strip(), normalized


def compare_schemas(previous: list[dict], current: list[dict]):
    """Return auditable changes; a removed+added name is not guessed to be a rename."""
    old = {column["name"]: column for column in previous}
    new = {column["name"]: column for column in current}
    changes = []
    for name in sorted(new.keys() - old.keys()):
        item = new[name]
        changes.append({"column_name": name, "change_type": "column_added", "previous": None,
                        "current": item, "severity": "info" if item.get("nullable", True) else "warning"})
    for name in sorted(old.keys() - new.keys()):
        changes.append({"column_name": name, "change_type": "column_removed", "previous": old[name],
                        "current": None, "severity": "breaking"})
    for name in sorted(old.keys() & new.keys()):
        before, after = old[name], new[name]
        if before.get("type") != after.get("type"):
            changes.append({"column_name": name, "change_type": "data_type_changed", "previous": before,
                            "current": after, "severity": "breaking"})
        if before.get("nullable") != after.get("nullable"):
            tighter = not after.get("nullable", True)
            changes.append({"column_name": name, "change_type": "nullability_changed", "previous": before,
                            "current": after, "severity": "breaking" if tighter else "info"})
    if set(old) == set(new) and [c["name"] for c in previous] != [c["name"] for c in current]:
        changes.append({"column_name": "*", "change_type": "column_order_changed",
                        "previous": [c["name"] for c in previous], "current": [c["name"] for c in current],
                        "severity": "info"})
    return changes


def schema_change_row(change):
    return (json.dumps(change["previous"]) if change["previous"] is not None else None,
            json.dumps(change["current"]) if change["current"] is not None else None)

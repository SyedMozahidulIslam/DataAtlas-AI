"""Metadata-grounded assistance with an optional OpenAI Responses provider.

Only workspace-authorized catalog metadata is sent to a configured provider. Parsed
records, raw files, credentials, and query results are never included in prompts.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone


MAX_QUESTION_LENGTH = 4000
MAX_CONTEXT_DATASETS = 6
MAX_CONTEXT_COLUMNS = 80
MAX_CONTEXT_ITEMS = 8
PROVIDER_TIMEOUT_SECONDS = 15


class AssistantProviderError(ValueError):
    pass


def provider_status(api_key: str | None, model: str | None) -> dict:
    configured = bool(api_key and model)
    return {
        "configured": configured,
        "provider": "openai" if configured else "local",
        "model": model if configured else None,
        "message": "OpenAI Responses enabled; metadata only is sent." if configured
                   else "Local metadata assistant active. Set OPENAI_API_KEY and DATAATLAS_AI_MODEL to enable OpenAI.",
    }


def call_openai(prompt: str, instructions: str, api_key: str, model: str) -> str:
    """Make one bounded, stateless Responses API call; never log request or key."""
    payload = json.dumps({
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": 700,
        "store": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=PROVIDER_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read(256 * 1024).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AssistantProviderError(f"AI provider returned HTTP {exc.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AssistantProviderError("AI provider could not be reached. Local answers remain available.") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AssistantProviderError("AI provider returned an unreadable response.") from None

    output = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                output.append(part["text"])
    answer = "\n".join(output).strip()
    if not answer:
        raise AssistantProviderError("AI provider returned no answer text.")
    return answer[:12_000]


def _terms(question: str) -> set[str]:
    ignored = {"about", "after", "before", "between", "could", "data", "dataset", "datasets",
               "does", "explain", "from", "have", "into", "latest", "most", "show", "that",
               "the", "their", "these", "this", "what", "which", "with", "would"}
    return {token for token in re.findall(r"[a-z0-9_]+", question.lower()) if len(token) > 2 and token not in ignored}


def retrieve_context(db, workspace_id: str, question: str, dataset_id: str | None = None) -> dict:
    """Retrieve bounded facts from one active workspace; never return raw record values."""
    if not isinstance(question, str) or not question.strip() or len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Question must contain 1 to {MAX_QUESTION_LENGTH:,} characters.")

    if dataset_id:
        rows = db.execute("""SELECT id,name,description,tags_json,source_name,updated_at,row_count,
            schema_json,records_json,layer,schema_version FROM datasets
            WHERE workspace_id=? AND id=?""", (workspace_id, dataset_id)).fetchall()
        if not rows:
            raise LookupError("Dataset not found in the active workspace.")
    else:
        rows = db.execute("""SELECT id,name,description,tags_json,source_name,updated_at,row_count,
            schema_json,records_json,layer,schema_version FROM datasets
            WHERE workspace_id=? ORDER BY updated_at DESC LIMIT 200""", (workspace_id,)).fetchall()

    terms = _terms(question)
    ranked = []
    for row in rows:
        schema = json.loads(row["schema_json"])
        metadata = " ".join([row["name"], row["description"], row["source_name"],
                             " ".join(json.loads(row["tags_json"])),
                             " ".join(column.get("name", "") for column in schema)]).lower()
        tokens = set(re.findall(r"[a-z0-9_]+", metadata))
        score = len(terms & tokens)
        if dataset_id and row["id"] == dataset_id:
            score += 1000
        ranked.append((score, row, schema))
    ranked.sort(key=lambda item: (-item[0], item[1]["name"].lower()))
    selected = [item for item in ranked if item[0] > 0][:MAX_CONTEXT_DATASETS]
    if dataset_id:
        selected = [item for item in ranked if item[1]["id"] == dataset_id]
    if not selected:
        selected = ranked[:min(3, len(ranked))]

    from .profiling import profile_dataset

    dataset_facts = []
    columns_total = 0
    for _, row, schema in selected:
        columns_total += len(schema)
        if columns_total > MAX_CONTEXT_COLUMNS:
            schema = schema[:max(0, MAX_CONTEXT_COLUMNS - (columns_total - len(schema)))]
        profile = profile_dataset(dict(row))
        columns = []
        for column in profile.get("columns", [])[:MAX_CONTEXT_COLUMNS]:
            fact = {key: column.get(key) for key in
                    ("name", "type", "nullable", "null_count", "distinct_count", "min", "max", "mean")}
            columns.append({key: value for key, value in fact.items() if value is not None})
        dataset_facts.append({
            "id": row["id"], "name": row["name"], "description": row["description"],
            "tags": json.loads(row["tags_json"]), "source_name": row["source_name"],
            "updated_at": row["updated_at"], "row_count": row["row_count"],
            "layer": row["layer"], "schema_version": row["schema_version"],
            "schema": schema, "profile": columns,
        })

    jobs = [dict(row) for row in db.execute("""SELECT id,source_name,status,dataset_id,records_read,
        records_written,error_message,completed_at,failure_type FROM ingestion_jobs
        WHERE workspace_id=? AND status='failed' ORDER BY completed_at DESC LIMIT ?""",
        (workspace_id, MAX_CONTEXT_ITEMS)).fetchall()]
    transformations = [dict(row) for row in db.execute("""SELECT r.id,r.transformation_id,r.source_dataset_id,
        r.output_dataset_id,r.status,r.input_rows,r.output_rows,r.error_message,r.completed_at,t.name
        FROM transformation_runs r JOIN transformations t ON t.id=r.transformation_id
        WHERE r.workspace_id=? ORDER BY r.completed_at DESC LIMIT ?""",
        (workspace_id, MAX_CONTEXT_ITEMS)).fetchall()]
    quality = [dict(row) for row in db.execute("""SELECT r.id,r.rule_id,r.status,r.violations,r.rows_evaluated,
        r.created_at,v.name,v.severity,v.rule_type,run.dataset_id,d.name AS dataset_name
        FROM quality_results r JOIN quality_runs run ON run.id=r.run_id
        JOIN quality_rule_versions v ON v.rule_id=r.rule_id AND v.version=r.rule_version
        JOIN datasets d ON d.id=run.dataset_id
        WHERE run.workspace_id=? AND r.status='failed' ORDER BY r.created_at DESC LIMIT ?""",
        (workspace_id, MAX_CONTEXT_ITEMS)).fetchall()]
    selected_ids = {item["id"] for item in dataset_facts}
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        edge_rows = db.execute(f"""SELECT e.source_dataset_id,e.target_dataset_id,e.created_at,
            s.name AS source_name,t.name AS target_name FROM dataset_edges e
            JOIN datasets s ON s.id=e.source_dataset_id JOIN datasets t ON t.id=e.target_dataset_id
            WHERE e.workspace_id=? AND (e.source_dataset_id IN ({placeholders})
                OR e.target_dataset_id IN ({placeholders}))
            ORDER BY e.created_at DESC LIMIT ?""",
            (workspace_id, *selected_ids, *selected_ids, MAX_CONTEXT_ITEMS)).fetchall()
    else:
        edge_rows = []
    edges = [dict(row) for row in edge_rows]
    return {"datasets": dataset_facts, "failed_ingestion_jobs": jobs,
            "recent_transformations": transformations, "failed_quality_rules": quality,
            "lineage_edges": edges}


def answer_locally(question: str, context: dict) -> str:
    """Answer common discovery questions using only retrieved facts."""
    lower = question.lower()
    datasets = context["datasets"]
    if not datasets:
        return "There are no datasets in this workspace yet. Ingest a CSV to build the catalog."

    if any(word in lower for word in ("missing", "null", "empty")):
        columns = [(dataset["name"], column) for dataset in datasets for column in dataset["profile"]]
        columns.sort(key=lambda pair: pair[1].get("null_count", 0), reverse=True)
        if not columns or not any(column.get("null_count", 0) for _, column in columns):
            names = ", ".join(dataset["name"] for dataset in datasets)
            return f"The retrieved profiles for {names} report no missing values in these columns."
        return "Columns with the most missing values in the retrieved datasets:\n" + "\n".join(
            f"- {name}.{column['name']}: {column.get('null_count', 0):,} nulls"
            for name, column in columns[:8])

    if "quality" in lower or "rule" in lower:
        failed = context["failed_quality_rules"]
        if not failed:
            return "No failed quality rule results were found in the retrieved workspace history."
        return "Recent quality failures:\n" + "\n".join(
            f"- {item['dataset_name']}: {item['name']} — {item['violations']:,} violation(s) "
            f"across {item['rows_evaluated']:,} row(s), severity {item['severity']}."
            for item in failed[:8])

    if any(word in lower for word in ("fail", "error", "pipeline", "job")):
        failures = []
        failures.extend(f"Ingestion {item['id'][:8]} ({item['source_name']}): {item['error_message'] or item['status']}."
                        for item in context["failed_ingestion_jobs"][:5])
        failures.extend(f"Transformation {item['name']} ({item['id'][:8]}): "
                        f"{item['error_message'] or item['status']}."
                        for item in context["recent_transformations"] if item["status"] == "failed")
        return "Recent processing failures:\n" + "\n".join(failures[:8]) if failures else \
            "No failed ingestion or transformation runs were found in the retrieved workspace history."

    if any(word in lower for word in ("lineage", "downstream", "upstream", "depend", "created by")):
        edges = context["lineage_edges"]
        if not edges:
            return "No persisted transformation lineage edges were found in the retrieved workspace metadata."
        return "Recent persisted transformation relationships:\n" + "\n".join(
            f"- {edge['source_name']} → {edge['target_name']} ({edge['created_at']})."
            for edge in edges[:8])

    if "customer" in lower:
        matches = [(dataset["name"], column["name"], column["type"])
                   for dataset in datasets for column in dataset["schema"]
                   if "customer" in column["name"].lower()]
        if not matches:
            return "No customer-named columns were found in the retrieved dataset schemas."
        return "Customer-related fields found:\n" + "\n".join(
            f"- {name}.{column} ({kind})" for name, column, kind in matches[:12])

    if "schema" in lower and len(datasets) == 1:
        dataset = datasets[0]
        return f"{dataset['name']} (schema v{dataset['schema_version']}):\n" + "\n".join(
            f"- {column['name']}: {column['type']}{' nullable' if column.get('nullable') else ' required'}"
            for column in dataset["schema"])

    return "Relevant catalog records:\n" + "\n".join(
        f"- {dataset['name']}: {dataset['row_count']:,} rows, {len(dataset['schema'])} columns, "
        f"{dataset['layer']} layer; updated {dataset['updated_at']}."
        for dataset in datasets[:6])


from .sql_workspace import quote_identifier


def local_sql_candidate(question, datasets, tables):
    """Generate only explicit row previews and counts; never guess analytical intent."""
    lower = question.lower()
    matches = []
    for dataset, table in zip(datasets, tables):
        aliases = [dataset["name"].lower(), table["table_name"].lower()]
        if any(alias and re.search(rf"(?<![a-z0-9_]){re.escape(alias)}(?![a-z0-9_])", lower)
               for alias in aliases):
            matches.append((max(map(len, aliases)), dataset, table))
    count_request = bool(re.search(
        r"\b(count|how many|number of rows|number of records|row count|record count)\b", lower))
    preview_request = bool(re.search(
        r"\b(preview|sample|first \d+|\d+ rows?|\d+ records?|show (?:me )?(?:some |the )?(?:rows?|records?|data)|list (?:some |the )?(?:rows?|records?))\b",
        lower))
    if not matches and len(datasets) == 1 and (count_request or preview_request):
        matches = [(0, datasets[0], tables[0])]
    if not matches:
        return None

    _, dataset, table = max(matches, key=lambda item: item[0])
    match = re.search(r"\b(\d{1,3})\b", lower)
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    limit = int(match.group(1)) if match else next(
        (value for word, value in words.items() if re.search(rf"\b{word}\b", lower)), 10)
    limit = min(max(limit, 1), 100)
    name = quote_identifier(table["table_name"])
    if count_request:
        sql = f"SELECT COUNT(*) AS row_count FROM {name}"
        explanation = f"Counts the stored rows in {dataset['name']}."
    elif preview_request:
        sql = f"SELECT * FROM {name} LIMIT {limit}"
        explanation = f"Previews up to {limit} row(s) from {dataset['name']}."
    else:
        return None
    return {"sql": sql, "explanation": explanation,
            "assumptions": ["The dataset name in the request identifies the source table.",
                            "The SQL workspace returns at most 500 rows."]}


def parse_json_object(text):
    if not isinstance(text, str):
        raise ValueError("AI response must be text.")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("AI response did not contain the expected JSON object.")
    value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("AI response must contain a JSON object.")
    return value

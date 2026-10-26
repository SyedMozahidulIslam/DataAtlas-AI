# DataAtlas

DataAtlas is a learning-scale data discovery and lakehouse workbench. The current local slice supports accounts, workspace-scoped catalog access, CSV ingestion, and lightweight profiling.

## Run locally

Requires Python 3.10 or later; the local application uses only the Python standard library. Versioned SQLite migrations run automatically when the server starts.

```powershell
python -m dataatlas.server
```

Open <http://127.0.0.1:8000>. Catalog, account, job, schema, and query-history metadata live in `var/dataatlas.sqlite3`; original CSV uploads live below `var/lake/bronze/<workspace-id>/<dataset-id>/<job-id>.csv`. Set `DATAATLAS_HOME`, `DATAATLAS_HOST`, and `DATAATLAS_PORT` to change local configuration (see `.env.example`; the application does not load `.env` files automatically). The first run creates a local `demo` account with password `dataatlas-demo`; set `DATAATLAS_DEMO_PASSWORD` before first launch to choose another password. Registration creates a separate private workspace. The demo dataset can be loaded from the UI or with `python -m dataatlas.seed` while the server is running.

Run `python -m unittest discover -s tests -v` or `./tasks.ps1 test` for checks. No database or frontend dependencies need installing for the local slice.

## Current checkpoint

Sign in or register, switch workspaces, add an existing account by username, and upload a CSV into the active workspace. Each upload creates a persistent ingestion job, stores an unmodified Bronze CSV with a SHA-256 checksum, and registers rows and schema metadata. The **Ingestion runs** tab shows status, attempt count, duration, and a persisted event timeline. Transient failures can be retried with the original file; the server verifies its filename, bytes, and replacement target, while validation failures cannot be retried. Retried requests remain idempotent. Catalog descriptions and tags are editable; search covers names, sources, descriptions, and tags. Replace an existing dataset from the upload dialog to preserve its ID, retain a raw-file version, and record schema history and change events. Profiling includes nulls, distinct values, category frequencies, numeric ranges/means/standard deviations/Tukey outliers, string lengths, booleans, and date ranges. Catalog, sample, profile, lineage, jobs, SQL tables, query history, transformations, and transformation runs are scoped to the active workspace. The **Lineage explorer** traverses persisted transformation edges upstream and downstream, with depth and size limits. The **SQL workspace** queries temporary in-memory SQLite copies of listed datasets. It accepts read-only SELECT queries and limits query length, loaded datasets/rows/data size, execution work, and results. History saves query text and execution metadata; query results are returned for the current run and are not stored in history. **Transformations** saves versioned linear recipes with validated filter, select, and derive steps. Runs create real Silver or Gold catalog datasets and lineage events; outputs are kept in the bounded local SQLite JSON catalog rather than raw Bronze files or Parquet. The AI discovery assistant answers questions from authorized catalog, profile, quality, job, and lineage metadata. It runs locally without credentials; optionally configure OPENAI_API_KEY and DATAATLAS_AI_MODEL for the stateless OpenAI Responses provider. Prompts contain metadata only, and proposed SQL is schema-validated without running it; review and execute a suggestion in the SQL workspace. Local suggestions are limited to explicit previews and row counts. A DAG editor, external-source graph nodes, aggregate/join operations, DuckDB, durable background workers, scheduling, and other file formats remain future phases.

Tests cover CSV validation, schema migrations, account authentication, workspace isolation, quality calculations, alert lifecycle, and automatic checks after replacement ingestion.

## Quality workspace

The **Quality** workspace manages workspace-scoped, versioned rules for nulls, uniqueness, expected types, numeric ranges and thresholds, regular expressions, allowed values, row counts, and referential integrity. Run checks manually or let successful ingestion and transformation runs trigger them. For transformation runs, output-specific rules run when configured; otherwise rules on the source dataset are evaluated after execution. Results retain the dataset schema and rule versions, evaluated-row and violation counts, bounded failed-row samples, and execution duration. No composite score is invented. In-app alerts cover quality failures, ingestion and transformation failures, and schema changes; they can be marked read and acknowledged. Custom SQL predicates, email delivery, dataset staleness detection, and downstream schema-impact analysis remain future work.

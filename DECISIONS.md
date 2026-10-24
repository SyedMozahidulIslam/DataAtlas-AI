# Architecture decisions

## 2026-10-24 — Start with a standard-library local slice

The workspace was empty and the available Python environment did not have FastAPI, SQLAlchemy, or DuckDB installed. The first checkpoint uses only standard-library HTTP, SQLite, and CSV modules to make the required upload → persistent dataset → profile/catalog workflow runnable without package installation or network access. This is a staging choice; it does not replace the planned modular API and analytical storage architecture. SQLite JSON record storage is bounded to the demo file/row limits and will need migration to columnar analytical storage as the roadmap proceeds.

## 2026-10-24 — Preserve uploaded values as text

CSV fields remain source strings (empty values become null); schema inference is explicit catalog metadata. This avoids silent coercion or loss at ingestion. Numeric profiles convert only values classified as numeric.

## 2026-10-24 — Loopback-only by default

The local app binds to `127.0.0.1` by default. Before the identity checkpoint it had no authentication; account and workspace boundaries were added in checkpoint 3. The local demo still should not be exposed to an untrusted network.

## 2026-10-24 — Version SQLite schema and close each session

Catalog schema changes are applied by an idempotent migration ledger at startup, so an existing first-checkpoint database upgrades without replacing data. A dedicated session context commits or rolls back and closes every connection. This also avoids holding SQLite file handles open across requests on Windows.

## 2026-10-24 — Defer Compose until Docker can verify it

The environment has no Docker executable. The project therefore keeps a runnable local SQLite path and does not claim a Compose/PostgreSQL environment was verified. Compose remains a planned deployment option once the required runtime is available.

## 2026-10-24 — Local account and workspace model

The local evaluator path uses PBKDF2-HMAC-SHA256 password hashes and opaque 12-hour session cookies. Only token hashes are stored. Each new account owns a private workspace; dataset reads and writes are scoped server-side to the active workspace. A pre-seeded `demo` account supports repeatable evaluation, with its password configurable before first database initialization. This is local-demo authentication; TLS, account recovery, rate limiting, and production identity integrations remain future work.

## 2026-10-24 — Persist original CSV in a local Bronze layer

The current evaluator has no Parquet or DuckDB runtime. Preserve uploaded CSV bytes as workspace-scoped Bronze files using an atomic local write and SHA-256 metadata, while retaining parsed rows in SQLite for the existing bounded profile screen. The storage class is replaceable; this does not represent a Parquet lakehouse or a distributed engine.

## 2026-10-24 — Make uploads observable and idempotent

Each accepted file submission creates a persistent job with explicit state, counts, timestamps, and failure detail. An idempotency key is unique within a workspace and bound to the upload checksum, preventing repeated HTTP submissions from creating duplicate datasets. Execution remains synchronous under the current local file/row limits; no queue or background worker is claimed.

## 2026-10-24 — Version schemas only when their inferred contract changes

New datasets get schema version 1. Replacement uploads create a new immutable snapshot only when detected columns, inferred types, nullability, or order change. A repeated upload with the same schema updates rows and the current raw-file pointer without creating a redundant schema version. Removed/added columns are reported independently rather than guessed as a rename. Numeric outliers use Tukey's 1.5×IQR fences; a generic quality score is not invented.

## 2026-10-24 — Keep prior Bronze uploads immutable on replacement

Each upload writes a new raw file keyed by its job ID beneath the stable dataset folder. SQLite updates the current pointer in the same transaction as records, schema history, lineage, and job completion. Thus a replacement that fails before commit does not overwrite the prior raw file. Orphan-file cleanup after a process crash remains a documented future task.

## 2026-10-24 — Run local SQL in a disposable, read-only workspace

DuckDB is not installed in the available runtime. Provide useful SQL exploration with Python's bundled SQLite by copying only active-workspace datasets into a fresh in-memory database for each query. An authorizer permits reads from generated workspace tables and an explicit safe function set, while denying writes, schema changes, attachment, and catalog access. Limits cap loaded data, query text, instruction work, and result rows. History stores SQL and execution metadata but not result rows. This is a local evaluator adapter, not a production query engine; keep the boundary explicit so DuckDB can replace it later.

## 2026-10-24 — Materialize bounded transformation recipes as catalog datasets

The local transformation fallback uses validated linear filter, select, and derive operations over parsed records instead of executable Python or arbitrary SQL. Each saved definition has immutable revisions, and each run creates a new Silver or Gold dataset plus a lineage event and persistent run record. Output records stay in SQLite JSON under explicit row/column/size limits; no Bronze object is fabricated for transformed data. DAGs, joins, aggregates, and durable workers are later extensions.

## 2026-10-24 — Retry only exact transient ingestion requests

Validation failures need a corrected upload and should not loop as retries. For storage/catalog or restart interruptions, allow a user-triggered retry only when the request uses the same file name, exact bytes, and replacement target. Persist each attempt and transition event, cap a retry chain at three attempts, and let the same idempotency key replay an already-created retry. This keeps retry behavior inspectable without retaining failed raw uploads.

## 2026-10-24 — Persist transformation lineage edges

Store successful dataset-to-dataset transformation relationships separately from event details so upstream/downstream traversal is indexed and workspace-scoped. Keep the event ID on each edge for traceability and backfill edges from prior transformation events during migration startup. CSV uploads remain external origins in event history until explicit source nodes are added; the graph does not invent file-system entities as datasets.

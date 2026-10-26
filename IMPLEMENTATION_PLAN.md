# Implementation plan

## Checkpoint 1 — Foundation and CSV vertical slice

- [x] Inspect project location and supplied brief; no supplied image files were attached.
- [x] Record scope, architecture, decisions, progress, and limitations.
- [x] Create local app shell and persistent storage foundation.
- [x] Upload CSV, register dataset/schema, persist records, and record ingestion lineage.
- [x] Browse catalog and inspect computed profile and sampled rows.
- [x] Add repeatable checks and fix defects found.

## Roadmap

1. Foundation and CSV ingestion slice (current checkpoint).
2. Repository tooling, environment configuration, migrations, and reproducible local setup (Compose deferred until Docker is available).
3. Identity, workspaces, permissions.
4. Source abstraction, persistent idempotent ingestion jobs, local Bronze storage; Parquet/DuckDB deferred.
5. Persistent catalog search, metadata, profiling and schema evolution (local complete).
6. Safe SQL workspace and query history using an available local engine (complete with temporary SQLite adapter; DuckDB deferred).
7. Transformation definitions and execution (complete for bounded local mode).
8. Job monitoring and bounded manual retry (complete for local ingestion mode; durable scheduling deferred).
9. Persisted lineage graph and schema evolution (graph traversal complete; schema evolution complete locally).
10. Quality rules, results and alerts (local implementation complete).
11. AI provider abstraction, metadata-grounded explanations, SQL validation and approval.
12. Exports, reporting, dashboard metrics, UI completion.
13. End-to-end verification, academic documentation, limitations and delivery.

Each phase should be split at a coherent checkpoint; update `PROGRESS.md` and `KNOWN_LIMITATIONS.md` as implementation changes.

## Checkpoint 2 — Local infrastructure foundation (complete with documented deployment deferral)

- [x] Add environment-backed settings and validate the configured port.
- [x] Separate CSV validation/schema inference from HTTP routing.
- [x] Add versioned, idempotent SQLite migrations and catalog indexes.
- [x] Close database connections reliably after each request.
- [x] Add project package metadata and repeatable PowerShell tasks.
- [x] Verify the migrated app through the HTTP server and update project state.
- [ ] Add Docker Compose when Docker is available to verify that local environment.

## Checkpoint 3 — Identity and workspace access (complete for local evaluator mode)

- [x] Add user, workspace, membership, and session schema with migration for existing catalog data.
- [x] Add password hashing, session issuance/expiry, registration, login, and logout.
- [x] Require authenticated sessions for data APIs and enforce active-workspace membership in dataset operations.
- [x] Add owner role, workspace creation/selection, and existing-user membership management.
- [x] Add browser sign-in/register and workspace controls; update demo seeding to authenticate.
- [x] Verify access denial, membership switching, persistence, and CSRF Origin checks.
- [ ] Add recovery, invitation UI, and additional authentication hardening in later product/security passes.

## Checkpoint 4 — Persistent ingestion jobs and Bronze storage (complete for local CSV mode)

- [x] Persist queued/running/succeeded/failed job states, counts, timestamps, error detail, and dataset link.
- [x] Add per-workspace idempotency keys bound to raw-upload SHA-256; reject reuse with different file bytes.
- [x] Store the original uploaded CSV atomically in a workspace-scoped local Bronze path.
- [x] Register file URI, format, size, checksum, schema, parsed records, and observed lineage.
- [x] Add workspace-scoped job list/detail API and ingestion-run UI.
- [x] Record CSV validation failures and mark interrupted jobs failed on application restart.
- [x] Test same-key replay, key/content conflict, stored-byte round trip, path traversal, failure observability, and authenticated seeding.
- [ ] Add asynchronous worker retries and Parquet/DuckDB adapters when scale/runtime support is ready.

## Checkpoint 5 — Catalog, profiling, and schema evolution (complete for local CSV mode)

- [x] Add descriptions, normalized tags, layer/source/search filters, and backend catalog query.
- [x] Add date, timestamp, boolean, integer, number, and string starting inference.
- [x] Add data-backed null, distinct, top-value, string length, boolean, date-range, and numeric/Tukey profile metrics.
- [x] Snapshot schemas and detect added/removed columns, type/nullability changes, and order changes.
- [x] Allow dataset replacement while retaining dataset ID and prior immutable Bronze/schema versions.
- [x] Persist severity and acknowledgement status for schema changes; do not guess ambiguous renames.
- [x] Add metadata editing, schema history/change detail, replacement workflow, and search UI.
- [ ] Add pagination, downstream impact analysis, richer categorical/date distributions, and a DuckDB catalog adapter later.

## Checkpoint 6 — Read-only SQL workspace and query history (complete for local CSV mode)

- [x] Expose active-workspace datasets as generated SQL table names with column metadata.
- [x] Query only temporary in-memory copies; never execute user SQL against the metadata database.
- [x] Restrict access to read-only SELECT operations and workspace tables with SQLite's authorizer.
- [x] Bound SQL length, loaded datasets/rows/raw bytes, SQLite row and column sizes, virtual-machine work, and result rows.
- [x] Persist successful and failed query text/status/timing/counts in workspace-scoped history; do not retain result rows.
- [x] Add SQL editor, table list, results grid, and recent-query reload controls.
- [x] Verify workspace isolation, successful reads, rejected mutations, result limits, and migration idempotence.
- [ ] Replace the local SQLite adapter with DuckDB when a suitable runtime is available; add transformation and query parameter workflows later.

## Checkpoint 7 — Versioned transformations and real output datasets (complete for local CSV mode)

- [x] Validate linear recipes with filter, select/project, and derive operations; reject unknown fields, types, and divide-by-zero values.
- [x] Persist recipe definitions and immutable revision snapshots in the active workspace.
- [x] Execute deterministic operations against the source's parsed records with row, step, column, and output-size limits.
- [x] Register each successful run as a new Silver or Gold dataset with a schema snapshot and transformation lineage event.
- [x] Persist successful and failed run metadata and provide workspace-scoped APIs and a recipe/run UI.
- [x] Verify recipe validation, real output values, revisions, lineage, and workspace access isolation.
- [ ] Add DAG editing, aggregate/join operations, durable workers/retries/scheduling, and Parquet/DuckDB materialization in later phases.

## Checkpoint 8 — Job event monitoring and transient retry (complete for local ingestion mode)

- [x] Persist queued, started, succeeded, validation-failed, execution-failed, and restart-recovery events.
- [x] Record elapsed ingestion duration and parsed/read versus written row counts.
- [x] Classify validation failures separately from retryable transient execution failures.
- [x] Allow one user-triggered retry per failed attempt, up to three total attempts, only for the same filename, exact file bytes, and replacement target.
- [x] Preserve idempotent replay for a retried request and enforce workspace authorization.
- [x] Add a run timeline and retry action to the ingestion UI.
- [x] Verify transient retry success, retry replay, validation retry rejection, workspace isolation, and restart recovery events.
- [ ] Add durable background workers, automatic backoff, scheduling, cancellation, and transformation retries later.

## Checkpoint 9 — Persisted lineage graph and traversal (complete for local transformation edges)

- [x] Persist source-to-output edges with their workspace, lineage event, and creation time.
- [x] Backfill edges from existing transformation lineage events during startup migration recovery.
- [x] Add bounded, workspace-scoped upstream/downstream/bidirectional traversal with depth and node/edge limits.
- [x] Add an interactive SVG graph with dataset focus, direction, depth, keyboard focus, and truncation status.
- [x] Verify graph edges from real transformation runs, both traversal directions, migration backfill, and access isolation.
- [ ] Add external-source nodes, more granular operation edges, and graph layout improvements later.

## Checkpoint 10 — Quality rules, results and alerts (complete for local records)

- [x] Persist workspace-scoped quality rules and immutable definition-version snapshots.
- [x] Validate and execute null, uniqueness, expected type, numeric range, regex, allowed-value, numeric threshold, row-count, and referential-integrity checks.
- [x] Persist each run with dataset schema version, rule version, row counts, violation counts, bounded samples, duration, and execution errors.
- [x] Run enabled checks after CSV ingestion/replacement and successful transformations (output rules when present, otherwise source rules); allow manual runs from the quality workspace.
- [x] Create in-app alerts for failed quality checks, failed ingestion/transformation runs, and detected schema changes; support read and acknowledgement state.
- [x] Add rule management, run detail, violation samples, recent alerts, and notification navigation to the UI.
- [x] Verify rule calculations, API persistence and versions, automatic checks after replacement, alert lifecycle, and schema migrations.
- [ ] Add custom SQL predicate rules under a dedicated validated expression grammar, staleness detection, email delivery, and downstream schema-impact analysis later.


## Checkpoint 11 — Metadata assistant and reviewed SQL suggestions (complete for bounded local mode)

- [x] Add a local metadata assistant for profile, quality, processing, lineage, schema, and catalog questions.
- [x] Add an optional stateless OpenAI Responses provider using environment-held credentials and model configuration.
- [x] Send bounded workspace-authorized metadata only; do not send records, raw files, or query results.
- [x] Suggest SQL from schemas, then validate it with SQLite EXPLAIN against empty schema-only tables.
- [x] Require the user to review and explicitly run a suggestion in the SQL workspace; suggestions never execute automatically.
- [x] Restrict local SQL generation to explicit row previews and counts and report unsupported requests clearly.
- [x] Verify SQL form restrictions, local answer grounding, provider-offline behavior, workspace authentication, and no query-history entry before execution.
- [ ] Add broader analytical intent handling only with explicit query review; add export and report workflows in checkpoint 12.

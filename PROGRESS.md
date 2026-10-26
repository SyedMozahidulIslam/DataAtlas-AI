# Progress

## Current checkpoint

Checkpoint 11 complete: metadata-grounded AI discovery with local fallback, optional OpenAI provider, and schema-validated SQL suggestions requiring explicit user review.

## Completed

- Read the full project brief and selected a dependency-free, local implementation for the first slice because framework dependencies are not installed in the available interpreter.
- Added project specification, architecture, roadmap, decisions, and limitations records.
- Implemented local browser workbench with catalog table, search, layer selector, upload dialog, dataset profile, sample rows, and observed ingestion lineage.
- Implemented bounded UTF-8 CSV ingestion and persistent SQLite catalog/data records.
- Added deterministic demo seed command.
- Added five standard-library unit tests for CSV schema inference, null handling, and invalid input.
- Verified API health, seed ingestion, catalog/profile/lineage reads, and persistence after restarting the server.
- Added environment settings, isolated CSV validation, SQLite schema migration tracking, catalog indexes, explicit connection close/rollback behavior, package metadata, and PowerShell task commands.
- Added migration tests for idempotence and upgrading a pre-migration catalog without data loss, plus environment configuration tests.
- Verified live health readiness reports schema version 2 and that a CSV upload/profile succeeds against a newly initialized database.
- Added migration 3 for users, workspaces, memberships, hashed browser sessions, and dataset workspace ownership. Existing datasets are migrated into the seeded demo workspace.
- Added PBKDF2 password hashing, opaque random session cookies with only token hashes persisted, session expiry, registration/login/logout, workspace creation/switching, and owner-managed membership by username.
- Enforced workspace membership and active-workspace filters on catalog, dataset, profile, lineage, and ingestion routes; mutations validate the Origin header.
- Added sign-in/register views, demo login, workspace selector/create controls, and sign-out to the browser app. Updated the demo seed command to authenticate.
- Added API integration checks for unauthenticated access, account creation/login, cross-workspace denial, authorized membership, and cross-origin rejection.
- Added migrations for persistent job records and Bronze file metadata.
- Added synchronous but persistent queued/running/succeeded/failed ingestion execution; invalid CSVs produce failed job records with useful errors.
- Added workspace-scoped idempotency keys bound to SHA-256, original CSV preservation with safe atomic local writes, catalog storage metadata, and job detail/list APIs.
- Added an Ingestion runs UI tab, linked failed/succeeded runs to their outcomes, and kept idempotency keys stable for in-page network retries.
- Added tests for same-key replay, different-content key conflicts, raw file round trip, path traversal rejection, failed job status, and authenticated demo seeding.
- Added searchable catalog descriptions/tags and server filters; added replacement ingestion preserving stable dataset IDs and immutable Bronze file versions.
- Added schema snapshots and persisted change events with severity/acknowledgement for column add/remove, type, nullability, and order changes.
- Added boolean/date/timestamp inference and richer computed profiles for numeric ranges, population standard deviation, Tukey outliers, string lengths, top values, booleans, and date ranges.
- Added metadata editing, schema history and change review, and existing-dataset replacement controls in the browser UI.
- Added migration 6 and tests for metadata normalization, schema compatibility classification, and data-backed profile formulas.
- Fixed idempotency replay validation to select and compare the source filename alongside checksum and replacement target.
- Added migration 7 and workspace-scoped SQL query history.
- Added generated query table names and a disposable SQLite in-memory adapter populated only from active-workspace datasets.
- Restricted user SQL to read-only SELECT statements over generated workspace tables, with a safe function allowlist and caps on query length, loaded datasets/rows/record bytes, SQLite values/columns, execution work, and result rows.
- Added SQL workspace UI with table/column discovery, query editor, results grid, and recent queries; history stores SQL and execution metadata, not result rows.
- Added API and unit coverage for query reads, mutation rejection, workspace isolation, history, and execution bounds.
- Added migration 8 for transformation definitions, immutable revisions, and persistent run records.
- Added a validated local transformation engine supporting filter, select/project, and numeric or string derive operations with output bounds.
- Added versioned recipe APIs and a transformation UI; successful runs persist new Silver or Gold datasets, schema snapshots, run metadata, and observed source lineage.
- Verified save/update/run APIs, derived output values, lineage, and workspace authorization boundaries.
- Added migration 9 with ingestion duration, retry lineage/attempt metadata, failure classification, and per-job lifecycle events.
- Recorded queued, started, completed, validation failure, execution failure, and restart recovery transitions with useful metadata.
- Added elapsed durations and parsed-row counts for failed as well as successful executions.
- Added an exact-request, user-triggered retry path for transient failures, capped at three chained attempts; validation errors are explicitly not retryable and retried requests remain idempotent.
- Added job event timelines, duration/attempt columns, and retry actions in the Ingestion runs UI.
- Verified transient failure and retry success, same-key replay, validation retry rejection, retry availability, workspace isolation, and restart recovery events.
- Added migration 10 with indexed workspace-scoped source-to-output lineage edges linked to their lineage event.
- Added startup backfill for transformation events created before edge persistence existed.
- Added bounded upstream, downstream, and bidirectional traversal with max depth, node, and edge limits.
- Added an interactive lineage explorer with dataset focus, direction/depth controls, graph node navigation, and truncation reporting.
- Verified lineage edges from successful transformation runs, traversal in both directions, migration backfill, and cross-workspace denial.
- Added migration 11 for dataset quality-check timestamps, workspace-scoped rules and immutable rule versions, run summaries/results, and in-app alerts.
- Added validated null, uniqueness, expected type, numeric range, regex, allowed-value, numeric threshold, row-count, and referential-integrity rules. Regexes and configurations are bounded; result samples cap at 20 rows.
- Added manual quality runs with schema/rule version snapshots, persisted pass/fail/error results, violation counts, safe samples, and rule-failure alerts.
- Automatically run enabled quality checks after successful CSV ingestion/replacement and transformation execution (using output rules when available, otherwise source rules); quality evaluator errors do not invalidate successful processing.
- Added quality rule editor, enable/disable, history/result inspection, alert read/acknowledge controls, and notification navigation. Ingestion, transformation, schema-change, and quality failures now create actionable in-app alerts.
- Verified rule validation/calculation, API workspace lifecycle, persisted results and version history, alert read/acknowledgement, and automatic checks after replacement ingestion.

## In progress / remaining

- Docker Compose and PostgreSQL service scaffolding are deferred: Docker is not installed in the current environment. The local SQLite setup is runnable and migrated automatically.
- Next phase: exports, reporting, dashboard metrics, and UI completion. The lineage graph currently represents transformation edges; external-source nodes and downstream schema-impact analysis remain future work. Durable asynchronous workers, automatic retry/backoff, scheduling, and transformation DAGs are also deferred.

- Added the metadata-grounded assistant with local answers and an optional stateless OpenAI Responses provider; only authorized metadata and aggregate profiles enter provider prompts.
- Added schema-only SQL suggestion validation via EXPLAIN; candidates are returned for review and do not create query-history records until a user runs them.
- Added the assistant discovery UI, provider status, local preview/count suggestions, and authenticated API tests.
- Verified bounded SQL validation, explicit local intent matching, assistant source grounding, local fallback, and authenticated suggestion flow.

## Files changed

`README.md`, `PROJECT_SPEC.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `DECISIONS.md`, `PROGRESS.md`, `KNOWN_LIMITATIONS.md`, `.env.example`, `pyproject.toml`, `tasks.ps1`, `dataatlas/{accounts.py,assistant.py,catalog.py,config.py,db.py,ingestion.py,jobs.py,lineage.py,profiling.py,quality.py,security.py,server.py,seed.py,sql_workspace.py,storage.py,transformations.py}`, `dataatlas/static/{index.html,styles.css,app.js}`, and tests including `test_auth_api.py`, `test_database.py`, `test_jobs.py`, `test_quality.py`, and `test_quality_api.py`.

## Commands and verification

- `python -B -m unittest discover -s tests -q` — 36 tests passed.
- Python AST parsing, `node --check dataatlas/static/app.js`, and `git diff --check` — passed.
- Ran `python -m dataatlas.server` and `python -m dataatlas.seed`; health endpoint reported `ok`, sample dataset held 5 rows/5 columns, profile and lineage endpoints returned computed/stored data.
- Restarted server against same `DATAATLAS_HOME`; sample dataset still present with 5 rows.
- Ran live HTTP verification against a fresh database on port 8013: migration readiness reported schema 2, CSV upload stored 2 rows, numeric profile mean was 15.0.
- Auth API tests exercise login, registration, cookie-backed current-user lookup, workspace switching, membership changes, dataset isolation, and Origin validation.
- Demo seed workflow tested through the authenticated HTTP API and produced the expected 5-row dataset.
- Job tests verified failed validation records, exact-byte Bronze persistence, identical-request replay, conflicting idempotency-key rejection, transient failure retries, lifecycle events, and restart recovery.
- Schema tests verified replacement history, persisted compatibility changes, review acknowledgement, metadata search, and richer column-profile calculations.
- SQL tests verified query result correctness, workspace isolation, SELECT-only enforcement, query-history persistence, migration 7, and execution/result limits.
- Transformation tests verified validation, filter/derive/project correctness, persisted revisions, materialized output values/layer, workspace isolation, and lineage; migration 8 was verified as idempotent.
- Job telemetry/retry API tests verified migration 9, event timeline ordering, transient retry matching, idempotent replay, and cross-workspace denial.
- Lineage tests verified migration 10/backfill and real transformation edge traversal upstream/downstream with workspace authorization.
- Quality tests verified migration 11, rule validation and calculations, immutable definition versions, real API run details and bounded samples, alert read/acknowledgement, workspace scoping, and automatic rules after replacement ingestion.

## Known blockers

Docker is unavailable, so Compose/PostgreSQL deployment remains unverified. The Next.js/FastAPI/PostgreSQL/Parquet/DuckDB target stack is not yet implemented; the current dependency-free local application remains usable. Ingestion is synchronous and orphan-file reconciliation after abrupt process exit remains unfinished. An ignored `var/lake` folder contains raw CSV fixtures from an earlier smoke-test attempt; automatic review rejected deleting the parent runtime folder because it could contain persistent catalog or lake data, so it was preserved.
- Assistant tests verified provider fallback, local grounding, explicit SQL intent, authenticated workspace access, candidate validation, and that a suggestion creates no query history before a user runs it.\n
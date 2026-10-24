# DataAtlas project specification

## Product scope

DataAtlas is a research-oriented, learning-scale data workbench for bringing datasets into a local lakehouse, understanding their metadata and quality, transforming them, querying them, monitoring operations, and tracing origins. It should be useful without paid cloud services or an LLM. Local storage and processing must be described honestly; no single-machine setup is represented as a distributed cluster.

## Core requirements

- Workspaces, identity, and server-side access control.
- File and read-only database sources; repeatable ingestion with observable jobs.
- Bronze, Silver, and Gold dataset layers, persistent catalog and schema history.
- Profiling, SQL execution, transformations, schedules, lineage, quality rules, alerts, and exports.
- Optional AI provider with authorized metadata retrieval and independent SQL validation.
- Responsive accessible interface, reproducible local setup, tests, and academic documentation.

## First checkpoint acceptance

- A local user can upload a UTF-8 CSV under 10 MB and 100,000 rows.
- The server validates headers and records, infers a transparent starting schema, and persists rows, schema, source metadata, and an observed ingestion lineage event.
- The catalog reflects stored datasets and row counts; dataset details show real sample rows and computed per-column null, distinct, and numeric summary statistics.
- State survives application restarts. Invalid files produce useful client errors.
- No claim is made that SQL, transformations, access control, or distributed storage exists in this checkpoint.

## Identity and workspace checkpoint acceptance

- Users can register and sign in with a locally stored password hash; browser sessions expire and can be revoked by logout.
- Each new account owns a workspace. Owners can create workspaces and add an existing account as a member.
- Dataset list, detail, profile, lineage, and ingestion endpoints enforce active-workspace membership server-side.
- An account that is not a workspace member cannot select the workspace or read its datasets.
- Same-site, HTTP-only session cookies are used and cross-origin mutations are rejected.

## Ingestion job and Bronze checkpoint acceptance

- Every accepted CSV submission has a persistent job id, state, timestamps, row counts, and a recorded dataset or failure.
- Retries with the same workspace-scoped idempotency key and same bytes return the first result; key reuse with different bytes is rejected.
- The original input CSV is stored in a workspace-scoped Bronze path with size and SHA-256 metadata.
- Job history and data file paths are visible only to workspace members.
- Local path traversal is rejected; the local Bronze write is atomic.
- This learning-scale checkpoint does not claim an asynchronous worker, Parquet conversion, or DuckDB query engine.

## Catalog and schema-history checkpoint acceptance

- Catalog records can be searched within the active workspace by name, source, description, or tags and filtered by layer.
- Workspace members can edit dataset description and normalized tags.
- Every dataset has an immutable schema snapshot; replacing a dataset preserves earlier schemas and raw Bronze versions.
- Added/removed columns, inferred type, nullability, and order changes are persisted with compatibility severity and can be acknowledged.
- Inference does not assert that a removed column and added column are a rename when evidence is ambiguous.
- Profiles compute data-backed null, distinct, top-value, numeric, text-length, boolean, and date metrics.

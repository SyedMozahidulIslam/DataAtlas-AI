<div align="center">

```
 ____        _          _   _   _
|  _ \  __ _| |_ __ _  / \ | |_| | __ _ ___
| | | |/ _` | __/ _` |/ _ \| __| |/ _` / __|
| |_| | (_| | || (_| / ___ \ |_| | (_| \__ \
|____/ \__,_|\__\__,_/_/   \_\__|_|\__,_|___/
```

# DataAtlas

### *Understand Your Data. Trace Every Transformation.*

**A learning-scale data lakehouse, catalog, ETL/ELT orchestrator, SQL workbench, data quality platform, lineage explorer, and AI-assisted discovery tool, in one coherent full-stack application.**

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)
![Parquet](https://img.shields.io/badge/Apache_Parquet-50ABF1?style=for-the-badge&logo=apache&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

![Status](https://img.shields.io/badge/status-senior_project-14b8a6?style=flat-square)
![Scale](https://img.shields.io/badge/scale-learning--scale_lakehouse-0f766e?style=flat-square)
![AI](https://img.shields.io/badge/AI-optional_%26_provider--agnostic-6366f1?style=flat-square)
![Cloud](https://img.shields.io/badge/cloud_account-not_required-success?style=flat-square)

[Features](#-feature-overview) · [Architecture](#-architecture) · [Modules](#-platform-modules) · [AI Layer](#-ai-assisted-discovery--safe-nl-to-sql) · [Quick Start](#-quick-start) · [Testing](#-testing--evaluation) · [Docs](#-documentation-map) · [Limitations](#-known-limitations)

</div>

---

## 📖 Table of Contents

1. [What is DataAtlas?](#-what-is-dataatlas)
2. [Product Principles](#-product-principles)
3. [Feature Overview](#-feature-overview)
4. [Architecture](#-architecture)
5. [Technology Stack](#-technology-stack)
6. [Lakehouse Design (Bronze / Silver / Gold)](#-lakehouse-design-bronze--silver--gold)
7. [Platform Modules](#-platform-modules)
8. [AI-Assisted Discovery & Safe NL-to-SQL](#-ai-assisted-discovery--safe-nl-to-sql)
9. [Security Model](#-security-model)
10. [Database & Metadata Model](#-database--metadata-model)
11. [REST API](#-rest-api)
12. [UI / UX & Design System](#-ui--ux--design-system)
13. [Project Structure](#-project-structure)
14. [Quick Start](#-quick-start)
15. [Configuration](#-configuration)
16. [Demo Data](#-demo-data)
17. [Testing & Evaluation](#-testing--evaluation)
18. [Performance & Reliability](#-performance--reliability)
19. [Documentation Map](#-documentation-map)
20. [Development Roadmap](#-development-roadmap)
21. [Known Limitations](#-known-limitations)
22. [Contributing](#-contributing)
23. [License & Acknowledgements](#-license--acknowledgements)

---

## 🧭 What is DataAtlas?

DataAtlas is a **research-oriented, learning-scale enterprise data platform** built as a university CSE senior project. It helps developers, analysts, data engineers, researchers, and small data teams:

> **bring data in → understand it → transform it → query it → monitor it → trace it.**

It is **not** a dashboard mockup, a CRUD demo, or a chatbot wrapper. Every screen is backed by persisted records, real ingestion, executable SQL, measurable quality results, and lineage derived from actual operations.

```text
 SOURCES            LAKEHOUSE                 ENGINEERING              INSIGHT
┌─────────┐   ┌───────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ CSV     │   │ 🥉 Bronze (raw)    │    │ Pipelines (DAG)  │    │ SQL Workbench      │
│ JSON    │──▶│ 🥈 Silver (clean)  │───▶│ Schedules/Jobs   │───▶│ Profiling          │
│ JSONL   │   │ 🥇 Gold (analytic) │    │ Quality Rules    │    │ Lineage Explorer   │
│ RDBMS   │   │ Parquet + DuckDB  │    │ Schema Registry  │    │ AI Assistant (opt.)│
│ S3      │   └───────────────────┘    └──────────────────┘    └────────────────────┘
└─────────┘            ▲                         │
                       └──── PostgreSQL metadata ┘
```

### Who is it for?

| Persona | What they use DataAtlas for |
|---|---|
| **Data engineer** | Build repeatable ingestion and transformation pipelines, monitor jobs, track schema drift |
| **Analyst** | Discover datasets, run SQL, export results, ask questions in natural language |
| **Researcher / student** | Study lakehouse, ETL, lineage, and quality patterns on a reproducible local stack |
| **Small data team** | Share a workspace-scoped catalog with quality and operational visibility |

---

## 🧱 Product Principles

| Principle | What it means in practice |
|---|---|
| **Data before dashboards** | Every chart and metric is computed from real stored data. No fake progress, no arbitrary scores |
| **Traceability** | Every managed dataset has an inspectable origin, and lineage is persisted from real runs |
| **Reproducibility** | Pipeline configs, revisions, runs, and quality results are all preserved |
| **Explicit schemas** | Inference is a starting point. Schema versions are tracked and never silently overwritten |
| **Safe execution** | SQL is parsed, resolved, authorized, limited, and run read-only, independent of any LLM |
| **Observable pipelines** | You can always tell what ran, when, what changed, and why it failed |
| **Honest AI** | AI output is a suggestion until validated, and it can never bypass permissions |
| **Practical scale** | Real data-engineering patterns, with no pretense of being a distributed cluster |
| **Modularity** | Connectors, storage, query engines, and AI providers are swappable adapters |
| **Accessible complexity** | Sophisticated capabilities behind a clear, approachable interface |

---

## ✨ Feature Overview

| # | Capability | Highlights |
|---|---|---|
| 🔐 | **Auth & Workspaces** | Registration, login, hashed passwords, owner/member roles, workspace-scoped everything |
| 🔌 | **Data Sources** | File upload, filesystem, read-only relational DB, S3-compatible storage, demo data generator |
| 📥 | **Batch Ingestion** | Chunked/streaming reads, full refresh / append / replace / incremental, idempotent retries |
| 🏞️ | **Lakehouse** | Bronze → Silver → Gold layers on Parquet + DuckDB, controlled storage abstraction |
| 📚 | **Data Catalog** | Search by dataset/column/tag/description, filters, ownership, tags, favorites, archival |
| 📊 | **Profiling** | Per-column stats, histograms, quantiles, outliers, sampling disclosure, rerunnable |
| 🧮 | **SQL Workspace** | Monaco editor, schema browser, validation, plan viewer, history, saved queries, exports |
| 🔧 | **Pipeline Builder** | Visual DAG editor, 12 node types, graph validation, node-level run status, revisions |
| ⏱️ | **Scheduling & Jobs** | Persistent schedules, durable workers, retries, concurrency policy, monitoring UI |
| 🕸️ | **Lineage Explorer** | Upstream/downstream traversal from persisted records, observed vs. inferred edges |
| 🧬 | **Schema Evolution** | Versioned schemas, change events, breaking/compatible assessment, downstream impact |
| ✅ | **Data Quality** | 10 rule types, severity, run history, violation samples, documented score formula |
| 🔔 | **Alerts** | In-app notifications for failures, quality, schema changes, staleness; optional email |
| 🤖 | **AI Assistant** | Grounded dataset Q&A, NL → SQL with independent validation, failure explanations |
| 📤 | **Exports & Reports** | CSV / JSON / JSONL / Parquet, profiling / quality / lineage / schema reports, Markdown/PDF |
| 📈 | **Dashboard** | Metrics derived from real execution and catalog records, with defined calculations |
| 🎨 | **Design System** | Light/dark themes, responsive layouts, accessible status semantics, reusable components |

> **Works without any AI key.** The catalog, ingestion, profiling, SQL, pipelines, lineage, and quality modules are fully functional with the AI layer disabled.

---

## 🏗 Architecture

DataAtlas is a **modular monolith** with a separate background worker. This is a deliberate choice over microservices, and the trade-offs are recorded in [`DECISIONS.md`](./DECISIONS.md).

```mermaid
flowchart LR
    subgraph Client["🖥 Browser"]
        UI["Next.js + React + Tailwind<br/>SQL Editor · React Flow · Charts"]
    end

    subgraph API["⚙️ FastAPI Backend (modular monolith)"]
        direction TB
        R["REST API /api/v1<br/>Auth · RBAC · Validation"]
        SVC["Services<br/>Catalog · Ingestion · Pipelines<br/>Quality · Lineage · Schema Registry"]
        QE["Query Engine Adapter<br/>SQL parse · validate · limits"]
        AI["AI Provider Abstraction<br/>+ Deterministic Fallback"]
        R --> SVC
        SVC --> QE
        SVC --> AI
    end

    subgraph Worker["🛠 Background Worker"]
        W["Job Runner<br/>Retries · Schedules · Recovery"]
    end

    subgraph Storage["💾 Storage"]
        PG[("PostgreSQL<br/>App Metadata")]
        PQ[("Parquet Files<br/>Bronze / Silver / Gold")]
        DK["DuckDB<br/>Analytical Engine"]
        S3[("S3-compatible<br/>optional")]
    end

    subgraph Ext["🌐 External (optional)"]
        SRC["Relational Sources<br/>read-only"]
        LLM["LLM Provider"]
    end

    UI <--> R
    SVC <--> PG
    SVC --> W
    W <--> PG
    W --> PQ
    QE --> DK
    DK --> PQ
    PQ -.adapter.-> S3
    SVC --> SRC
    AI -.optional.-> LLM
```

### Who owns what?

| Concern | PostgreSQL | DuckDB + Parquet |
|---|:---:|:---:|
| Users, workspaces, memberships, settings | ✅ | |
| Source registrations and credential references | ✅ | |
| Dataset catalog, schema versions, change events | ✅ | |
| Jobs, runs, retries, schedules, logs | ✅ | |
| Pipelines, revisions, node runs | ✅ | |
| Quality rules, results, violation summaries | ✅ | |
| Lineage entities and relationships | ✅ | |
| Query history, saved queries, alerts, audit events | ✅ | |
| **Actual analytical data (Bronze / Silver / Gold)** | | ✅ |
| **SQL analytics, profiling scans, transformations** | | ✅ |

> PostgreSQL is **not** used as a substitute for analytical processing, and DuckDB is **not** used for application state.

### End-to-end data flow

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Frontend
    participant API as FastAPI
    participant Q as Job Queue
    participant WK as Worker
    participant ST as Parquet Storage
    participant PG as PostgreSQL

    U->>FE: Upload orders.csv
    FE->>API: POST /sources/upload (validated)
    API->>PG: Register source + ingestion job (queued)
    API->>Q: Enqueue job
    Q->>WK: Deliver job
    WK->>ST: Stream chunks → Bronze Parquet
    WK->>PG: Record schema version, rows read/written
    WK->>PG: Create dataset + lineage (observed)
    WK->>PG: Run profile / quality (optional)
    WK->>PG: Mark job SUCCEEDED (atomic publish)
    FE->>API: Poll job status
    API-->>FE: Dataset ready → link to catalog entry
```

---

## 🧰 Technology Stack

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | Next.js · React · TypeScript | Type-safe, route-based, production-ready |
| **Styling** | Tailwind CSS · shadcn/ui | Accessible primitives, consistent design tokens |
| **Graph UI** | React Flow | Pipeline builder and lineage explorer |
| **SQL Editor** | Monaco Editor | Professional editing experience with SQL syntax |
| **Charts** | Recharts (or equivalent) | Histograms, trends, distributions |
| **Validation** | Zod | Schema-based form and API validation |
| **Backend** | Python · FastAPI · Pydantic | Async, typed, auto-generated OpenAPI |
| **ORM / Migrations** | SQLAlchemy · Alembic | Versioned, reviewable schema migrations |
| **Metadata DB** | PostgreSQL | Relational integrity for application state |
| **Analytical engine** | DuckDB | Fast embedded OLAP over Parquet |
| **Analytical storage** | Apache Parquet | Columnar, compressed, portable |
| **SQL parsing** | sqlglot (AST-based) | Proper parser, not regex, for validation |
| **Background jobs** | Durable worker (+ optional Redis) | Persisted job state, retries, recovery |
| **Scheduling** | Persistent scheduler (cron-style) | Survives restarts |
| **AI** | Provider abstraction | OpenAI-compatible / Anthropic / local, all optional |
| **Infra** | Docker · Docker Compose | One-command local environment |
| **Testing** | pytest · Vitest · React Testing Library · Playwright | Backend, frontend, integration, E2E |

---

## 🏞 Lakehouse Design (Bronze / Silver / Gold)

DataAtlas uses a **medallion-style layered organization**. Datasets are tagged with their layer and carry a full creation history. Not every workflow has to pass through all three layers.

```mermaid
flowchart LR
    A[("📄 External Source<br/>CSV / JSON / DB / S3")] --> B
    subgraph Bronze["🥉 BRONZE · Raw"]
        B["Source-faithful Parquet<br/>+ ingestion metadata"]
    end
    B -->|"Cleaning Pipeline"| C
    subgraph Silver["🥈 SILVER · Standardized"]
        C["Typed · deduped · validated<br/>normalized dates & categories"]
    end
    C -->|"Aggregation Pipeline"| D
    subgraph Gold["🥇 GOLD · Analytical"]
        D["Aggregates · dimensional-style<br/>business-ready datasets"]
    end
    D --> E["📊 SQL · Reports · Exports"]
```

| Layer | Purpose | Typical operations |
|---|---|---|
| 🥉 **Bronze** | Raw data preserved close to source form. Records source identity, ingestion time, and source schema | Ingestion, append, full refresh |
| 🥈 **Silver** | Cleaned and standardized | Type casting, renaming, null handling, dedup, date normalization, validation filters |
| 🥇 **Gold** | Business-ready analytics | Joins, group-by aggregates, dimensional tables, reusable metrics |

### Physical storage

- Every logical dataset has a **stable dataset ID** mapped to a **physical location, storage format, schema version, and access policy**.
- Paths are generated by a **controlled storage abstraction**. Clients never supply raw filesystem paths, which prevents path traversal.
- Outputs are written to a staging location and **atomically published** only after data writes and metadata updates succeed.
- Local filesystem is the default backend, and an **S3-compatible adapter** is provided for object storage.

> **Honesty note:** this is a *learning-scale* lakehouse. Local Parquet + DuckDB is not a distributed production cluster. The storage and query-engine adapters are designed so that Spark, Trino, or Delta/Iceberg-style engines could be added later. See [`docs/architecture/`](./docs/architecture/) for what would change in a genuinely distributed deployment.

---

## 🧩 Platform Modules

<details open>
<summary><b>🔐 A. Authentication, Workspaces & Access Control</b></summary>

<br/>

- Registration, login, logout, protected routes, user profile & preferences
- Passwords hashed with a modern adaptive algorithm. No plaintext storage, no secrets in code
- **Workspaces** isolate datasets, connections, pipelines, and query history
- **Roles:** `owner` and `member`

| Operation | Owner | Member |
|---|:---:|:---:|
| View datasets, run read queries | ✅ | ✅ |
| Create/edit datasets, pipelines, queries | ✅ | ✅ |
| Manage sources and credentials | ✅ | ❌ |
| Invite/remove members, delete workspace | ✅ | ❌ |
| Change workspace settings | ✅ | ❌ |

- **Every** private-resource request enforces ownership/membership **server-side**. Frontend checks are cosmetic only
- Documented demo account and seeding procedure (see [Quick Start](#-quick-start))

</details>

<details open>
<summary><b>🔌 B. Data Source Management</b></summary>

<br/>

| Source type | Status | Notes |
|---|:---:|---|
| File upload (CSV, JSON, JSONL/NDJSON) | ✅ Full | Drag-and-drop, multi-file, progress, preview |
| Parquet | ✅ Where supported | Validated by signature |
| Local / managed filesystem | ✅ Full | Restricted to configured roots |
| Relational database | ✅ Read-only | Connection test, schema inspection, no DDL/DML ever |
| S3-compatible object storage | ✅ Adapter | Local-compatible alternative for offline use |
| Generated demo data | ✅ Full | Clearly labelled synthetic |

**Upload safety:** extension check + **file-signature check** + size limit + **real content parsing**. Client-supplied MIME types are never trusted.

**Import settings:** delimiter, encoding, JSON structure detection, header handling, preview before ingestion, connection testing, and import history with retry/recovery.

**Secrets:** credentials are referenced via environment-based or encrypted stored references and are **never** returned to the browser, written to logs, or placed in LLM prompts.

</details>

<details open>
<summary><b>📥 C. Batch Ingestion Engine</b></summary>

<br/>

```mermaid
stateDiagram-v2
    [*] --> Queued
    Queued --> Running: worker picks up
    Running --> Succeeded: data + metadata published atomically
    Running --> Failed: error
    Failed --> Retrying: retry policy allows
    Retrying --> Running
    Failed --> [*]
    Running --> Cancelled: user cancels
    Succeeded --> [*]
    Cancelled --> [*]
```

**Workflow:** register source → validate → inspect schema → preview sample → choose target namespace/name → configure mode → submit job → track progress → persist data → register dataset → record lineage → optional profiling & quality.

| Mode | Behavior | Idempotency strategy |
|---|---|---|
| **Full refresh** | Rebuild dataset from the source | Staged write + atomic swap |
| **Append** | Add new records | Per-run batch ID and duplicate-prevention keys |
| **Replace** | Replace existing contents | Atomic replace after successful stage |
| **Incremental** | Only for connectors with a cursor/watermark | Watermark persisted per source and dataset |

Each job records: job ID, start/finish times, **records read / written / rejected**, error details, retry history, source & target references, and logs.

> Incremental ingestion is **only offered where the connector actually implements it**, with no pretend support.

Large files are **streamed in chunks** instead of being loaded fully into memory.

</details>

<details>
<summary><b>📚 E. Dataset Catalog & Metadata Management</b></summary>

<br/>

A searchable, persistent catalog populated from **real ingestion and transformation records**.

**Dataset metadata:** name, stable ID, description, workspace, source, layer, storage format, schema + version, column names/types, row count, size, timestamps, latest ingestion & processing run, quality status, owner, tags, glossary terms, upstream/downstream links, sensitivity classification.

**Capabilities:**
- Search across dataset names, **column names**, descriptions, and tags
- Filter by layer, source type, quality status, owner · sort · paginate
- Detail pages: **Overview · Schema · Preview · Profile · Quality · Lineage · History · Metadata**
- Edit descriptions (dataset *and* column level), tags, ownership
- Favorites, recent activity, archival/deletion

</details>

<details>
<summary><b>📊 F. Data Profiling & Exploration</b></summary>

<br/>

All statistics are computed from the stored dataset (or a **clearly disclosed sample**).

| Column kind | Computed statistics |
|---|---|
| **General** | Type, row count, non-null, nulls, null %, distinct count, duplicates, sample values |
| **Numeric** | Min, max, mean, median, std-dev, quantiles, histogram, **outliers (documented IQR method)** |
| **String** | Min/max length, empty-string count, top values, pattern summaries |
| **Date / Timestamp** | Min/max, missing, distribution over time, unparsable counts |
| **Boolean / Categorical** | Value counts, category frequencies, unexpected categories |

- Handles empty datasets, high-cardinality columns, and unsupported types
- **Sampling is disclosed** (size and method), and sampled results are never labelled as exact
- Profile history with timestamps and a **rerun** action
- The browser never receives full datasets, only aggregates and bounded previews

</details>

<details>
<summary><b>🧮 G. SQL Analytics Workspace</b></summary>

<br/>

A professional query environment powered by **DuckDB**, executed strictly server-side.

**UI:** Monaco editor · dataset & schema browser (click-to-insert) · format · validate · run · cancel · result grid · duration & row counts · query plan viewer · history · saved queries · CSV/JSON/Parquet download

**Execution safety stack:**

```mermaid
flowchart TD
    A["SQL text"] --> B["AuthN + workspace authorization"]
    B --> C["AST parse (sqlglot)"]
    C --> D{"Single read-only<br/>SELECT / WITH?"}
    D -- No --> X["❌ Reject (DDL, DML, PRAGMA,<br/>extensions, file/network access)"]
    D -- Yes --> E["Resolve tables & columns<br/>against authorized catalog"]
    E --> F{"All references<br/>authorized?"}
    F -- No --> X
    F -- Yes --> G["Apply row LIMIT + timeout<br/>+ memory limits"]
    G --> H["Run in read-only DuckDB connection<br/>filesystem & network disabled"]
    H --> I["Bounded result + metadata"]
    I --> J["Audit log + query history"]
```

- **Defense in depth:** application-level AST validation **plus** engine-level read-only/sandbox settings
- Identifiers are resolved against catalog metadata and safely quoted, with no string concatenation of untrusted input
- Query history stores text, user/workspace, timings, status, row count, and error summary. **Full result sets are not retained**

</details>

<details>
<summary><b>🔧 H. Transformation & Pipeline Builder (ETL/ELT)</b></summary>

<br/>

A visual DAG editor (React Flow) with an **accessible non-drag alternative** for adding and connecting nodes.

**Supported nodes:**

| Node | Description |
|---|---|
| `source` | Read from a registered dataset |
| `select` | Choose / reorder columns |
| `rename` | Rename columns |
| `filter` | Row filtering with validated predicates |
| `cast` | Type casting |
| `dedupe` | Remove duplicates (by key or full row) |
| `fill_null` | Null handling strategies |
| `derive` | Add derived columns (validated expressions) |
| `join` | Join compatible datasets |
| `aggregate` | Group + aggregate |
| `sort` | Ordering |
| `sink` | Write to a target dataset (layer + namespace) |

**Engine guarantees:**
- Pipelines are stored as **validated structured definitions** (stable node IDs, typed config, ports, positions)
- Graph validation detects **missing inputs, invalid edges, unsupported operations, and cycles**
- Nodes compile to **safe DuckDB operations**, with no fake runs
- **Revision history** for every saved version
- **Node-level run status**, timestamps, row counts, error messages, and logs
- Output datasets are registered **only after** writes and metadata updates succeed
- Execution automatically generates **lineage** and **schema versions**

</details>

<details>
<summary><b>⏱ I. Scheduling & Job Orchestration</b></summary>

<br/>

| Schedule type | Support |
|---|:---:|
| Manual | ✅ |
| One-time | ✅ |
| Recurring interval | ✅ |
| Daily | ✅ |
| Cron expression | ✅ |

- Schedules and run history are **persisted in PostgreSQL**, so nothing is lost on restart
- Prevents duplicate scheduling and **unintended concurrent runs** (documented concurrency policy)
- Defined **retry policy** with backoff and clear retry history
- Interrupted jobs are **recovered or reported** after a restart
- Job monitor shows queued / running / succeeded / failed / cancelled / retried jobs, with logs, durations, and links to related sources, pipelines, and datasets
- Long jobs never block the API, because heavy work runs in the **worker process**

</details>

<details>
<summary><b>🕸 J. Data Lineage Explorer</b></summary>

<br/>

Lineage is a **persisted graph**, created automatically during real operations. Layout is stored independently of the graph itself.

```mermaid
flowchart LR
    S["📄 orders.csv<br/>External File"] --> I["⚙ Ingestion Run #42"]
    I --> B["🥉 bronze.orders"]
    B --> P1["🔧 Cleaning Pipeline<br/>run #7"]
    P1 --> SV["🥈 silver.orders_clean"]
    SV --> P2["🔧 Revenue Aggregation<br/>run #3"]
    P2 --> G["🥇 gold.revenue_by_category"]
```

- Upstream / downstream traversal with depth control
- Click a node → details, timestamps, status, and **navigation to the actual resource**
- Highlights **failed or stale upstream dependencies** where determinable
- Distinguishes **observed** vs **inferred** vs **manually registered** relationships
- **Honest about gaps**: incomplete lineage is shown as incomplete, with no fabricated edges
- **Tabular dependency view** for large graphs and screen-reader users

</details>

<details>
<summary><b>🧬 K. Schema Evolution & Change Detection</b></summary>

<br/>

Every re-ingestion or pipeline output is compared against the previous registered schema version.

| Detected change | Default assessment |
|---|---|
| Column added (nullable) | 🟢 Compatible |
| Column added (non-nullable) | 🟡 Potentially breaking |
| Column removed | 🔴 Breaking |
| Data type changed | 🔴 / 🟡 Depends on widening vs. narrowing |
| Nullability changed | 🟡 Review |
| Column renamed | ⚠️ Flagged for review (never assumed certain) |
| Column order changed | 🟢 Informational |

- Schema history is **never silently overwritten**
- Compares each change against **downstream pipeline references** and warns about likely impact
- Side-by-side version diff, severity, detection time, related run, and an **acknowledgement workflow**
- Records whether a schema was **inferred** or **declared**

</details>

<details>
<summary><b>✅ L. Data Quality & Rule Management</b></summary>

<br/>

| Rule type | Example |
|---|---|
| Not null | `customer_id` must not contain nulls |
| Unique | `order_id` must be unique |
| Type match | `order_date` must be a valid `DATE` |
| Range | `0 ≤ unit_price ≤ 100000` |
| Pattern | `email` matches an expected regex |
| Allowed set | `status ∈ {pending, shipped, delivered, cancelled}` |
| Min / max threshold | `quantity ≥ 1` |
| Row count | Dataset must have ≥ N rows |
| Referential integrity | `orders.customer_id` exists in `customers.customer_id` |
| Custom predicate | Strictly validated SQL expression |

**Each execution persists:** run ID, dataset + **schema version**, **rule version**, timestamps, pass/fail, rows evaluated, violation count, safe violation samples, and error details.

**Quality score:** if shown, the **formula, weights, treatment of skipped rules, and interpretation are documented**, and the **underlying rule results are always visible**. No mystery percentages.

Rules can run **manually**, **after ingestion**, or **after a pipeline run**.

</details>

<details>
<summary><b>🔔 M. Alerts & Operational Observability</b></summary>

<br/>

**Alert triggers:** failed ingestion · failed pipeline · failed scheduled run · quality rule failure · schema change · stale dataset · repeated processing failure

**Features:** severity levels, related-resource deep links, read/unread, acknowledgement, in-app notification center. **Email is optional** and is only sent when a provider is configured, with a visible configuration status.

**Operational views:** recent runs, failure trends, job-duration trends, processing status, all derived from actual execution records.

</details>

<details>
<summary><b>📤 Q. Exports & Reports</b></summary>

<br/>

| Export | Formats |
|---|---|
| Query results | CSV · JSON · JSONL · Parquet |
| Profiling report | Markdown · PDF |
| Quality report | Markdown · PDF |
| Pipeline execution report | Markdown · JSON |
| Lineage summary | Markdown · JSON |
| Schema comparison report | Markdown · JSON |
| SQL & pipeline configuration | `.sql` · JSON |
| Metadata catalog | JSON · CSV |

All exports are **permission-checked**, **streamed or bounded** (never unbounded in memory), and contain **real generated content with metadata**.

</details>

<details>
<summary><b>📈 R. Dashboard & Analytics</b></summary>

<br/>

Every metric has a **defined calculation and data source**, and empty states are handled gracefully.

- Registered datasets · datasets by layer
- Ingestion & pipeline runs over time · success vs. failure
- Quality rule results · recent schema changes · recent alerts
- Storage usage (when measurable) · dataset freshness
- Most-queried datasets (from query history) · pipeline duration trends

</details>

---

## 🤖 AI-Assisted Discovery & Safe NL-to-SQL

The AI layer is an **optional enhancement**, never a dependency. It follows a strict rule: **LLM output is untrusted input.**

### Capabilities

| Feature | Description |
|---|---|
| 💬 **Dataset Q&A** | Answers grounded in retrieved catalog metadata, lineage, quality, and run records |
| 🧠 **NL → SQL** | Generates a SQL *candidate*, which is validated independently before it can run |
| 🔍 **Schema & dataset explanations** | Plain-language descriptions of schemas, schema diffs, and transformations |
| 🩺 **Failure analysis** | Sanitized-log-based diagnosis, with facts and hypotheses clearly separated |

Example questions it can answer:

- *"Which datasets contain customer-related fields?"*
- *"Which columns have the most missing values?"*
- *"Why did the latest pipeline run fail?"*
- *"Which downstream datasets depend on this table?"*
- *"Show the five product categories with the highest total revenue during the previous quarter."*

### NL-to-SQL pipeline

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant A as AI Service
    participant C as Catalog (authorized)
    participant L as LLM Provider
    participant V as Independent SQL Validator
    participant E as DuckDB (read-only)

    U->>A: "Top 5 categories by revenue last quarter"
    A->>C: Retrieve authorized schemas & column descriptions
    C-->>A: Relevant metadata only
    A->>L: Prompt (metadata as untrusted data, no secrets)
    L-->>A: SQL candidate + assumptions
    A->>V: Parse → allow-list → resolve refs → authz → limits
    alt invalid or unauthorized
        V-->>U: ❌ Rejected with reason
    else valid
        V-->>U: ✅ Show SQL + assumptions + plan (editable)
        U->>E: Explicit approval → run
        E-->>U: Real results + execution metadata
    end
```

### Reliability and safety guarantees

- ✅ The **validator is independent of the LLM**. Prompts alone are never the safety mechanism
- ✅ Generated SQL is **shown and explained first**, and runs only after explicit user approval (an auto-execute mode, if enabled, is visibly flagged and still fully validated)
- ✅ Hallucinated tables/columns are **rejected** by catalog resolution
- ✅ **Prompt-injection resistance:** dataset descriptions, column names, sample values, SQL comments, and logs are treated as *data*, never as instructions
- ✅ Secrets, env vars, connection strings, and other users' data are **never** sent to a model
- ✅ Only **schemas or small authorized samples** are shared, never entire datasets
- ✅ The LLM **cannot grant itself permissions or invoke arbitrary tools**
- ✅ Insufficient metadata → the assistant **says so** and suggests next steps
- ✅ **No provider configured?** A deterministic diagnostic view is shown and **clearly labelled as non-LLM**
- ✅ Failure explanations never auto-modify or auto-rerun pipelines

### Provider abstraction

```text
AIProvider (interface)
 ├── chat() / complete()
 ├── structured_output()
 ├── generate_sql()
 ├── explain_metadata()
 ├── diagnose_failure()
 └── embed()  (optional)

Implementations: OpenAI-compatible · Anthropic · Local/Ollama-style · Deterministic fallback
```

---

## 🛡 Security Model

| Area | Controls |
|---|---|
| **Authentication** | Secure password hashing, safe session/token handling, rate-limited sensitive endpoints |
| **Authorization** | Server-side checks on every private dataset, job, query, pipeline, and export |
| **Workspace isolation** | All queries and lookups are scoped by workspace and membership |
| **SQL safety** | AST parsing, statement allow-list, reference resolution, timeouts, row/memory limits, read-only engine, no filesystem or network access |
| **Upload safety** | Extension + signature + size + content validation. Path-traversal-safe storage |
| **Secrets** | Environment-based config, no secrets in code or logs, masked in UI |
| **Transport / browser** | CORS limited to known origins, CSRF protection where relevant |
| **Auditability** | Audit events for sensitive actions (logins, executions, exports, permission changes) |
| **Logging** | Structured logs with credential redaction. No full sensitive datasets in logs |
| **AI** | Disclosed external processing, redaction before prompts, untrusted-input handling |

> DataAtlas makes **no claims of regulatory compliance, certification, or hardened multi-tenant isolation** beyond what is implemented and tested. See [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md).

---

## 🗄 Database & Metadata Model

Normalized PostgreSQL schema managed by **Alembic migrations**, with primary/foreign keys, unique constraints, workspace boundaries, timestamps, soft-archival, and indexes for search and filtering.

```mermaid
erDiagram
    USER ||--o{ WORKSPACE_MEMBERSHIP : has
    WORKSPACE ||--o{ WORKSPACE_MEMBERSHIP : includes
    WORKSPACE ||--o{ DATA_SOURCE : owns
    WORKSPACE ||--o{ DATASET : owns
    WORKSPACE ||--o{ PIPELINE : owns
    DATA_SOURCE ||--o{ INGESTION_JOB : triggers
    INGESTION_JOB ||--o{ INGESTION_RUN : executes
    INGESTION_RUN }o--|| DATASET : produces
    DATASET ||--o{ DATASET_SCHEMA_VERSION : versions
    DATASET_SCHEMA_VERSION ||--o{ SCHEMA_CHANGE_EVENT : detects
    DATASET ||--o{ DATASET_STORAGE_OBJECT : stored_as
    DATASET ||--o{ DATASET_TAG : tagged
    DATASET ||--o{ DATA_QUALITY_RULE : validated_by
    DATA_QUALITY_RULE ||--o{ DATA_QUALITY_RUN : executed
    PIPELINE ||--o{ PIPELINE_REVISION : versioned
    PIPELINE ||--o{ SCHEDULED_JOB : scheduled
    PIPELINE_REVISION ||--o{ PIPELINE_RUN : executed
    PIPELINE_RUN ||--o{ PIPELINE_NODE_RUN : contains
    LINEAGE_ENTITY ||--o{ LINEAGE_RELATIONSHIP : upstream
    LINEAGE_ENTITY ||--o{ LINEAGE_RELATIONSHIP : downstream
    USER ||--o{ QUERY_HISTORY : runs
    USER ||--o{ SAVED_QUERY : saves
    USER ||--o{ NOTIFICATION : receives
    WORKSPACE ||--o{ AUDIT_EVENT : records
```

**Core entity groups**

| Group | Entities |
|---|---|
| Identity | `User`, `UserSettings`, `Workspace`, `WorkspaceMembership` |
| Sources & ingestion | `DataSource`, `DataSourceCredentialReference`, `IngestionJob`, `IngestionRun` |
| Catalog | `Dataset`, `DatasetColumn`, `DatasetStorageObject`, `DatasetTag`, `DatasetFavorite` |
| Schema registry | `DatasetSchemaVersion`, `SchemaChangeEvent` |
| Pipelines | `Pipeline`, `PipelineRevision`, `PipelineRun`, `PipelineNodeRun`, `ScheduledJob` |
| Quality | `DataQualityRule`, `DataQualityRuleVersion`, `DataQualityRun`, `DataQualityViolationSummary` |
| Lineage | `LineageEntity`, `LineageRelationship` |
| Operations | `QueryHistory`, `SavedQuery`, `Notification`, `AuditEvent`, `AIInteractionHistory` |

JSON columns are used **only** for genuinely flexible, validated configuration (e.g., node config, provider metadata). Run history is persisted **once** and referenced by dashboards, lineage, alerts, and failure analysis, so there are no duplicate sources of truth.

Full schema docs: [`docs/database/`](./docs/database/)

---

## 🌐 REST API

Versioned under **`/api/v1`**, with auto-generated **OpenAPI/Swagger** docs at `http://localhost:8000/docs`.

| Area | Representative endpoints |
|---|---|
| **Auth & account** | `POST /auth/register` · `POST /auth/login` · `POST /auth/logout` · `GET /me` |
| **Workspaces** | `GET/POST /workspaces` · `GET/PATCH/DELETE /workspaces/{id}` · membership routes |
| **Sources** | `GET/POST /sources` · `POST /sources/{id}/test` · `POST /sources/upload` · `GET /sources/{id}/preview` |
| **Ingestion** | `POST /ingestion/jobs` · `GET /ingestion/jobs/{id}` · `POST /ingestion/jobs/{id}/retry` |
| **Catalog** | `GET /datasets` (search/filter/sort/paginate) · `GET/PATCH/DELETE /datasets/{id}` |
| **Schema registry** | `GET /datasets/{id}/schema-versions` · `GET /schema-changes` · `POST /schema-changes/{id}/acknowledge` |
| **Profiling** | `POST /datasets/{id}/profile` · `GET /datasets/{id}/profile` |
| **SQL** | `POST /sql/validate` · `POST /sql/execute` · `POST /sql/explain` · `POST /sql/cancel/{id}` |
| **Queries** | `GET/POST /saved-queries` · `GET /query-history` |
| **Pipelines** | `GET/POST /pipelines` · `POST /pipelines/{id}/validate` · `POST /pipelines/{id}/run` · `GET /pipelines/{id}/revisions` |
| **Jobs & schedules** | `GET /jobs` · `GET /jobs/{id}/logs` · `GET/POST /schedules` |
| **Quality** | `GET/POST /quality/rules` · `POST /quality/rules/{id}/run` · `GET /quality/runs` |
| **Lineage** | `GET /lineage/{entity_id}?direction=up\|down\|both&depth=n` |
| **Alerts** | `GET /notifications` · `POST /notifications/{id}/read` · `POST /notifications/{id}/acknowledge` |
| **AI** | `POST /ai/ask` · `POST /ai/nl-to-sql` · `POST /ai/explain-failure/{run_id}` · `GET /ai/status` |
| **Exports** | `POST /exports` · `GET /exports/{id}/download` |
| **Dashboard** | `GET /dashboard/summary` · `GET /dashboard/trends` |
| **Ops** | `GET /health` · `GET /ready` |

**API conventions:** validated request/response schemas · correct status codes · consistent error envelope · pagination, filtering, sorting · upload limits · rate limiting on sensitive routes · bounded processing · safe logging.

---

## 🎨 UI / UX & Design System

DataAtlas is designed to feel like a **professional data engineering workbench**, not a generic admin template.

| Aspect | Decision |
|---|---|
| **Palette** | Deep navy / charcoal · teal-aqua primary accent · soft neutral light surfaces · dark slate dark mode |
| **Themes** | Light (default) and Dark, both fully supported |
| **Typography** | Inter for UI · monospaced font for SQL, schemas, identifiers, logs, and query plans |
| **Status semantics** | Success · Warning · Failed · Running · Info, **always paired with icon + text** (never color alone) |
| **Layout** | Persistent sidebar · header with workspace switcher, breadcrumbs, search, notifications · contextual panels |
| **Responsive** | Desktop-first, with tablet/mobile drawers, usable tables, and simplified graph interaction |
| **Accessibility** | Keyboard navigation, labelled controls, tabular alternatives to graphs, sufficient contrast, touch-friendly targets |

**Reusable components:** workspace switcher · dataset cards & catalog tables · connector cards · schema/column tables · SQL editor & result grid · job status badges · pipeline nodes/edges · run timelines · quality summaries · rule editors · lineage graph · metadata panels · filter bars · log viewers · drawers/modals · skeleton, empty, and error states · confirmation dialogs.

### Screens

| Screen | Purpose |
|---|---|
| **Landing / Auth** | Value proposition, login, registration, demo entry |
| **Dashboard** | Real-data overview of datasets, runs, quality, schema changes, alerts |
| **Catalog** | Search, filters, table/card view |
| **Dataset Detail** | Overview · Schema · Preview · Profile · Quality · Lineage · History · Metadata |
| **Sources** | Connector cards, config forms, connection tests |
| **Ingestion Workspace** | Preview → configure → run → result |
| **SQL Workspace** | Editor, schema browser, results, history, AI panel |
| **Pipeline Builder** | Node palette, canvas, config panel, logs, outputs |
| **Job Monitor** | Filterable job list, details, logs, retries |
| **Profiling** | Column stats, histograms, outliers, samples |
| **Quality Workspace** | Rules, runs, violations, history |
| **Lineage Explorer** | Interactive graph + tabular view |
| **Schema History** | Version diff, compatibility, acknowledgement |
| **AI Assistant** | Scoped Q&A with sources and links |
| **Alerts** | Notification center with deep links |
| **Settings** | Profile, theme, workspace, AI/storage/connector guidance |

---

## 📁 Project Structure

```text
dataatlas/
├── frontend/                    # Next.js + TypeScript application
│   ├── app/                     # Routes (App Router)
│   ├── components/
│   │   ├── layout/              # Shell, sidebar, header
│   │   ├── catalog/             # Dataset tables, cards, filters
│   │   ├── ingestion/           # Upload, preview, config
│   │   ├── sql/                 # Editor, schema browser, result grid
│   │   ├── pipelines/           # Canvas, nodes, config panels
│   │   ├── lineage/             # Graph + tabular views
│   │   ├── quality/             # Rule editors, run views
│   │   └── shared/              # Badges, dialogs, states
│   ├── hooks/                   # Data-fetching & UI hooks
│   ├── lib/                     # Utilities, validation schemas
│   ├── services/                # Typed API client
│   ├── types/                   # Shared TypeScript types
│   └── tests/                   # Vitest / Playwright
│
├── backend/
│   ├── app/
│   │   ├── api/v1/              # Routers
│   │   ├── core/                # Config, security, logging
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── repositories/        # Data access layer
│   │   ├── services/            # Business logic
│   │   ├── connectors/          # File, relational, S3 adapters
│   │   ├── ingestion/           # Ingestion engine
│   │   ├── storage/             # Lakehouse storage abstraction
│   │   ├── query_engine/        # DuckDB adapter + SQL validator
│   │   ├── transformations/     # Node → SQL compilers
│   │   ├── pipelines/           # Graph validation + executor
│   │   ├── profiling/           # Profiling engine
│   │   ├── quality/             # Rule engine
│   │   ├── lineage/             # Lineage recording & traversal
│   │   ├── schema_registry/     # Versioning & diffing
│   │   ├── ai/                  # Providers, retrieval, validators
│   │   ├── exports/             # Export & report generators
│   │   └── workers/             # Background job runner & scheduler
│   ├── migrations/              # Alembic migrations
│   └── tests/                   # pytest suite
│
├── data/
│   ├── demo/                    # Synthetic demo datasets
│   ├── uploads/                 # Validated uploads
│   ├── lakehouse/               # Bronze / Silver / Gold Parquet
│   └── temporary/               # Staging area (auto-cleaned)
│
├── docs/                        # Academic + technical documentation
├── scripts/                     # Seed, evaluation, utilities
├── docker-compose.yml
├── .env.example
├── README.md
├── PROJECT_SPEC.md
├── ARCHITECTURE.md
├── IMPLEMENTATION_PLAN.md
├── DECISIONS.md
├── PROGRESS.md
└── KNOWN_LIMITATIONS.md
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Docker + Docker Compose | recent | Recommended path |
| Python | 3.11+ | Manual backend setup |
| Node.js | 18+ (20 LTS recommended) | Manual frontend setup |
| PostgreSQL | 14+ | Manual setup only (Docker provides it) |

> **No cloud account, paid warehouse, Kubernetes, or LLM key is required.**

### Option 1: Docker Compose (recommended)

```bash
# 1. Clone
git clone https://github.com/<your-username>/my-data-leaf.git
cd my-data-leaf

# 2. Configure environment (safe defaults, no real secrets)
cp .env.example .env

# 3. Build and start frontend, backend, worker, PostgreSQL (and optional Redis)
docker compose up --build -d

# 4. Apply database migrations
docker compose exec backend alembic upgrade head

# 5. Load demo account + synthetic demo datasets
docker compose exec backend python -m scripts.seed_demo
```

Then open:

| Service | URL |
|---|---|
| 🖥 Web app | http://localhost:3000 |
| ⚙️ API | http://localhost:8000 |
| 📘 OpenAPI docs | http://localhost:8000/docs |
| ❤️ Health / readiness | http://localhost:8000/health · `/ready` |

**Demo login:** use the demo account created by the seed script. Its email and password come from `DEMO_USER_EMAIL` / `DEMO_USER_PASSWORD` in your `.env`, so no credentials are hardcoded in the source.

### Option 2: Manual local setup

<details>
<summary><b>Click to expand</b></summary>

<br/>

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/dataatlas"
alembic upgrade head
python -m scripts.seed_demo

uvicorn app.main:app --reload --port 8000
```

**Worker (separate terminal)**

```bash
cd backend && source .venv/bin/activate
python -m app.workers.run
```

**Frontend (separate terminal)**

```bash
cd frontend
npm install
npm run dev                         # http://localhost:3000
```

</details>

### Production build

```bash
# Frontend
cd frontend && npm run build && npm run start

# Backend
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Troubleshooting

| Symptom | Fix |
|---|---|
| Backend can't reach PostgreSQL | Check `DATABASE_URL`, confirm the `postgres` container is healthy: `docker compose ps` |
| `alembic` reports a missing revision | Run migrations from inside `backend/` or the backend container |
| Upload rejected | Check the file extension and signature, and the `MAX_UPLOAD_MB` limit |
| Jobs stay in `queued` | Make sure the **worker** service is running: `docker compose logs worker` |
| AI panel says "not configured" | Expected, as AI is optional. See [Configuration](#-configuration) |
| Port already in use | Change published ports in `docker-compose.yml` |

---

## ⚙️ Configuration

All configuration is **environment-based**. Copy `.env.example` → `.env`. The example file contains **no real secrets**.

| Variable | Purpose | Default / Notes |
|---|---|---|
| `DATABASE_URL` | PostgreSQL metadata DB | Compose default provided |
| `SECRET_KEY` | Session/token signing | **Set your own for any non-local use** |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000` |
| `LAKEHOUSE_PATH` | Parquet storage root | `./data/lakehouse` |
| `UPLOAD_PATH` | Validated upload directory | `./data/uploads` |
| `MAX_UPLOAD_MB` | Upload size limit | Safe default |
| `QUERY_TIMEOUT_SECONDS` | SQL execution timeout | Safe default |
| `QUERY_MAX_ROWS` | Result row cap | Safe default |
| `QUERY_MEMORY_LIMIT` | DuckDB memory limit | Safe default |
| `REDIS_URL` | Optional queue backend | Optional |
| `DEMO_USER_EMAIL` / `DEMO_USER_PASSWORD` | Demo account seed | Set locally |
| `AI_PROVIDER` | `none` · `openai` · `anthropic` · `local` | `none` |
| `AI_MODEL` | Model identifier | Configurable |
| `AI_API_KEY` | Provider credential | **Never commit** |
| `AI_AUTO_EXECUTE` | Auto-run validated generated SQL | `false` |
| `SMTP_*` | Optional email alerts | Disabled unless set |
| `S3_ENDPOINT` / `S3_BUCKET` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Optional object storage | Optional |

### Enabling the AI assistant (optional)

```bash
# .env
AI_PROVIDER=openai          # or anthropic / local
AI_MODEL=<your-model-name>
AI_API_KEY=<your-key>
```

Restart the backend. The AI panel will show **configured** status. Without a key, DataAtlas shows deterministic diagnostics, clearly labelled as **non-AI**.

### Connecting external sources (optional)

- **Relational DB:** add a read-only connection from *Sources → New Source → Database* (use a read-only DB user)
- **S3-compatible storage:** set the `S3_*` variables and register it from *Sources*

---

## 🧪 Demo Data

A **synthetic, legally safe, reproducible** business dataset is included to showcase joins, aggregations, transformations, quality rules, and lineage.

| Table | Description |
|---|---|
| `customers` | Synthetic customer profiles |
| `products` | Product catalog |
| `product_categories` | Category hierarchy |
| `orders` | Order headers |
| `order_items` | Line items |
| `payments` | Transactions |

Mixed types (numeric, categorical, date, string) and **related keys** enable meaningful analytics.

A **separate dirty dataset** deliberately includes missing values, duplicates, invalid dates, unexpected categories, type inconsistencies, and referential-integrity violations, so quality rules, schema detection, and failure analysis have real material to work on. It is documented separately and never mixed into the clean demo set.

> 🏷 All demo data is **synthetic** and visibly labelled as such. It does not represent real customers or live enterprise data.

**Regenerate demo data**

```bash
docker compose exec backend python -m scripts.seed_demo --reset
```

### Try this walkthrough

1. Sign in with the demo account
2. Open the **Catalog** and inspect `bronze.orders`
3. Run **Profiling** and check null/distinct/outlier stats
4. Open **SQL Workspace** and try:
   ```sql
   SELECT c.name AS category,
          SUM(oi.quantity * oi.unit_price) AS revenue
   FROM   order_items oi
   JOIN   products p            ON p.product_id = oi.product_id
   JOIN   product_categories c  ON c.category_id = p.category_id
   GROUP  BY c.name
   ORDER  BY revenue DESC
   LIMIT  5;
   ```
5. Build a **Cleaning Pipeline** (filter → cast → dedupe → sink to Silver)
6. Run it, then open the **Lineage Explorer** to trace Bronze → Silver
7. Add a **Quality Rule** (`order_id` unique) and run it against the dirty dataset
8. Re-ingest a file with a changed column to trigger a **schema change event**
9. Export the query result as **CSV**
10. Ask the **AI Assistant** *"Which datasets depend on orders?"* (if AI is configured)

---

## 🧫 Testing & Evaluation

A meaningful automated suite runs **without paid services** using isolated test databases and temporary storage.

### Run the tests

```bash
# Backend (unit + integration)
cd backend && pytest -v

# Backend with coverage
cd backend && pytest --cov=app --cov-report=term-missing

# Frontend unit/component tests
cd frontend && npm test

# Type checks & linting
cd frontend && npm run lint && npm run typecheck
cd backend  && ruff check . && mypy app

# End-to-end acceptance workflow
cd frontend && npx playwright test

# Evaluation suite
python -m scripts.run_evaluation
```

### What is covered

| Layer | Coverage areas |
|---|---|
| **Backend** | Auth · workspace isolation · upload restrictions · CSV/JSON ingestion · type inference · idempotency · catalog ops · profiling stats · SQL validation & permissions · query limits · graph validation · transformation correctness · job state transitions · schema-change detection · quality rules · lineage generation · exports · alerts · AI fallback · NL-SQL validation · cross-workspace access prevention |
| **Frontend** | Auth validation · workspace selection · catalog search/filter · source config · upload flow · schema preview · SQL editor · result grid · pipeline validation · job status · rule editing · lineage navigation · alert acknowledgement · theme switch · responsive nav · export actions |
| **Integration** | API ↔ PostgreSQL ↔ DuckDB ↔ storage: ingestion creates valid metadata + physical data, profiling reads stored data, SQL returns real results, transformations produce new outputs, rollback on failure |
| **E2E** | Login → workspace → upload CSV → ingest → catalog → profile → search → SQL → pipeline → run → output → lineage → quality rule → schema version → export → consistency check |
| **AI** | Mocked provider responses, adversarial/prompt-injection inputs, hallucinated-reference rejection, fallback behavior. Live-model tests run **only** if credentials and network exist |

### Evaluation framework

The evaluation suite defines inputs, expected outputs, metrics, and commands for:

`Ingestion correctness` · `Type inference` · `Profiling correctness` · `SQL safety` · `Transformation correctness` · `Schema-change detection` · `Lineage integrity` · `Quality-rule accuracy` · `Query result correctness` · `LLM-generated SQL validity` · `AI explanation grounding`

> 📌 **Reporting policy:** results documented in [`docs/evaluation/`](./docs/evaluation/) and [`PROGRESS.md`](./PROGRESS.md) are **only those actually produced** by running the suite. No invented accuracy numbers or benchmarks. Anything not run is listed as skipped or as a *proposed* evaluation.

---

## ⚡ Performance & Reliability

| Concern | Approach |
|---|---|
| Large files | Streaming / chunked ingestion, no full-file memory loads |
| Large result sets | Row caps, pagination, bounded exports |
| Heavy work | Background worker, never blocks the API |
| Runaway queries | Timeouts + resource limits |
| Duplicate processing | Idempotent job design, concurrency policy |
| Failures | Retries with backoff, clear retry history |
| Interrupted jobs | Recovered or surfaced after restart |
| Temp data | Staging cleanup after success/failure |
| External calls | Timeouts and graceful degradation (e.g., AI offline) |
| Observability | Structured logging, `/health` and `/ready`, safe worker shutdown |
| Lookups | Indexes on common filter/search paths |

Performance figures should be measured on the supplied evaluation dataset via the evaluation suite. A small synthetic dataset does **not** imply production-scale throughput.

---

## 📚 Documentation Map

| Document | Contents |
|---|---|
| [`PROJECT_SPEC.md`](./PROJECT_SPEC.md) | Scope, requirements, acceptance criteria |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Components, boundaries, data flows |
| [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) | Phases, tasks, completion criteria |
| [`DECISIONS.md`](./DECISIONS.md) | Architectural decision records and trade-offs |
| [`PROGRESS.md`](./PROGRESS.md) | Status, commands run, tests run, results |
| [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) | Deferred features and compromises |
| [`docs/architecture/`](./docs/architecture/) | Diagrams, component responsibilities, lakehouse storage design |
| [`docs/api/`](./docs/api/) | API reference notes |
| [`docs/database/`](./docs/database/) | Schema and ER documentation |
| [`docs/data-engineering/`](./docs/data-engineering/) | Ingestion, transformation, profiling, quality, lineage, schema evolution methodology |
| [`docs/ai-methodology/`](./docs/ai-methodology/) | NL-to-SQL, grounding, validation, prompt-injection handling |
| [`docs/evaluation/`](./docs/evaluation/) | Test methodology, metrics, reproducibility, results |

The academic documentation covers: motivation and objectives · functional and non-functional requirements · architecture and data-flow diagrams · use cases · database design · lakehouse layers · ingestion/transformation methodology · profiling and quality methodology · SQL safety architecture · scheduling and monitoring · lineage and schema evolution · AI methodology · security and privacy · testing and evaluation · installation and user guide · limitations and future work.

---

## 🗺 Development Roadmap

| Phase | Focus |
|:---:|---|
| 1 | Workspace inspection, requirements, architecture |
| 2 | Repository foundation, Docker, PostgreSQL, migrations, health checks, design tokens |
| 3 | Authentication, workspaces, permissions |
| 4 | Dataset storage and ingestion |
| 5 | Catalog and metadata |
| 6 | Profiling and exploration |
| 7 | SQL workspace and safe query execution |
| 8 | Transformation engine and pipeline builder |
| 9 | Job monitoring and scheduling |
| 10 | Lineage and schema evolution |
| 11 | Data quality and alerts |
| 12 | AI-assisted discovery and NL-to-SQL |
| 13 | Exports, reports, dashboard analytics |
| 14 | UI completion and end-to-end integration |
| 15 | Verification, academic documentation, delivery |

### 🔮 Future work

- Optional **Apache Spark / Trino** execution adapters for distributed processing
- **Delta Lake / Apache Iceberg** table formats (ACID, time travel)
- Streaming ingestion (Kafka-style sources)
- Column-level lineage
- Finer-grained RBAC and row/column-level security
- Vector-embedding-based semantic catalog search
- Additional database connectors

---

## ⚠️ Known Limitations

DataAtlas is deliberately honest about its boundaries:

- **Learning-scale**: a single-node Parquet + DuckDB lakehouse. It is **not** a distributed production cluster
- **Incremental ingestion** is available only for connectors that implement a cursor/watermark
- **Source database connectors** are read-only and cover only the supported database engines
- **SQL dialect** is that of DuckDB, not every SQL database
- **AI features** depend on an optional configured provider. Without one, only deterministic diagnostics are shown, labelled as such
- **Security**: not certified or audited for regulatory compliance or hardened multi-tenant deployment
- **Rename detection** in schema evolution is heuristic and flagged for review, never auto-confirmed
- **Scale claims** are not made beyond what the evaluation suite actually measured

See [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) for the complete, current list.

---

## 🤝 Contributing

Contributions, issues, and ideas are welcome.

```bash
# 1. Fork and create a branch
git checkout -b feature/your-feature

# 2. Make changes, add tests, run checks
cd backend && pytest && ruff check .
cd ../frontend && npm test && npm run lint

# 3. Commit using a clear message
git commit -m "feat: add <your feature>"

# 4. Push and open a pull request
git push origin feature/your-feature
```

**Guidelines:** keep modules small and typed · add tests for new behavior · never commit secrets · update the relevant docs and `PROGRESS.md` · don't fake functionality, so a feature is either implemented or documented as a limitation.

---

## 📜 License & Acknowledgements

Distributed under the license specified in the [`LICENSE`](./LICENSE) file.

**Built with** [FastAPI](https://fastapi.tiangolo.com/) · [Next.js](https://nextjs.org/) · [DuckDB](https://duckdb.org/) · [Apache Parquet](https://parquet.apache.org/) · [PostgreSQL](https://www.postgresql.org/) · [SQLAlchemy](https://www.sqlalchemy.org/) · [Alembic](https://alembic.sqlalchemy.org/) · [React Flow](https://reactflow.dev/) · [Monaco Editor](https://microsoft.github.io/monaco-editor/) · [Tailwind CSS](https://tailwindcss.com/) · [shadcn/ui](https://ui.shadcn.com/) · [sqlglot](https://github.com/tobymao/sqlglot)

<div align="center">

<br/>

**DataAtlas**: *Understand Your Data. Trace Every Transformation.*

Built as a CSE senior project 🎓 · If you find it useful, consider giving it a ⭐

</div>
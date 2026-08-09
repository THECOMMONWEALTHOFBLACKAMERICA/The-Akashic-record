# T.A.R. — The Akashic Records

**Release candidate: 1.0.0-rc.1**

T.A.R. is an open, source-aware, community-governed multimodal AI platform for preserving, searching, analyzing, verifying, creating and expanding knowledge while retaining provenance.

T.A.R. is not an oracle. Source evidence, persistent memory, model interpretation, execution and governance are deliberately separate layers so generated claims remain auditable.

## Current capabilities

### Research and knowledge

- conversational research with evidence returned alongside answers
- persistent workspace-scoped memory
- lexical + optional sentence-transformer semantic retrieval
- current-web metasearch through an operator-controlled SearXNG instance
- Wikipedia and Wikidata
- Library of Congress
- U.S. National Archives Catalog API v2
- PubMed / NCBI E-utilities
- Dawes / Final Rolls research strategy
- Freedmen records research strategy
- operator-supplied archival datasets and documents
- source URLs, retrieval metadata, dates when available and provenance metadata

### Ingestion and research library

T.A.R. can ingest:

- PDF
- EPUB
- TXT / Markdown
- CSV / JSON
- DOCX
- XLSX
- PPTX

EPUB ingestion follows the package/spine, extracts metadata and readable chapters, and does not execute embedded scripts or remote content.

Each workspace has a research-library layer for favorites, reading progress, flexible page/chapter/section locators and notes.

### Bounded autonomous agents

T.A.R. includes a persisted multi-step planner/executor.

Default autonomous tools:

- search
- recall
- research
- PDF generation
- DOCX generation
- configured image generation
- configured video generation

Autonomy is intentionally bounded. A hard step budget applies and autonomous planning does **not** include shell/code execution, credential changes, purchases, external messaging, destructive operations or governance mutation.

Runs and individual steps are persisted and remain workspace-scoped.

### Documents, media and artifacts

- PDF creation, merge and annotation
- DOCX creation
- XLSX creation
- CSV analysis
- image metadata processing
- configurable image-generation provider
- configurable image-edit provider
- configurable video-generation provider
- configurable audio-transcription provider
- artifacts recorded with SHA-256 integrity metadata
- local or S3-compatible artifact storage
- MinIO development profile for shared-storage testing

### Distributed execution

- PostgreSQL-backed durable job queue
- capability-based worker registration
- leased jobs with concurrent-worker row locking
- retries and worker heartbeats
- independent worker capability lists
- autonomous goals can execute through the distributed queue using task kind `agent`

### Provenance and decentralized publication

- hash-chained workspace audit records
- artifact SHA-256 verification on retrieval
- explicit, opt-in public IPFS publication
- artifact CID plus a separate canonical provenance-manifest CID
- public IPFS publication is disabled by default and requires administrative authorization and explicit acknowledgement of immutable/public storage

### Governance

The Solidity governance registry provides:

- proposals based on action hashes
- voting-power assignments
- snapshotted proposal quorum
- voting periods and timelocks
- guardian cancellation
- bounded vote arithmetic
- two-step administrator transfer

The governance contract records approved action hashes. It deliberately does not make arbitrary external calls. Normal AI inference does not require a blockchain transaction.

## Architecture

```text
Operator / API Client
        |
        v
FastAPI + Workspace Identity
        |
        +--> Bounded Agent Planner/Executor
        |        +--> Search / Recall / Research
        |        +--> Document / Media Tools
        |        `--> Persistent Run + Step History
        |
        +--> Research Orchestrator --> LLM Provider
        |        |
        |        +--> Hybrid Retrieval
        |        |      +--> Persistent Source Memory
        |        |      `--> Chunked Document Store
        |        `--> Archive + Current-Web Connectors
        |
        +--> Ingestion --> Provenance + Research Library
        +--> Artifact Layer --> Local or S3-Compatible Storage
        +--> Durable Queue --> Distributed Workers
        +--> Workspace Audit Chain
        +--> Optional IPFS Publication
        `--> Governance Adapter / Contract

PostgreSQL  = production system of record
S3/MinIO    = shared artifact storage option
SearXNG     = optional self-hosted current-web metasearch
Prometheus  = operational metrics
IPFS        = optional intentional public/distributed publication
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Quick start

Requirements: Docker with Compose.

```bash
cp .env.example .env
```

At minimum, replace the example PostgreSQL password before starting.

```bash
docker compose up --build
```

Compose runs Alembic migrations before starting the API and workers.

Local endpoints:

- Operator console: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/ready`
- Metrics: `http://localhost:8000/metrics`

### Optional current-web metasearch

Run the bundled SearXNG override:

```bash
docker compose -f docker-compose.yml -f compose.websearch.yml up --build
```

SearXNG is exposed only on localhost by the supplied development configuration. Change its secret and deployment controls before exposing it beyond a developer machine.

### Optional monitoring

```bash
docker compose --profile monitoring up --build
```

Prometheus is available on localhost port `9090`.

### Optional shared artifact storage

The `distributed-storage` profile provides local MinIO infrastructure for S3-compatible testing. Configure the S3 environment variables in `.env` and set `TAR_ARTIFACT_BACKEND=s3` for T.A.R. services that should use it.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
alembic upgrade head
pytest -q
uvicorn backend.app.production:app --reload
```

`TAR_AUTO_SCHEMA_BOOTSTRAP=auto` retains convenient SQLite bootstrap behavior for development. Production/PostgreSQL deployments use Alembic as the schema authority.

## Important API surfaces

### Research

- `POST /v1/ask`
- `POST /v1/search`
- `POST /v1/memory/recall`
- `GET /v1/memory/stats`

### Agents

- `POST /v1/agents/run`
- `GET /v1/agents/runs/{run_id}`

### Ingestion and library

- `POST /v1/ingest/file`
- `GET /v1/ingest/jobs/{job_id}`
- `GET /v1/documents`
- `GET /v1/library`
- `GET /v1/library/{document_id}`
- `PUT /v1/library/{document_id}`

### Distributed jobs

- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- authenticated worker claim/complete/fail routes

### Documents and media

- `/v1/doc-tools/*`
- `/v1/media/*`
- `/v1/tools/csv`
- `/v1/tools/image-metadata`

### Artifacts and provenance

- `GET /v1/artifacts`
- `GET /v1/artifacts/{artifact_id}`
- publication routes mounted by the production app
- `GET /v1/audit`
- `GET /v1/audit/verify`

### Operations and governance

- `/v1/system/providers`
- `/v1/system/capabilities`
- `/v1/system/storage`
- `/v1/system/version`
- `/v1/admin/*`
- `/v1/nodes*`
- `/v1/governance*`

## Production security

When `TAR_ENV=production`, T.A.R. fails closed unless core production requirements are satisfied. Among other checks, production requires:

- PostgreSQL
- `TAR_REQUIRE_API_KEY=true`
- strong, distinct `TAR_ADMIN_KEY` and `TAR_WORKER_KEY`
- explicit HTTPS allowed origins
- API-host code execution disabled
- valid artifact-backend configuration

Code execution is not an autonomous-agent capability. The separate explicit Python/code primitive remains disabled by default and belongs only in hardened disposable sandbox workers if an operator intentionally enables it.

Read [`SECURITY.md`](SECURITY.md) and [`docs/PRODUCTION_RUNBOOK.md`](docs/PRODUCTION_RUNBOOK.md) before network deployment.

## Provider configuration

T.A.R. ships provider interfaces—not invented service URLs and not proprietary credentials.

Operators choose and configure:

- language model endpoint/model
- image generation/editing endpoint/model
- video endpoint/model
- transcription endpoint/model
- NARA API key
- optional NCBI identity/API key
- optional SearXNG instance
- optional blockchain RPC + governance contract

If no LLM endpoint is configured, the development echo provider keeps retrieval/evidence paths testable without pretending model synthesis occurred.

## Release qualification

CI is designed to validate:

- Python compilation
- frontend JavaScript syntax
- PostgreSQL migration upgrade → downgrade → upgrade
- Alembic model/migration drift
- Python tests
- live API + worker smoke test
- ingestion and recall
- research-library persistence
- bounded-agent persistence
- artifact creation/retrieval
- audit-chain verification
- distributed jobs
- governance-contract tests
- Docker Compose configuration
- container image build
- CodeQL and dependency-update workflows

Tagged releases are separately gated before the container is published. The tag must match the repository `VERSION` file, and the release workflow reruns database migration, tests and live smoke validation before pushing to GitHub Container Registry and generating build provenance.

See [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

## What code cannot provide by itself

A production installation still requires real infrastructure and operator-owned credentials where applicable: hosting, DNS/TLS, PostgreSQL, durable object storage, model/media provider access or self-hosted models, optional NARA credentials, optional SearXNG, optional blockchain RPC/contract deployment, secret management, monitoring destinations and backup storage.

Those are deployment dependencies, not placeholder functionality. T.A.R. deliberately fails explicitly when a requested external provider is not configured.

## Third-party design reference

Phase 17 reviewed the MIT-licensed `Luiz-eduardp/akashic_records` project for compatible EPUB/offline-library concepts. T.A.R. reimplemented those concepts in its own architecture and did not vendor the upstream novel-site scraping plugins. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Project documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/AUTONOMY.md`](docs/AUTONOMY.md)
- [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md)
- [`docs/IPFS_PROVENANCE.md`](docs/IPFS_PROVENANCE.md)
- [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md)
- [`docs/PRODUCTION_RUNBOOK.md`](docs/PRODUCTION_RUNBOOK.md)
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)
- [`SECURITY.md`](SECURITY.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## License

MIT

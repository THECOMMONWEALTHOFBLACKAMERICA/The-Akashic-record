# T.A.R. — The Akashic Records

**Release candidate: 1.1.0-rc.1**

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

### Foundational Citizenship Commission case engine

T.A.R. includes an optional Commission workflow designed to support — not replace — human citizenship review. Commission routes require an authenticated T.A.R. API key even if the general development API permits anonymous access.

The case engine provides:

- credential-scoped case access roles (`owner`, `commissioner`, `staff`, `reviewer`, `readonly`)
- strict case-level isolation inside a Commission workspace
- source tiers and human evidence statuses (`verified`, `corroborated`, `conflicting`, `unverified`, `insufficient`, `excluded`)
- protected evidence uploads with SHA-256 and chain-of-custody metadata
- case-local research plus restricted official/archive connectors by default
- explicit broad-web override rather than implicit web evidence
- human evidence review and source-tier correction
- legal holds and policy-based retention deletion
- case-authorized audit and protected-artifact retrieval
- a hard block preventing protected Commission evidence from public IPFS publication

The generic artifact and audit APIs deliberately hide protected Commission originals/events. Commission materials use `/v1/commission/*` routes so case grants remain enforceable. Applicant evidence should not be placed into the generic workspace ingestion pipeline.

See [`docs/TAR-CITIZENSHIP-COMMISSION-INTEGRATION.md`](docs/TAR-CITIZENSHIP-COMMISSION-INTEGRATION.md) and [`docs/COMMISSION_CASE_ENGINE.md`](docs/COMMISSION_CASE_ENGINE.md).

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
- protected Commission originals cannot be published through the IPFS endpoint even by an administrator

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
        +--> Commission Case Engine
        |        +--> Per-Key Case Grants
        |        +--> Evidence + Protected Artifacts
        |        +--> Restricted Archive Research
        |        `--> Case Audit / Retention
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

Prometheus is then available on localhost port `9090`.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
alembic upgrade head
pytest -q
uvicorn backend.app.production:app --reload
```

## Core API surfaces

### Research and memory

- `POST /v1/ask`
- `POST /v1/search`
- `POST /v1/memory/recall`
- `GET /v1/memory/stats`

### Commission cases

- `POST /v1/commission/cases`
- `GET /v1/commission/cases`
- `PATCH /v1/commission/cases/{case_id}`
- `POST /v1/commission/cases/{case_id}/research`
- `POST /v1/commission/cases/{case_id}/evidence`
- `POST /v1/commission/cases/{case_id}/evidence/upload`
- `GET /v1/commission/cases/{case_id}/evidence`
- `PATCH /v1/commission/evidence/{evidence_id}/review`
- `GET /v1/commission/cases/{case_id}/artifacts/{artifact_id}`
- `GET /v1/commission/cases/{case_id}/audit`
- `GET /v1/commission/cases/{case_id}/export`
- case access management under `/v1/commission/cases/{case_id}/access`

### Knowledge ingestion

- `POST /v1/ingest/file`
- `GET /v1/ingest/jobs/{job_id}`
- `GET /v1/documents`

### Durable jobs and agents

- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `/v1/agents/*`

### Artifacts and tools

- `GET /v1/artifacts`
- `GET /v1/artifacts/{artifact_id}`
- `/v1/doc-tools/*`
- `/v1/media/*`
- `/v1/tools/csv`
- `/v1/tools/image-metadata`

### Control and provenance

- `/v1/admin/*`
- `/v1/nodes*`
- `/v1/audit`
- `/v1/audit/verify`
- `/v1/governance*`
- `/v1/system/providers`
- `/v1/system/capabilities`
- `/v1/system/version`

## Model and media providers

T.A.R. ships provider interfaces, not fabricated service URLs or bundled proprietary credentials. Configure supported endpoints in `.env`.

Without an LLM endpoint, `TAR_LLM_PROVIDER=echo` keeps research/evidence inspection usable for development without pretending model synthesis occurred.

## Security and production

Stored memory, documents, ordinary artifacts and general research are workspace-scoped. Commission case materials add a second case-level authorization boundary and must use Commission-specific routes.

Administrative actions use `TAR_ADMIN_KEY`; worker operations use a separate worker trust boundary. Arbitrary code execution remains disabled on API hosts and should only be enabled inside hardened disposable sandbox workers.

Production should use PostgreSQL, durable shared artifact/object storage, TLS, secret management, API authentication, backup/restore drills and monitoring. Read [`SECURITY.md`](SECURITY.md), [`docs/PRODUCTION_RUNBOOK.md`](docs/PRODUCTION_RUNBOOK.md), and [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

## Database migrations

Fresh databases:

```bash
alembic upgrade head
```

Commission persistence is introduced by revision `0005_commission_cases`.

## CI and releases

CI is configured for Python compilation/tests, PostgreSQL migrations and drift checks, live API/worker smoke tests, governance-contract tests, frontend syntax checks, Compose validation, Docker image builds and CodeQL. Tag releases are gated by version consistency and the release validation workflow before container publication.

## License

MIT

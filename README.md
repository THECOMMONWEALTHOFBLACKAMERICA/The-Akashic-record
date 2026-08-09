# T.A.R. — The Akashic Records

**Release candidate: 0.13.0-rc.1**

T.A.R. is an open, source-aware, community-governed multimodal AI platform designed to preserve, search, analyze, verify, create and expand human knowledge while retaining provenance.

T.A.R. is not an oracle and does not treat model output as automatically true. Its architecture separates source evidence, persistent memory, generated interpretation, execution and governance.

## What it does

- conversational research with citation-ready evidence
- persistent workspace-scoped memory
- hybrid recall across source records and ingested documents
- archive and public-data research
- distributed durable AI jobs and capability-based workers
- PDF/DOCX/XLSX creation plus PDF merge and annotation
- PDF, TXT, MD, CSV, JSON, DOCX, XLSX and PPTX ingestion
- CSV analysis and image metadata processing
- configurable language-model provider
- configurable image generation and editing providers
- configurable video generation provider
- configurable audio transcription provider
- artifact storage with SHA-256 integrity metadata
- workspace API keys and independent administrative authorization
- hash-chained workspace audit/provenance records
- blockchain governance foundation
- PostgreSQL production deployment, migrations, readiness checks and Prometheus metrics

## Knowledge sources

Built-in source adapters/strategies include:

- Wikipedia
- Wikidata
- Library of Congress
- U.S. National Archives Catalog API v2
- PubMed / NCBI E-utilities
- Dawes / Final Rolls research strategy
- Freedmen records research strategy
- operator-supplied archival datasets and documents

T.A.R. does **not** silently mirror entire third-party libraries. It retrieves public or authorized material on demand and preserves source metadata. Operators remain responsible for source licensing, privacy and archive/API terms.

## Architecture

```text
Client / Operator Console
          |
          v
FastAPI + Workspace Identity
          |
          +--> Research Orchestrator --> Model Provider
          |          |
          |          +--> Hybrid Retrieval
          |          |      +--> Source Memory
          |          |      `--> Document Chunks
          |          `--> Archive Connectors
          |
          +--> Ingestion --> Provenance + Chunk Store
          +--> Document / Media Tools --> Artifact Store
          +--> Durable Job Queue --> Distributed Workers
          +--> Audit Chain
          `--> Governance Adapter / Contract

PostgreSQL = production system of record
Artifact storage = generated/source files
Prometheus = operational metrics
IPFS = optional public/distributed artifact layer
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for trust boundaries and scaling details.

## Quick start with Docker

Requirements: Docker with Compose.

```bash
cp .env.example .env
```

At minimum, replace `TAR_POSTGRES_PASSWORD` with a strong local value. For any network-accessible deployment also configure `TAR_ADMIN_KEY`, require API authentication, and set explicit allowed origins.

Start the system:

```bash
docker compose up --build
```

Compose performs the database migration before API/workers start.

- Operator console: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/ready`
- Metrics: `http://localhost:8000/metrics`

Optional local monitoring:

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

For Windows PowerShell use the appropriate virtual-environment activation command.

## Release smoke test

With the API and a worker running:

```bash
python scripts/smoke_test.py
```

The smoke test verifies the live service path: readiness, question answering, ingestion, recall, PDF creation/retrieval, audit integrity and a queued distributed job.

For an authenticated deployment set:

```bash
export TAR_SMOKE_URL=https://your-host.example
export TAR_SMOKE_API_KEY=tar_your_workspace_key
python scripts/smoke_test.py
```

## Core API surfaces

### Research and memory

- `POST /v1/ask`
- `POST /v1/search`
- `POST /v1/memory/recall`
- `GET /v1/memory/stats`

### Knowledge ingestion

- `POST /v1/ingest/file`
- `GET /v1/ingest/jobs/{job_id}`
- `GET /v1/documents`

### Durable jobs

- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- worker claim/complete/fail endpoints under `/v1/jobs`

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

T.A.R. ships provider **interfaces**, not fabricated service URLs or bundled proprietary credentials. Configure supported endpoints in `.env`:

- `TAR_LLM_*`
- `TAR_IMAGE_*`
- `TAR_VIDEO_*`
- `TAR_TRANSCRIBE_*`

`GET /v1/system/providers` reports only whether integrations are configured; it never returns provider secrets.

Without an LLM endpoint, `TAR_LLM_PROVIDER=echo` keeps the research pipeline usable for development and evidence inspection without pretending a model-generated synthesis occurred.

## Archive credentials

NARA Catalog API v2 requires an operator-supplied API key (`TAR_NARA_API_KEY`). NCBI application identity/API configuration is available through `TAR_NCBI_EMAIL` and `TAR_NCBI_API_KEY`.

## Workspaces and security

Stored memory, documents, chunks, ingestion jobs, retrieval results and artifacts are workspace-scoped.

Administrative actions are separately protected by `TAR_ADMIN_KEY`; an ordinary workspace API credential is not an administrator credential.

Code execution is **disabled by default**. Do not enable arbitrary code execution on the API container. Executable workloads belong only in hardened, disposable sandbox workers with no ambient secrets and restricted network/filesystem access.

Read [`SECURITY.md`](SECURITY.md) before exposing T.A.R. to a network.

## Database migrations

Release-to-release schema management uses Alembic.

Fresh database:

```bash
alembic upgrade head
```

Existing pre-Alembic deployments should follow [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md) and back up before stamping the baseline.

## Production operations

Read [`docs/PRODUCTION_RUNBOOK.md`](docs/PRODUCTION_RUNBOOK.md) for deployment, backup/restore, incident response, monitoring and release procedures.

Production should use:

- PostgreSQL
- durable artifact/object storage
- TLS/reverse proxy or managed ingress
- secret management
- API authentication
- separate worker pools by risk/capability
- backup and restore drills
- metrics/log aggregation and alerting

## CI and release pipeline

Pull requests and pushes run:

- Python compilation
- PostgreSQL migration
- test suite
- live API + worker smoke test
- Docker image build validation
- CodeQL scanning

Dependabot tracks Python, Actions and Docker dependencies.

Tagging a reviewed `main` commit with `v*` activates the release workflow, which builds/pushes the container to GitHub Container Registry, creates a GitHub release and generates a build-provenance attestation.

## Governance

The governance layer is intended for protocol and control-plane decisions—not for making every AI query a blockchain transaction. A deployment must configure an RPC endpoint and governance contract address before the on-chain adapter is active.

## Privacy and provenance

Do not place private medical records, identity documents, credentials, financial secrets, confidential archives or other sensitive data on public IPFS. Public immutable storage should be used only for material intentionally suitable for public distribution.

SHA-256 artifact hashes and audit chains provide tamper evidence. They do not prove that an archival claim or AI-generated statement is true. T.A.R. preserves source identity so evidence can be checked independently.

## Project documents

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/PRODUCTION_RUNBOOK.md`](docs/PRODUCTION_RUNBOOK.md)
- [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md)
- [`SECURITY.md`](SECURITY.md)
- [`CHANGELOG.md`](CHANGELOG.md)

## License

MIT

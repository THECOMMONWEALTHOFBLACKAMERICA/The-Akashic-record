# T.A.R. Architecture

## System goal

T.A.R. is a source-aware, multimodal AI platform that separates knowledge retrieval, persistent memory, execution, artifacts, governance and distributed compute into independently evolvable layers.

## Request plane

`client -> API -> identity/workspace -> orchestrator -> retrieval/providers -> response`

The API authenticates a caller and establishes a workspace. The orchestrator first recalls workspace-scoped evidence, optionally queries configured public/archive sources, persists useful evidence, and invokes the configured language-model provider when synthesis is required.

## Knowledge plane

- **Source connectors** query Wikipedia/Wikidata, Library of Congress, NARA, PubMed and dedicated genealogy/archive strategies.
- **Ingestion** normalizes supported files, records provenance, chunks content and deduplicates by cryptographic hash.
- **Memory** stores source evidence separately from document chunks.
- **Hybrid retrieval** combines persisted evidence and chunk search inside the caller's workspace.

Source metadata is retained because a generated answer is not a substitute for provenance.

## Execution plane

Durable jobs are stored in PostgreSQL. Workers register capabilities, heartbeat, lease compatible jobs, execute them and record results. High-risk capabilities such as arbitrary code execution belong on separate sandboxed worker pools.

## Artifact plane

Generated documents, analyses and media are stored as artifacts with SHA-256 hashes and workspace ownership. Production deployments should use durable/object storage even when local filesystem storage is convenient during development.

## Multimodal plane

Provider adapters isolate T.A.R. from any single vendor. Text/model, image generation/editing, video generation and transcription endpoints are configured at deployment time. Missing providers fail explicitly rather than using fictional endpoints.

## Control plane

- workspaces and API keys
- independent administrative authorization
- node registry/heartbeats
- workspace-scoped audit chain
- governance adapter and smart contract

Governance is for protocol/control decisions, not every user inference.

## Storage

PostgreSQL is the production system of record for control state, memory metadata, document/chunk indexes, jobs and artifact metadata. SQLite remains a development convenience only.

Large artifact bytes should reside in durable filesystem/object storage. Public IPFS may be used only for material intentionally suitable for public immutable distribution; sensitive records must not be placed there.

## Security invariants

1. Workspace A cannot recall, enumerate or retrieve Workspace B's stored knowledge/artifacts.
2. Ordinary API credentials cannot perform administrative operations.
3. Code execution is disabled on API hosts.
4. Provider credentials never enter browser bundles or stored research text.
5. Audit-chain failure is surfaced, not silently repaired.
6. A production deployment never silently falls back from PostgreSQL to SQLite.
7. External content and provider output are untrusted input.

## Scaling path

API replicas are stateless except for configured artifact storage and use shared PostgreSQL. Worker pools scale independently by capability. Heavy media/GPU workers can be separated from research/document workers. Retrieval can later move from SQL scoring to a dedicated vector/search engine without changing the source/ingestion contracts.

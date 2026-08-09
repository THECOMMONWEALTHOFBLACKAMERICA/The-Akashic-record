# Changelog

## 1.1.0-rc.1

### Foundational Citizenship Commission case engine
- added authenticated Commission case management under `/v1/commission`
- Commission APIs require a real T.A.R. API key even when the general development API permits anonymous access
- API-key identities now expose stable `key_id` values for case-level authorization grants
- case access is credential-scoped with owner, commissioner, staff, reviewer and read-only roles
- only owners/commissioners can manage access, legal holds, retention settings and final case dispositions
- added evidence source tiers and human-review statuses: verified, corroborated, conflicting, unverified, insufficient and excluded
- applicant uploads preserve SHA-256, uploader, claimed provenance, source metadata and protected original artifact storage
- Commission original evidence is explicitly blocked from public IPFS publication, including administrative publication attempts
- restricted Commission research defaults to workspace/vetted material and official archival strategies; broad web/Wikipedia/Wikidata require an intentional override
- retrieved research enters the case as unverified evidence rather than an automated citizenship determination
- legal holds block deletion
- policy-authorized deletion removes case/evidence rows, revokes case grants and attempts protected artifact cleanup while reporting any incomplete cleanup
- Commission model, access, retention and IPFS-guard tests added
- Alembic revision `0005_commission_cases` adds case, evidence and case-access persistence
- system capability reporting now advertises the Commission case engine and its public-IPFS prohibition

## 1.0.0-rc.1

### Final qualification
- production configuration now fails closed for unsafe production defaults
- PostgreSQL/Alembic is authoritative in production; remaining import-time schema creation and default-workspace mutation are suppressed during migration discovery
- migration CI validates upgrade, one-step downgrade, re-upgrade and ORM/schema drift
- live smoke testing now covers ingestion, recall, research-library state, bounded agent persistence, PDF artifact integrity, audit verification and distributed jobs
- default worker capabilities now include bounded agent jobs
- current-web SearXNG deployment is packaged as a local Compose override
- operator console exposes bounded agents, EPUB/library workflows, capability state and agent jobs
- CI validates frontend JavaScript and Docker Compose configurations in addition to Python, governance contracts and container builds
- tagged release workflow is gated by version/tag consistency, PostgreSQL migrations, tests and live API/worker smoke validation before GHCR publication
- added explicit 1.0 release checklist separating code qualification from production infrastructure/provider qualification
- root README brought current with semantic retrieval, EPUB, live web, S3/MinIO, IPFS provenance, bounded autonomy and production requirements

## 0.18.0-rc.1

### Bounded autonomous runtime
- added persistent multi-step agent runs and per-step execution records
- planner uses a hard allowlist and a configurable maximum of 10 steps
- safe autonomous tools are limited to search, recall, research, PDF/DOCX generation and configured image/video generation
- autonomous planning explicitly excludes shell/code execution, credential operations, purchases, messaging, destructive actions and governance mutation
- every run remains workspace-scoped and can be retrieved only from its owning workspace
- autonomous goals can execute directly through `/v1/agents/run` or through the durable task/worker system using task kind `agent`
- planner falls back to deterministic research plans when no planning-capable model is configured
- completed/failed runs are audited through the existing workspace audit chain
- Alembic migration and autonomy boundary tests added

## 0.17.0-rc.1

### Current knowledge and reading library
- added safe native EPUB metadata/chapter extraction and ingestion
- added operator-controlled SearXNG current-web metasearch with provenance and publication dates when supplied
- web search remains optional and archive-only research continues when no metasearch endpoint is configured
- added workspace-scoped research library favorites, progress, locators and notes
- added Alembic migration for library state
- added explicit development-only schema bootstrap so Alembic is authoritative for PostgreSQL production
- Alembic model discovery no longer creates or repairs tables as an import side effect
- added EPUB, web connector and library isolation tests
- feature direction was informed by the MIT-licensed `Luiz-eduardp/akashic_records` reader project; T.A.R. ports compatible concepts into its own backend rather than copying unrelated novel scraping plugins

## 0.16.0-rc.1

### Public provenance
- IPFS publication is now an explicit admin operation rather than an implied side effect of running an IPFS daemon
- public publication is disabled by default behind `TAR_ENABLE_PUBLIC_IPFS`
- administrators must explicitly acknowledge immutable/public storage before publishing
- T.A.R. pins artifact bytes plus a canonical provenance manifest
- publication records persist artifact CID, manifest CID, SHA-256 and workspace ownership
- publication actions are written to the workspace audit chain
- Alembic migration and publication tests added

## 0.15.0-rc.1

### Distributed storage
- artifacts now use a storage backend abstraction instead of assuming one host filesystem
- S3-compatible storage supports AWS S3, MinIO and compatible object stores
- existing legacy local artifact paths remain readable during migration
- newly retrieved artifacts are SHA-256 verified before they are served
- failed metadata commits clean up newly written artifact objects
- storage health and active backend are exposed in the system API
- optional local MinIO Compose profile added for distributed-storage testing

## 0.14.0-rc.1

### Intelligence
- optional sentence-transformer semantic reranking layered over lexical retrieval
- semantic retrieval remains fail-soft and falls back to lexical ranking if the model is disabled or unavailable
- semantic readiness is exposed through the operational capability/status APIs
- workspace boundaries remain enforced during semantic and lexical retrieval

### Governance
- proposal quorum is snapshotted at proposal creation
- vote/quorum arithmetic is bounded to proposal counter widths
- administration now uses a two-step transfer
- proposal/timelock timestamp overflow is rejected
- governance execution remains deliberately limited to recording an approved action hash rather than making arbitrary external calls
- Hardhat governance tests and contract CI added
- governance trust model and deployment checklist documented

## 0.13.0-rc.1

Release candidate consolidating the T.A.R. platform into a deployable system.

### Knowledge and research
- persistent workspace-scoped memory and hybrid retrieval
- traceable source metadata and provenance
- Wikipedia, Wikidata, Library of Congress, NARA, PubMed, Dawes/Final Rolls and Freedmen research strategies
- PDF, text, CSV, JSON, DOCX, XLSX and PPTX ingestion

### Execution and multimodal
- durable PostgreSQL-backed jobs and distributed workers
- artifact persistence and SHA-256 integrity metadata
- PDF/DOCX/XLSX creation and PDF merge/annotation tools
- provider interfaces for language models, image generation/editing, video generation and audio transcription
- executable-code support disabled by default and reserved for isolated workers

### Governance and security
- workspaces and API keys
- independent administrative authorization
- workspace-scoped audit chains and verification
- blockchain governance primitives and adapter
- strict workspace isolation for stored knowledge and artifacts

### Operations
- PostgreSQL production deployment
- Alembic migration baseline
- API readiness checks
- Prometheus metrics
- non-root production container
- Docker secret/data exclusions
- end-to-end smoke test
- PostgreSQL integration CI and Docker build validation
- CodeQL and Dependabot configuration
- signed/attested GHCR release workflow
- production, migration, architecture, backup/restore and incident-response documentation

### External configuration still required
T.A.R. intentionally does not ship vendor credentials or proprietary model access. Operators choose and configure their model/media providers, NARA API key, governance RPC/contract, deployment domain/TLS and production infrastructure.

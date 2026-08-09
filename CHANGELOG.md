# Changelog

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

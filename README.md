# T.A.R. — The Akashic Records

T.A.R. is an open, community-governed multimodal AI knowledge network designed to preserve, search, analyze, verify, create, and expand human knowledge while retaining source provenance.

## Capabilities

- Conversational AI and coding
- Retrieval-augmented generation (RAG)
- Persistent research memory backed by SQLAlchemy/SQLite
- PDF, text, CSV, and JSON ingestion with chunking and SHA-256 deduplication
- Hybrid recall across remembered source records and ingested document chunks
- Web and archive research
- Wikipedia/Wikidata connectors
- Library of Congress connector
- National Archives catalog connector
- Dawes/Freedmen dataset ingestion support through CSV/JSON/PDF imports
- Image/video provider interfaces
- IPFS-compatible artifact storage
- Blockchain governance foundation
- Source provenance and confidence metadata
- Docker-based local development

## Architecture

```text
Web UI -> FastAPI -> Orchestrator -> Model Provider
                    |-> Hybrid Retrieval
                    |    |-> Persistent Research Memory
                    |    `-> Chunked Document Store
                    |-> Source Connectors
                    |-> Ingestion Pipeline
                    |-> Artifact Storage
                    |-> Provenance Ledger
                    `-> Governance
```

T.A.R. follows a memory-first flow: it recalls stored evidence and ingested documents, optionally performs live source searches, persists new records, deduplicates them, and gives the model a combined evidence set with source metadata.

## Quick start

1. Copy `.env.example` to `.env`.
2. Configure an LLM provider, or use the built-in development echo provider.
3. Run `docker compose up --build`.
4. API docs: `http://localhost:8000/docs`
5. Web app: `http://localhost:3000`

## API

- `GET /health` — service and memory status
- `POST /v1/ask` — answer using stored memory, ingested documents, and optional live research
- `POST /v1/search` — search configured archives and optionally persist results
- `POST /v1/memory/recall` — hybrid recall across memory and document chunks
- `GET /v1/memory/stats` — record counts by source
- `POST /v1/ingest/file` — ingest PDF, TXT, MD, CSV, or JSON up to 100 MB
- `GET /v1/ingest/jobs/{job_id}` — inspect ingestion status
- `GET /v1/documents` — list ingested documents

Example research request:

```bash
curl -X POST http://localhost:8000/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"Find primary-source material about Freedmen enrollment records","research":true}'
```

Example document ingestion:

```bash
curl -X POST http://localhost:8000/v1/ingest/file \
  -F 'file=@records.pdf' \
  -F 'source=freedmen_records' \
  -F 'title=Freedmen Enrollment Records'
```

## Knowledge sources

Connectors are adapters. T.A.R. does not silently mirror entire third-party collections. It retrieves public/authorized records on demand, preserves citations and metadata, and can index permitted datasets supplied by operators.

Included adapters cover Wikipedia, Wikidata, Library of Congress, the U.S. National Archives catalog, and local archival datasets such as properly sourced Dawes or Freedmen roll exports.

## Persistent memory and document store

Research records are stored in the configured SQLAlchemy database (`TAR_DATABASE_URL`, SQLite by default). Ingested documents retain source, title, URI, media type, SHA-256 digest, document ID, chunk ordering, page references where available, and ingestion metadata.

Repeated source retrievals update existing memory records and identical files are deduplicated by digest. Hybrid retrieval combines remembered source snippets and relevant document chunks before the model generates an answer.

## Safety and privacy

Do not place secrets, private medical records, personal identifiers, copyrighted bulk datasets, or confidential documents on public IPFS. Model-generated claims are not automatically facts: source records and provenance remain distinct from AI interpretations.

## Status

**Phase 3: durable ingestion and hybrid retrieval.** T.A.R. now retains research across requests and can absorb large PDFs and archival datasets into a searchable chunk store. Next work expands authenticated workspaces, autonomous tool execution, coding/data sandboxes, image/video/audio providers, richer provenance, and distributed node execution.

Image/video providers require valid credentials and supported APIs; T.A.R. does not ship fake provider endpoints.

## License

MIT

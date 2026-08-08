# T.A.R. — The Akashic Records

T.A.R. is an open, community-governed multimodal AI knowledge network designed to preserve, search, analyze, verify, create, and expand human knowledge while retaining source provenance.

## Capabilities

- Conversational AI and coding
- Retrieval-augmented generation (RAG)
- Persistent research memory backed by SQLAlchemy/SQLite
- Web and archive ingestion
- Wikipedia/Wikidata connectors
- Library of Congress connector
- National Archives catalog connector
- Dawes/Freedmen dataset ingestion foundation
- PDF/document/data processing
- Image/video provider interfaces
- IPFS-compatible artifact storage
- Blockchain governance foundation
- Source provenance and confidence metadata
- Docker-based local development

## Architecture

```text
Web UI -> FastAPI -> Orchestrator -> Model Provider
                    |-> Persistent Memory / Retrieval
                    |-> Source Connectors
                    |-> Artifact Storage
                    |-> Provenance Ledger
                    `-> Governance
```

Research now follows a memory-first flow: T.A.R. recalls stored evidence, optionally performs live source searches, persists new records, deduplicates them, and gives the model a combined evidence set.

## Quick start

1. Copy `.env.example` to `.env`.
2. Configure an LLM provider, or use the built-in development echo provider.
3. Run `docker compose up --build`.
4. API docs: `http://localhost:8000/docs`
5. Web app: `http://localhost:3000`

## API

- `GET /health` — service and memory status
- `POST /v1/ask` — answer using stored memory plus optional live research
- `POST /v1/search` — search configured archives and optionally persist results
- `POST /v1/memory/recall` — query persistent T.A.R. memory directly
- `GET /v1/memory/stats` — record counts by source

Example:

```bash
curl -X POST http://localhost:8000/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"Find primary-source material about Freedmen enrollment records","research":true}'
```

## Knowledge sources

Connectors are adapters. T.A.R. does not silently mirror entire third-party collections. It retrieves public/authorized records on demand, preserves citations and metadata, and can index permitted datasets supplied by operators.

Included adapters cover Wikipedia, Wikidata, Library of Congress, the U.S. National Archives catalog, and local CSV/JSON archival datasets such as properly sourced Dawes or Freedmen roll exports.

## Persistent memory

Research records are stored in the configured SQLAlchemy database (`TAR_DATABASE_URL`, SQLite by default). Records retain source, title, URL, evidence text, confidence, and creation time. Repeated retrievals update existing source records rather than blindly duplicating them.

The current recall implementation uses lightweight lexical relevance so the service works without downloading an embedding model. A vector backend can be layered on later without changing the API contract.

## Safety and privacy

Do not place secrets, private medical records, personal identifiers, copyrighted bulk datasets, or confidential documents on public IPFS. Model-generated claims are not automatically facts: source records and provenance remain distinct from AI interpretations.

## Status

**Phase 2: persistent memory and research orchestration.** The API now retains retrieved evidence across requests and can answer from combined memory + live sources. Upcoming work includes durable ingestion jobs, hybrid vector/keyword retrieval, document chunking, authenticated user workspaces, and richer multimodal providers.

Image/video providers require valid credentials and supported APIs; T.A.R. does not ship fake provider endpoints.

## License

MIT

# T.A.R. — The Akashic Records

T.A.R. is an open, community-governed multimodal AI knowledge network designed to preserve, search, analyze, verify, create, and expand human knowledge while retaining source provenance.

## Capabilities

- Conversational AI and coding
- Retrieval-augmented generation (RAG)
- Persistent semantic memory
- Web and archive ingestion
- Wikipedia/Wikidata connectors
- Library of Congress connector
- National Archives catalog connector
- Dawes/Freedmen dataset ingestion
- PDF/document/data processing
- Image/video provider interfaces
- IPFS-compatible artifact storage
- Blockchain governance foundation
- Source provenance and confidence metadata
- Docker-based local development

## Architecture

```text
Web UI -> FastAPI -> Orchestrator -> Model Provider
                    |-> Retrieval / Semantic Memory
                    |-> Source Connectors
                    |-> Artifact Storage
                    |-> Provenance Ledger
                    `-> Governance
```

## Quick start

1. Copy `.env.example` to `.env`.
2. Configure an LLM provider, or use the built-in development echo provider.
3. Run `docker compose up --build`.
4. API docs: `http://localhost:8000/docs`
5. Web app: `http://localhost:3000`

## Knowledge sources

Connectors are adapters. T.A.R. does not silently mirror entire third-party collections. It retrieves public/authorized records on demand, preserves citations and metadata, and can index permitted datasets supplied by operators.

Included adapters cover Wikipedia, Wikidata, Library of Congress, the U.S. National Archives catalog, and local CSV/JSON archival datasets such as properly sourced Dawes or Freedmen roll exports.

## Safety and privacy

Do not place secrets, private medical records, personal identifiers, copyrighted bulk datasets, or confidential documents on public IPFS. Model-generated claims are not automatically facts: source records and provenance remain distinct from AI interpretations.

## Status

Active development. This repository is a production-oriented foundation, not a claim that every external model/provider is bundled or free. Image/video providers require valid credentials and supported APIs.

## License

MIT

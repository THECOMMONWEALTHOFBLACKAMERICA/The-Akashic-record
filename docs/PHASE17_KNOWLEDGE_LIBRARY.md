# Phase 17 — Current Knowledge and Research Library

## EPUB

T.A.R. ingests EPUB archives by reading `META-INF/container.xml`, resolving the OPF package, following the manifest/spine, extracting common Dublin Core metadata and converting readable XHTML/HTML chapters to plain text. Scripts/styles are discarded and no embedded remote content is executed.

## Current web

`TAR_SEARXNG_URL` enables current-web metasearch through an operator-controlled SearXNG instance. Results retain URL, title, snippet, optional publication date and engine provenance. If SearXNG is not configured, T.A.R. continues using archive and knowledge connectors without pretending live-web coverage exists.

## Research library

Each workspace can attach private reading state to an ingested document:

- favorite flag
- progress from 0.0 to 1.0
- flexible locator JSON (chapter/page/section/etc.)
- research notes

Endpoints are mounted at `/v1/library` in the production app.

## Migration authority

Production PostgreSQL schema changes are owned by Alembic. `TAR_AUTO_SCHEMA_BOOTSTRAP=auto` preserves convenient automatic setup only for SQLite development. Alembic sets `TAR_MIGRATION_CONTEXT=1` while discovering model metadata, preventing historical import-time table creation or legacy repair logic from mutating the target database before migrations run.

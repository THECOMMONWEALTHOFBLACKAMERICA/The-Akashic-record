# T.A.R. Production Runbook

## Purpose

This runbook defines the minimum operational discipline for a production T.A.R. deployment. Production uses PostgreSQL/Alembic as the schema authority, authenticated workspaces, separate administrative/worker trust boundaries, durable artifact storage, health/readiness probes, monitoring and tested backups.

## Required production configuration

Set `TAR_ENV=production`. The production application validates its configuration and refuses to start with several unsafe defaults.

Required baseline:

- `TAR_DATABASE_URL`: PostgreSQL DSN.
- `TAR_AUTO_SCHEMA_BOOTSTRAP=false`.
- `TAR_REQUIRE_API_KEY=true`.
- `TAR_ADMIN_KEY`: strong secret stored in a secret manager.
- `TAR_WORKER_KEY`: separate strong worker secret.
- `TAR_ALLOWED_ORIGINS`: explicit HTTPS origins; never `*`.
- `TAR_ENABLE_CODE_EXECUTION=false` on API hosts.
- durable artifact storage. S3-compatible storage is preferred for independent/multi-host workers.
- provider credentials only for capabilities actually enabled.

Optional systems:

- `TAR_SEARXNG_URL` for current-web research. The repository includes `compose.websearch.yml` for a localhost development SearXNG service.
- semantic embedding model/settings for semantic reranking.
- NARA/NCBI configuration for those archive APIs.
- image/video/transcription provider configuration.
- blockchain RPC/governance contract configuration.
- public IPFS publication only when explicitly intended.

## Deployment sequence

1. Provision PostgreSQL with encryption, restricted networking and automated snapshots.
2. Provision durable S3-compatible/object artifact storage if workers will run on different hosts.
3. Create admin, worker, database and provider secrets in the platform secret manager.
4. Set `TAR_ENV=production`, API authentication, HTTPS origins and code execution off.
5. Run `alembic upgrade head` before application traffic.
6. Deploy the API and require `/ready` before routing traffic.
7. Deploy worker pools with least-privilege credentials and explicit capabilities.
8. Create the first workspace/API key through the admin API.
9. Configure optional model/archive/media/current-web providers.
10. Inspect `/v1/system/providers`, `/v1/system/capabilities` and `/v1/system/storage`.
11. Run `python scripts/smoke_test.py` against the target environment.
12. Enable external traffic only after smoke validation succeeds.

## Current-web service

For a developer-owned SearXNG instance:

```bash
docker compose -f docker-compose.yml -f compose.websearch.yml up --build
```

The supplied override binds SearXNG to localhost. Replace the example SearXNG secret and apply normal ingress/security controls before a networked deployment.

## Artifact storage

A database-only backup is incomplete because artifact records reference external bytes.

For horizontally distributed workers use the S3-compatible backend rather than a host-local artifact directory. The repository MinIO profile is for development/testing; production may use AWS S3 or a compatible private object store.

Public IPFS is **not** private object storage. Do not publish sensitive material to public IPFS. Public publication is an explicit admin action and should remain disabled unless deliberately required.

## PostgreSQL backup

Example logical backup:

```bash
pg_dump --format=custom --no-owner --file=tar.dump "$TAR_DATABASE_URL"
```

Store backups encrypted outside the primary environment and maintain a tested retention policy.

## Restore drill

1. Create an isolated PostgreSQL instance.
2. Restore the database with `pg_restore`.
3. Restore artifact/object storage into an isolated location/bucket.
4. Point a disposable T.A.R. deployment at the restored resources.
5. Run `alembic upgrade head` if required by the target version.
6. Verify `/ready` and workspace authentication.
7. Verify the audit chain.
8. Retrieve historical artifacts and confirm SHA-256 integrity.
9. Run hybrid recall against known ingested documents.
10. Run the full smoke test, including library and bounded-agent paths.
11. Record recovery time and manual steps.

A backup is not considered operationally valid until restored successfully.

## Incident response

### Workspace API-key compromise

- revoke/rotate the affected credential;
- inspect workspace audit events;
- preserve relevant logs/snapshots;
- rotate downstream provider credentials if exposure is possible.

### Administrative secret compromise

Treat as critical. Rotate `TAR_ADMIN_KEY`, restrict administrative ingress, inspect workspace/API-key creation events and redeploy with the new secret.

### Worker secret/node compromise

Rotate `TAR_WORKER_KEY`, remove the affected node, preserve its environment for investigation, inspect leased jobs and discard outputs that cannot be trusted.

### Database outage

Stop write traffic when consistency is uncertain. Recover PostgreSQL from platform failover or the latest verified backup. Never silently fall back to SQLite in production.

### Artifact-store failure

Stop workflows that create artifacts if durable persistence is unavailable. Do not claim successful artifact creation when metadata exists but object bytes cannot be verified.

## Monitoring

Prometheus metrics are exposed at `/metrics` through the production application wrapper. The Compose `monitoring` profile includes a local Prometheus deployment.

Alert on:

- `/ready` failures;
- elevated 5xx rate or latency;
- authentication failures/spikes;
- queue age/retry growth;
- worker heartbeat loss;
- PostgreSQL connection/storage pressure;
- artifact storage errors/capacity;
- external provider latency/error rates;
- current-web/search-provider failures when that capability is advertised;
- audit-chain verification failures.

## Release discipline

The source-of-truth version is `VERSION` and must match `backend/app/version.py`.

The release candidate checklist is [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). CI validates source compilation, frontend syntax, PostgreSQL migration round-trip/drift, tests, live API+worker smoke paths, governance contracts, Compose configuration and container builds.

Tag releases as `v<VERSION>`. The release workflow rejects mismatched tags and re-runs migration/tests/live smoke qualification before publishing the GHCR image and provenance attestation.

Do not promote `1.0.0-rc.1` to stable `1.0.0` until the actual production environment has completed the environment-specific release checklist, including backup/restore and configured-provider validation.

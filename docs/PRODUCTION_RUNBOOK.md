# T.A.R. Production Runbook

## Purpose

This runbook defines the minimum operational discipline for a production T.A.R. deployment. Production must use PostgreSQL, isolated workers for executable workloads, explicit secrets, health/readiness probes, durable artifact storage, and tested backups.

## Required production configuration

- `TAR_DATABASE_URL`: PostgreSQL DSN. Do not use SQLite for multi-node production.
- `TAR_ADMIN_KEY`: long random administrative secret stored in a secret manager.
- Workspace API keys: create them through the administrative API and require them for network-accessible deployments.
- `TAR_ALLOWED_ORIGINS`: explicit HTTPS origins; never `*` for credentialed production traffic.
- `TAR_ARTIFACT_DIR`: durable mounted storage or replace the artifact backend with object storage.
- Provider credentials: configure only providers actually enabled.
- `TAR_ENABLE_CODE_EXECUTION=false` on the API service. Executable workloads belong only on sandboxed worker infrastructure.

## Deployment sequence

1. Provision PostgreSQL with encrypted storage and automated snapshots.
2. Provision durable artifact/object storage.
3. Create application and admin secrets in the platform secret manager.
4. Run `alembic upgrade head` before starting application traffic.
5. Deploy the API with code execution disabled.
6. Wait for `/health`, then require `/ready` to succeed before routing traffic.
7. Deploy workers separately with least-privilege credentials and explicit capability lists.
8. Bootstrap the first workspace/API key through the admin interface.
9. Configure optional archive/model/media providers and check `/v1/system/providers`.
10. Run `python scripts/smoke_test.py` against the deployment.
11. Enable external traffic only after smoke tests pass.

## Backup

Back up both the database and artifact store. A database-only backup is incomplete because artifact rows reference external bytes.

### PostgreSQL

Example logical backup:

```bash
pg_dump --format=custom --no-owner --file=tar.dump "$TAR_DATABASE_URL"
```

Store the dump encrypted outside the primary environment. Keep daily backups and at least one longer-term retention tier.

### Artifacts

Snapshot or replicate the directory/object-store prefix configured for T.A.R. Preserve object keys exactly because database records reference artifact identifiers and hashes.

## Restore drill

A backup is not considered valid until restored.

1. Create an isolated PostgreSQL instance.
2. Restore `tar.dump` with `pg_restore`.
3. Restore the artifact snapshot into an isolated artifact location.
4. Point a disposable T.A.R. deployment at both restored resources.
5. Verify `/ready`.
6. Verify workspace authentication and audit-chain verification.
7. Retrieve several historical artifacts and compare their SHA-256 values.
8. Run hybrid recall against known ingested documents.
9. Run the full smoke test.
10. Record the recovery time and any manual repair required.

Perform this drill regularly and after schema/storage changes.

## Incident response

### Suspected API-key compromise

- Revoke/rotate the affected key.
- Inspect workspace-scoped audit events.
- Rotate provider credentials if exposed downstream.
- Preserve logs and database snapshots for investigation.

### Admin-key compromise

Treat as critical. Rotate `TAR_ADMIN_KEY` immediately, restrict ingress to administrative routes, inspect workspace/key creation events and redeploy services with the new secret.

### Worker compromise

Remove the node from service, revoke its credentials, preserve the container/VM for investigation, inspect jobs leased to that node and requeue only jobs whose outputs cannot be trusted.

### Database outage

Stop write traffic if consistency cannot be guaranteed. Restore service from the database platform or the latest verified backup. Do not silently fall back to a local SQLite database.

## Monitoring

Prometheus metrics are available at `/metrics` on the production application wrapper. The Compose `monitoring` profile supplies a local Prometheus configuration.

Alert on:

- `/ready` failures
- elevated 5xx rate or latency
- authentication failures/spikes
- job queue age and repeated retries
- worker heartbeat loss
- PostgreSQL connection exhaustion/storage pressure
- artifact storage errors/capacity
- provider latency/error rates
- audit-chain verification failures

## Release discipline

Every production release should have a tagged commit, migration/build validation, live smoke test, rollback target, changelog and container digest. Tag pushes matching `v*` produce a GHCR image and provenance attestation through the release workflow. Never deploy directly from an unreviewed feature branch.

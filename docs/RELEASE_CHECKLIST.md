# T.A.R. 1.0 Release Qualification Checklist

This checklist distinguishes **code readiness** from **environment readiness**. A commit can be release-qualified without possessing third-party credentials; a production deployment cannot claim a provider capability until the corresponding real endpoint and credentials are configured and tested.

## Source and build

- [ ] `VERSION` matches `backend/app/version.py`.
- [ ] Python sources compile.
- [ ] Frontend JavaScript passes syntax validation.
- [ ] Docker image builds from the reviewed commit.
- [ ] Docker Compose base configuration validates.
- [ ] Current-web Compose override validates.
- [ ] No `.env`, database, artifact data, credentials or local model cache is included in the image context.

## Database

- [ ] Fresh PostgreSQL database upgrades to Alembic head.
- [ ] Latest migration can downgrade one revision and return to head.
- [ ] `alembic check` reports no ORM/schema drift.
- [ ] Production model imports do not create or repair schema outside Alembic.
- [ ] Restore drill has been performed against the target production storage stack.

## Core product smoke test

- [ ] health endpoint succeeds.
- [ ] readiness endpoint succeeds.
- [ ] capability endpoint reflects actual configuration.
- [ ] question path responds without fabricated provider output.
- [ ] source document ingests.
- [ ] ingested marker is retrievable.
- [ ] research-library state persists.
- [ ] bounded agent run completes and history persists.
- [ ] PDF artifact is generated and integrity-valid on retrieval.
- [ ] audit chain verifies.
- [ ] distributed worker accepts and completes a compatible job.

## Security

- [ ] `TAR_ENV=production` is set on production API instances.
- [ ] PostgreSQL is used.
- [ ] workspace API authentication is required.
- [ ] admin and worker secrets are strong, distinct and secret-manager backed.
- [ ] TLS terminates before the API and allowed origins are explicit HTTPS origins.
- [ ] arbitrary code execution is disabled on API hosts.
- [ ] high-risk worker pools have no ambient cloud/admin credentials.
- [ ] IPFS API is not publicly exposed.
- [ ] public IPFS publication remains disabled unless intentionally required.
- [ ] sensitive artifacts use encrypted private storage and are never accidentally published to public IPFS.

## Knowledge providers

Validate only providers that the deployment intends to advertise:

- [ ] LLM endpoint/model
- [ ] image generation
- [ ] image editing
- [ ] video generation
- [ ] transcription
- [ ] NARA API v2
- [ ] NCBI identity/API configuration if higher-rate usage is required
- [ ] SearXNG current-web search if enabled
- [ ] semantic embedding model if enabled

Missing optional providers must be reported as unavailable, not silently substituted with fictional results.

## Distributed infrastructure

- [ ] worker capability lists match deployed worker pools.
- [ ] PostgreSQL is reachable by API/workers over private networking.
- [ ] S3-compatible artifact storage is shared by independently hosted workers when horizontal distribution is required.
- [ ] object lifecycle/backups are configured.
- [ ] node heartbeats and queue latency are monitored.

## Governance

If governance is enabled:

- [ ] contract tests pass.
- [ ] intended chain/RPC is verified.
- [ ] deployed contract bytecode/address are recorded.
- [ ] voting power, quorum and timelock are reviewed.
- [ ] administrator/guardian keys use the intended custody model.
- [ ] downstream executors verify approved action hashes before applying governed changes.

## Operations

- [ ] `/ready` alerting configured.
- [ ] 5xx/authentication/queue/provider error alerts configured.
- [ ] PostgreSQL backup configured and restoration tested.
- [ ] artifact-store backup/versioning configured and restoration tested.
- [ ] incident contacts and credential-rotation procedure documented.
- [ ] rollback target identified before release.

## Tagging

A release tag must be exactly `v<VERSION>` (for this candidate: `v1.0.0-rc.1`). The repository release workflow revalidates migrations, tests and the live API/worker smoke path before publishing a GHCR container and provenance attestation.

Do not promote the release candidate to stable `1.0.0` until the target production environment has completed the environment-specific items above.

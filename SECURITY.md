# T.A.R. Security Model

T.A.R. treats every model, node, external source, uploaded file and provider response as untrusted input.

## Production requirements

- Require workspace API authentication for network-accessible deployments.
- Set a strong, unique `TAR_ADMIN_KEY`; administrative APIs fail closed when it is absent.
- Set a separate strong `TAR_WORKER_KEY` if remote worker HTTP endpoints are enabled.
- Use PostgreSQL with a strong password and a secret manager. Never commit `.env` files.
- Put the API behind TLS and an ingress/reverse proxy with request-size and rate limits.
- Do not expose the IPFS API port publicly.
- Keep executable-code support disabled in the API process.
- Use separate credentials for model/media/archive providers and rotate them when compromised.
- Encrypt sensitive source data at rest and before any external/public storage. Never place private records on public IPFS.

## Trust boundaries

1. **Client/API traffic** — authenticated and scoped to a workspace.
2. **Administrative API** — independently protected and never exposed through browser credentials.
3. **Remote worker API** — independently protected by `TAR_WORKER_KEY`; ordinary workspace credentials cannot lease or complete arbitrary jobs.
4. **Workers/nodes** — execute explicit capabilities and must be isolated according to risk.
5. **Executable-code sandbox** — separate from ordinary workers; disposable, resource-limited, no ambient host/cloud secrets, restricted filesystem and networking.
6. **External providers** — model, media, archive and RPC endpoints are untrusted dependencies.
7. **Storage** — PostgreSQL stores control-plane state; artifact bytes live in durable storage and are verified with SHA-256.
8. **Governance** — on-chain proposals govern protocol-level changes; ordinary inference does not require blockchain transactions.

## Workspace isolation

Memory, documents, chunks, ingestion jobs, queued-job visibility, artifacts and retrieval are workspace-scoped. New storage features must preserve this boundary. Cross-workspace access is a security defect.

## Executable workloads

`TAR_ENABLE_CODE_EXECUTION` must remain false on API hosts. Enabling the helper is appropriate only inside a hardened sandbox. The built-in subprocess isolation is defense-in-depth, not a complete hostile-code sandbox.

## Distributed jobs

PostgreSQL workers lease jobs with row locking to prevent concurrent workers from claiming the same task. Job-status access remains scoped to the owning workspace. Remote lease/complete/fail HTTP endpoints require the worker secret and should be restricted at the network layer as well.

## Audit integrity

Audit events are chained per workspace and `/v1/audit/verify` verifies the stored chain. This provides tamper evidence, not proof that underlying research claims are true. Provenance and independent corroboration remain necessary.

## Supply chain

- Pin/review production dependencies and run dependency scanning in CI.
- Build deployable images from reviewed commits/tags.
- Never commit provider tokens, private keys, database passwords, worker keys or admin credentials.
- Rotate a credential immediately if it is accidentally committed, even when the commit is later removed.

## Reporting vulnerabilities

Do not publish credentials, private user data or exploit instructions against live installations in public issues. Use GitHub private vulnerability reporting/security advisories when available. Include the affected component, safe reproduction conditions, impact and relevant sanitized logs.

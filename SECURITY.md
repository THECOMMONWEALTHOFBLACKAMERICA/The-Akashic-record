# T.A.R. Security Model

T.A.R. is experimental infrastructure. Treat every model, node, external source, uploaded file, and provider response as untrusted input.

## Production requirements

- Set `TAR_REQUIRE_API_KEY=true` for network-accessible deployments.
- Set a strong, unique `TAR_ADMIN_KEY`; administrative APIs fail closed when it is absent.
- Set a strong `TAR_POSTGRES_PASSWORD` and do not commit `.env` files.
- Put the API behind TLS and a reverse proxy with request-size and rate limits.
- Do not expose the IPFS API port (`5001`) publicly.
- Keep code execution disabled in the API process. If enabled on a worker, isolate that worker with a container/VM sandbox, resource limits, no host secrets, and restricted network/filesystem access.
- Use separate credentials for model/media providers and rotate them when compromised.
- Encrypt sensitive source data before external storage. Do not place private records on public IPFS.

## Trust boundaries

1. **Public/user API** — authenticated by optional T.A.R. API keys.
2. **Administrative API** — independently protected by `X-TAR-Admin-Key`.
3. **Workers/nodes** — execute queued capabilities and should be isolated according to risk.
4. **External providers** — model, media, archive, and RPC endpoints are untrusted dependencies.
5. **Storage** — PostgreSQL stores control-plane state; artifacts are content-addressed with SHA-256 provenance.
6. **Governance** — on-chain proposals govern protocol-level changes; ordinary inference does not require a blockchain transaction.

## Audit integrity

Audit events are chained per workspace. `/v1/audit/verify` verifies the stored chain. This provides tamper evidence, not magical immutability; anchoring audit heads to a public chain can be added for stronger external verification.

## Reporting vulnerabilities

Do not publish credentials, exploit payloads against live installations, or private user data in public issues. Report enough information to reproduce the defect safely and rotate affected secrets immediately.

# T.A.R. Foundational Citizenship Commission Case Engine

## Purpose

This subsystem implements the operational rules in `docs/TAR-CITIZENSHIP-COMMISSION-INTEGRATION.md`. It is a research, evidence-management and audit system. It does not make citizenship determinations.

## Authentication and case isolation

All `/v1/commission/*` routes require an authenticated T.A.R. API key even when the general API is running in development mode with anonymous access enabled.

Each API key has a stable `key_id`. Commission cases grant access to specific key IDs with one of these roles:

- `owner` — full case/control access;
- `commissioner` — full case/control access;
- `staff` — research and evidence-writing access, but no access-management/legal-hold/final-disposition authority;
- `reviewer` — evidence review and research/write access, but no access-management authority;
- `readonly` — read/export only.

A key with access to one case receives no implicit access to another case in the same workspace.

## Case API

- `POST /v1/commission/cases` — create case; caller becomes owner.
- `GET /v1/commission/cases` — list only cases available to the caller's key.
- `PATCH /v1/commission/cases/{case_id}` — update case state/research mode/retention/hold according to role.
- `GET /v1/commission/cases/{case_id}/export` — export case and evidence record.
- `DELETE /v1/commission/cases/{case_id}` — policy-authorized retention deletion; owner/commissioner only and blocked by legal hold.

## Case access API

- `POST /v1/commission/cases/{case_id}/access`
- `GET /v1/commission/cases/{case_id}/access`
- `DELETE /v1/commission/cases/{case_id}/access/{key_id}`

Only owners/commissioners may manage case grants.

The administrative API-key creation response includes `key_id`; that identifier is used when granting a Commission case role. Raw API keys are never stored in Commission case records.

## Evidence API

- `POST /v1/commission/cases/{case_id}/evidence` — add structured evidence metadata.
- `POST /v1/commission/cases/{case_id}/evidence/upload` — store original protected bytes plus chain-of-custody metadata.
- `GET /v1/commission/cases/{case_id}/evidence` — retrieve evidence records.
- `PATCH /v1/commission/evidence/{evidence_id}/review` — human review, status assignment and optional tier correction.

Evidence statuses are `verified`, `corroborated`, `conflicting`, `unverified`, `insufficient`, and `excluded`. Excluded evidence requires a reason.

Uploaded originals record SHA-256, filename, uploader, claimed provenance, media type, protected artifact ID and storage backend. Original bytes are stored as artifacts classified `commission_original_evidence` with `public_ipfs_allowed=false`.

## Public IPFS prohibition

The public-IPFS publication layer inspects artifact classification before publishing. Artifacts marked `commission_original_evidence` or `public_ipfs_allowed=false` are rejected even when an administrator acknowledges immutable/public publication.

This is a defense-in-depth control. Commission operators must also keep `TAR_ENABLE_PUBLIC_IPFS=false` for applicant-material environments as required by the integration specification.

## Restricted research

`POST /v1/commission/cases/{case_id}/research` searches workspace-ingested material and official/purpose-built archival connectors first. The default remote connector set is NARA, Library of Congress and the Freedmen research strategy. Dawes/Final Rolls research is opt-in per query.

General web, Wikipedia and Wikidata are not used in restricted mode unless `broaden_web=true` is explicitly supplied, or the case's restricted-research setting has been deliberately disabled.

Retrieved results are persisted as `unverified` evidence when requested. Initial source tiers are only a classification aid and may be corrected during human review. Repeated identical research results are deduplicated against existing case evidence.

## Retention and legal holds

A legal hold blocks case deletion. Policy-authorized deletion collects referenced original/derived artifact IDs, deletes the case/evidence transaction, removes protected artifact metadata/bytes, revokes case grants and returns any artifact-cleanup failures explicitly. An incomplete artifact cleanup must be remediated; the system does not silently report a fully completed deletion.

## Authority boundary

Case status fields support Commission workflows, but T.A.R. itself does not determine eligibility. Final approval/denial authority remains with the Commission under the governing Citizenship Code and Constitution. The software specification yields to those governing instruments if they conflict.

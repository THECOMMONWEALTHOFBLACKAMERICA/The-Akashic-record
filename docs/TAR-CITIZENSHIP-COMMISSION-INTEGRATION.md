# T.A.R. — Foundational Citizenship Commission Integration Specification

**Status:** Implementation specification
**Applies to:** Commonwealth Foundational Citizenship Commission workflows and T.A.R.

## 1. Purpose

T.A.R. may be used as a research and evidence-organization tool in support of the Foundational Citizenship Commission. It supports the Commission; it does not replace it.

T.A.R. may retrieve, organize, cross-reference, summarize, and flag gaps in historical records relevant to a claimed lineage. It must not be the sole basis for approval, denial, or a request-for-more-evidence determination. Every T.A.R.-assisted finding entered into a case record must retain source citations, retrieval metadata, and the underlying evidence reference.

## 2. Authority boundary

The Commission remains the decision-maker. T.A.R. is an evidentiary research system and case-management aid. Generated summaries are not themselves primary evidence and must remain auditable against underlying sources.

T.A.R. project governance is separate from Commonwealth civic governance and elections. T.A.R.'s software governance contract must not implicitly control citizenship determinations or Commonwealth voting.

## 3. Evidence model

Each evidence item should carry a source tier and an evidence status.

### Source tiers

- **Tier 1:** federal/state census, vital records, Freedmen's Bureau records, emancipation records, land/probate/court records and comparable primary governmental records.
- **Tier 2:** military/pension records, newspapers, published genealogies and other corroborating documentary sources.
- **Tier 3:** DNA corroboration, oral history and other supporting evidence handled under the Commission's governing rules.

T.A.R. retrieval never upgrades the legal/evidentiary tier of a source.

### Evidence statuses

- `verified` — underlying record has been reviewed and supports the stated fact.
- `corroborated` — multiple independent sources support the stated fact but the item is not treated as conclusive primary proof.
- `conflicting` — material sources disagree and require human resolution.
- `unverified` — retrieved or submitted information has not yet been independently reviewed.
- `insufficient` — evidence does not establish the fact for which it was offered.
- `excluded` — item is retained for audit/history but excluded from the Commission's evidentiary analysis, with a recorded reason.

Automated confidence scores must not replace these human-review statuses.

## 4. Source mapping

T.A.R.'s NARA connector and Freedmen research strategy are strong fits for Tier 1 research. Operator-supplied PDFs, Office documents, CSV/JSON datasets and archival records may supplement incomplete online coverage. The Dawes/Final Rolls strategy is used only when relevant to the documented lineage and is not a substitute for the governing foundational-lineage standard.

NARA military/pension material may support Tier 2 research. General current-web metasearch, Wikipedia and Wikidata are corroborating discovery tools and should not be treated as Tier 1 evidence merely because T.A.R. retrieved them.

## 5. Commission tenancy and case isolation

Use a dedicated Commission tenant with case-level isolation:

```text
Commission tenant
  ├── Case / Application A
  ├── Case / Application B
  ├── Case / Application C
  └── Shared vetted historical reference corpus
```

Applicant evidence must remain isolated by case. The shared reference corpus may contain approved non-applicant-specific historical material such as census guides, archival finding aids, roll indexes, maps and vetted public-domain reference works.

No case may retrieve another case's applicant documents, notes, artifacts, memory or audit data.

## 6. Restricted Commission research mode

Commission case workspaces should default to a restricted research profile:

1. Search the case's submitted evidence and vetted Commission corpus first.
2. Prefer official archival/government connectors such as NARA and Library of Congress.
3. Use purpose-built Freedmen/Dawes strategies where relevant.
4. General web/Wikipedia/Wikidata results are disabled or strongly demoted by default.
5. Broad-web research requires an intentional operator action and remains corroborating/discovery evidence unless the underlying primary source is independently obtained.

## 7. Chain of custody

Every applicant-uploaded document must retain at minimum:

- original filename;
- SHA-256 of original bytes;
- uploader identity or service principal;
- upload timestamp;
- applicant-claimed source/provenance when supplied;
- MIME/media type;
- case/workspace identifier;
- transformations performed by T.A.R.;
- hashes and identifiers of derived artifacts;
- reviewer status and material notes.

The original bytes must remain distinguishable from extracted text, OCR output, summaries, annotations and generated reports.

## 8. Confidentiality and publication

Applicant genealogical evidence is protected case data. Public IPFS/decentralized publication must remain disabled for Commission case workspaces. Applicant evidence must never be published to public IPFS as part of an automated workflow.

Access to Commission case workspaces must be limited to authorized Commissioners and designated staff operating under the applicable confidentiality rules. Production deployment must satisfy `SECURITY.md` and `docs/PRODUCTION_RUNBOOK.md` before real applicant material is ingested.

Workspace audit chains and artifact SHA-256 verification should be retained so the Commission can reconstruct what was received, retrieved, transformed and reviewed during a determination or appeal.

## 9. Retention and deletion

Retention is policy-driven rather than decided by the AI. The Commission must configure retention periods for approved, denied, withdrawn, incomplete and appealed applications under its governing records rules.

Until a formal retention schedule is adopted:

- T.A.R. must not automatically destroy Commission case records;
- deletion requires authorized administrative action;
- deletion must generate an audit event identifying the case, actor, policy basis and categories removed;
- legal/appeal holds override ordinary deletion schedules;
- public-IPFS publication is prohibited because effective deletion cannot be guaranteed there.

## 10. Recommended workflow

1. Applicant submits the Foundational Citizenship Application and supporting documentation.
2. Authorized staff creates an isolated case inside the Commission tenant.
3. Original evidence is hashed and chain-of-custody metadata is recorded before transformation.
4. T.A.R. retrieves and organizes corroborating records using the restricted Commission research profile.
5. T.A.R. records source tier, citations, retrieval metadata and an initial `unverified` status.
6. A Commissioner reviews the underlying evidence and assigns the appropriate evidence status.
7. The Commissioner makes the actual determination under the governing Citizenship Code.
8. The case audit chain and determination record are retained under the applicable retention schedule and appeal rules.
9. The case is never automatically published to IPFS or another public store.

## 11. Implementation requirements

The T.A.R. implementation should provide:

- Commission tenant/case identifiers and strict case authorization;
- evidence records with tier/status/source metadata;
- immutable original-upload hash metadata;
- transformation/derived-artifact lineage;
- restricted-source research profile;
- reviewer actions separated from autonomous-agent actions;
- retention/legal-hold metadata and audited deletion;
- case-level export suitable for Commission review and appeal records;
- explicit prohibition on public publication for Commission cases.

## 12. Governing-document priority

This specification is operational guidance and software architecture, not a modification to the Citizenship Code or Constitution. Where this specification conflicts with an applicable governing document, the governing document controls.

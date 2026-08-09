# T.A.R. Knowledge Sources

T.A.R. treats external records as evidence with provenance, not as model truth. Source adapters should preserve the originating institution, URL/identifier, retrieval metadata, and confidence separately from generated interpretation.

## Included connectors

### Wikipedia / Wikidata
Useful for orientation, entity discovery, aliases, and links. These are not treated as primary historical evidence.

### Library of Congress
Uses the public loc.gov JSON API. No API key is required, but rate limits apply. T.A.R. preserves the LOC item URL and available metadata. The loc.gov API does not represent every catalog record, so lack of a result is not proof that the Library lacks a record.

### National Archives Catalog
Uses the current Catalog API v2 at `https://catalog.archives.gov/api/v2/records/search`. A NARA API key is required and must be supplied as `TAR_NARA_API_KEY`. Do not commit the key.

Required attribution for applications using the Catalog API:

> This product uses the National Archives Catalog API but is not endorsed or certified by the National Archives and Records Administration.

T.A.R. must respect NARA rate limits and terms. Do not attempt to mirror the full Catalog through repeated search calls; use NARA's published bulk/open-data mechanisms when bulk research is legitimately required.

### Dawes / Final Rolls research
`source=dawes` is a research strategy, not a fabricated standalone API. It searches authoritative NARA material (when configured) and Library of Congress material using terminology associated with the Dawes Commission, Final Rolls, and Five Tribes. Operators can also ingest lawfully obtained roll exports, scans, PDFs, CSVs, or transcriptions directly into T.A.R.

Every genealogy conclusion should retain the exact roll/card/application identifiers and underlying record image or archive citation where available.

### Freedmen records research
`source=freedmen` searches configured NARA and Library of Congress sources using Freedmen's Bureau/Freedmen record terminology. It is deliberately broader than any one index because Freedmen-era material spans multiple record groups, jurisdictions, agencies, formats, and repositories.

Do not infer identity, tribal citizenship, or family relationships solely from fuzzy name similarity. Preserve dates, locations, ages, household relationships, roll numbers, collection identifiers, and conflicting evidence.

### PubMed / NCBI
Uses NCBI Entrez E-utilities. `TAR_NCBI_EMAIL` identifies the application/operator and `TAR_NCBI_API_KEY` can be supplied for higher authorized rate limits. PubMed search results are bibliographic evidence; medical answers should distinguish published findings, reviews, guidelines, and inference.

## Local archival datasets

T.A.R. accepts PDF, TXT/MD, CSV, and JSON imports. For local archival data, use a stable `source` label and fill `source_uri` with the institution URL, catalog identifier, archival citation, or acquisition record whenever possible.

Recommended provenance fields:

- repository/institution
- collection or record group
- series/title
- box/folder or roll/card/application number
- item/NAID/call number
- date
- jurisdiction/location
- source URL
- transcription status
- image availability
- retrieval date

## Source hierarchy

For disputed factual claims, prefer:

1. original/primary records and images
2. official archival descriptions and government databases
3. peer-reviewed research and authoritative reference works
4. curated secondary sources
5. general encyclopedias
6. unsourced web material

T.A.R. should surface disagreement rather than silently average conflicting records into a single claim.

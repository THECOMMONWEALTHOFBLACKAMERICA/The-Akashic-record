# IPFS Publication and Provenance

T.A.R. treats private artifact storage and public IPFS publication as different operations.

## Default behavior

`TAR_ENABLE_PUBLIC_IPFS=false` by default. Merely running an IPFS daemon does not publish T.A.R. artifacts.

The publication API is administrative and requires an explicit request field acknowledging that IPFS content may become public and difficult to retract. This is intentional protection against accidentally publishing private genealogy, identity, health, financial, or other sensitive records.

## Publication record

When an artifact is intentionally published, T.A.R. pins:

1. the artifact bytes;
2. a canonical JSON provenance manifest.

The manifest binds the artifact CID to:

- T.A.R. artifact ID
- workspace ID
- filename/media type
- SHA-256
- byte size
- T.A.R. version
- publication timestamp

T.A.R. then stores the artifact CID, manifest CID and SHA-256 in PostgreSQL and writes an audit event.

## API

After enabling public IPFS publication, an administrator can call:

`POST /v1/admin/publications/ipfs`

with an artifact ID, workspace ID and `acknowledge_public_immutable_storage=true`.

Publication is deduplicated for an already published artifact. Existing publication records can be listed by workspace through the administrative publication endpoint.

## What this proves

A CID proves content addressing: the same content maps to the same content identifier under the selected IPFS representation. The manifest and SHA-256 allow T.A.R. to tie the public bytes back to its own artifact/provenance record.

This does **not** prove that the underlying historical claim, AI output, image, or document is true. Provenance answers “what bytes were published, when, and from which T.A.R. record?” Truth still depends on source quality and independent verification.

## Retraction

Pinned content can be unpinned from a local node, but another participant may already have replicated it. T.A.R. therefore does not provide a misleading “delete from IPFS everywhere” control.

Never publish material that depends on guaranteed future deletion.

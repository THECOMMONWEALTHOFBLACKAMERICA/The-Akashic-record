# Artifact Storage

T.A.R. separates artifact metadata from artifact bytes. PostgreSQL records workspace ownership, SHA-256, media type and the storage URI; bytes can live on the local filesystem or an S3-compatible object store.

## Local backend

Use for development or a single host:

```env
TAR_ARTIFACT_BACKEND=local
TAR_ARTIFACT_DIR=./artifacts
```

The local backend keeps each workspace in a separate directory and rejects reads that escape the configured artifact root.

## S3-compatible backend

Use for multiple API/worker machines:

```env
TAR_ARTIFACT_BACKEND=s3
TAR_S3_BUCKET=tar-artifacts
TAR_S3_REGION=us-east-1
TAR_S3_PREFIX=tar-artifacts
```

For AWS, leave `TAR_S3_ENDPOINT_URL` blank and prefer workload/instance identity over static keys when the deployment platform supports it.

For MinIO or another compatible service, configure:

```env
TAR_S3_ENDPOINT_URL=http://minio:9000
TAR_S3_ACCESS_KEY_ID=...
TAR_S3_SECRET_ACCESS_KEY=...
TAR_S3_ADDRESSING_STYLE=path
```

The bucket must already exist. The optional Docker Compose `distributed-storage` profile starts MinIO plus a one-shot initializer that creates a private bucket.

## Integrity

Every artifact is hashed before storage. On retrieval T.A.R. recalculates SHA-256 and refuses to serve bytes whose digest no longer matches database metadata.

A successful object upload followed by a failed database commit is rolled back by deleting the new object. Storage deletion failure during this rollback should be monitored as a potential orphan-object event.

## Migration

The database column historically called `path` may contain either a filesystem path or an `s3://bucket/key` URI. This preserves compatibility with older installations.

Switching `TAR_ARTIFACT_BACKEND` affects **new writes**. Legacy local artifacts remain readable only where their original filesystem data is still mounted. For a full migration:

1. back up PostgreSQL and the artifact directory;
2. copy legacy artifact bytes to the target object store;
3. update each artifact metadata URI only after verifying its SHA-256;
4. verify representative downloads through the API;
5. retire the local copy only after a restore test.

A dedicated bulk migration command can be added when an installation actually needs to migrate existing production data; automatic silent migration is intentionally avoided.

## Privacy

S3 buckets and MinIO buckets should be private. Client access goes through authenticated T.A.R. endpoints unless a deployment deliberately implements signed URLs. Public IPFS publication is a separate opt-in concern and should never be implied by using S3 storage.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class StorageError(RuntimeError):
    pass


class ArtifactStorage:
    name = "unknown"

    def put(self, workspace_id: str, key: str, data: bytes, media_type: str) -> str:
        raise NotImplementedError

    def get(self, uri: str) -> bytes | None:
        raise NotImplementedError

    def delete(self, uri: str) -> None:
        raise NotImplementedError

    def health(self) -> dict:
        raise NotImplementedError


@dataclass
class LocalStorage(ArtifactStorage):
    root: Path
    name = "local"

    def __post_init__(self) -> None:
        self.root = self.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, workspace_id: str, key: str, data: bytes, media_type: str) -> str:
        workspace = self.root / workspace_id
        workspace.mkdir(parents=True, exist_ok=True)
        path = workspace / key
        path.write_bytes(data)
        return str(path)

    def get(self, uri: str) -> bytes | None:
        path = Path(uri)
        if not path.is_absolute():
            path = (self.root / path).resolve()
        try:
            path.resolve().relative_to(self.root)
        except ValueError:
            return None
        if not path.exists() or not path.is_file():
            return None
        return path.read_bytes()

    def delete(self, uri: str) -> None:
        path = Path(uri)
        if not path.is_absolute():
            path = (self.root / path).resolve()
        try:
            path.resolve().relative_to(self.root)
        except ValueError:
            raise StorageError("artifact path escapes configured root")
        if path.exists():
            path.unlink()

    def health(self) -> dict:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return {"backend": self.name, "ok": self.root.exists(), "root": str(self.root)}
        except Exception as exc:
            return {"backend": self.name, "ok": False, "error": str(exc)}


class S3Storage(ArtifactStorage):
    name = "s3"

    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = os.getenv("TAR_S3_BUCKET", "").strip()
        if not self.bucket:
            raise StorageError("TAR_S3_BUCKET is required for S3 artifact storage")
        self.prefix = os.getenv("TAR_S3_PREFIX", "tar-artifacts").strip("/")
        endpoint = os.getenv("TAR_S3_ENDPOINT_URL", "").strip() or None
        region = os.getenv("TAR_S3_REGION", "us-east-1").strip() or "us-east-1"
        access_key = os.getenv("TAR_S3_ACCESS_KEY_ID", "").strip() or None
        secret_key = os.getenv("TAR_S3_SECRET_ACCESS_KEY", "").strip() or None
        session_token = os.getenv("TAR_S3_SESSION_TOKEN", "").strip() or None
        addressing = os.getenv("TAR_S3_ADDRESSING_STYLE", "path" if endpoint else "auto")
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            config=Config(s3={"addressing_style": addressing}, retries={"max_attempts": 4, "mode": "standard"}),
        )

    def _key(self, workspace_id: str, key: str) -> str:
        parts = [x for x in [self.prefix, workspace_id, key] if x]
        return "/".join(parts)

    def put(self, workspace_id: str, key: str, data: bytes, media_type: str) -> str:
        object_key = self._key(workspace_id, key)
        extra = {"ContentType": media_type or "application/octet-stream"}
        self.client.put_object(Bucket=self.bucket, Key=object_key, Body=data, **extra)
        return f"s3://{self.bucket}/{object_key}"

    def _parse(self, uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
            raise StorageError("invalid S3 artifact URI")
        return parsed.netloc, parsed.path.lstrip("/")

    def get(self, uri: str) -> bytes | None:
        from botocore.exceptions import ClientError

        bucket, key = self._parse(uri)
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404", "NotFound"}:
                return None
            raise

    def delete(self, uri: str) -> None:
        bucket, key = self._parse(uri)
        self.client.delete_object(Bucket=bucket, Key=key)

    def health(self) -> dict:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return {"backend": self.name, "ok": True, "bucket": self.bucket, "prefix": self.prefix}
        except Exception as exc:
            return {"backend": self.name, "ok": False, "bucket": self.bucket, "error": str(exc)}


def configured_storage() -> ArtifactStorage:
    backend = os.getenv("TAR_ARTIFACT_BACKEND", "local").strip().lower()
    if backend == "local":
        return LocalStorage(Path(os.getenv("TAR_ARTIFACT_DIR", "./artifacts")))
    if backend == "s3":
        return S3Storage()
    raise StorageError(f"unsupported TAR_ARTIFACT_BACKEND: {backend}")


def read_artifact_uri(uri: str) -> bytes | None:
    """Read current or legacy artifact references.

    Existing databases may contain absolute filesystem paths even when a new
    deployment has switched to S3. Those records remain readable when their
    local bytes are present; new records are written through the configured backend.
    """
    if uri.startswith("s3://"):
        return S3Storage().get(uri)
    return LocalStorage(Path(os.getenv("TAR_ARTIFACT_DIR", "./artifacts"))).get(uri)

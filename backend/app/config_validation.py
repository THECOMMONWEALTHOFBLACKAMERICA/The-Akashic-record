from __future__ import annotations

import os

from .settings import settings


class ConfigurationError(RuntimeError):
    pass


def production_errors() -> list[str]:
    if settings.env.lower() not in {"prod", "production"}:
        return []
    errors: list[str] = []
    if not settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        errors.append("production requires PostgreSQL via TAR_DATABASE_URL")
    if os.getenv("TAR_REQUIRE_API_KEY", "false").lower() not in {"1", "true", "yes"}:
        errors.append("production requires TAR_REQUIRE_API_KEY=true")
    admin = os.getenv("TAR_ADMIN_KEY", "")
    worker = os.getenv("TAR_WORKER_KEY", "")
    if len(admin) < 24:
        errors.append("TAR_ADMIN_KEY must be a strong production secret")
    if len(worker) < 24:
        errors.append("TAR_WORKER_KEY must be a strong production secret")
    if admin and worker and admin == worker:
        errors.append("TAR_ADMIN_KEY and TAR_WORKER_KEY must be different")
    if os.getenv("TAR_ENABLE_CODE_EXECUTION", "false").lower() in {"1", "true", "yes"}:
        errors.append("code execution must be disabled on the production API host")
    origins = settings.allowed_origins
    if not origins or "*" in origins:
        errors.append("production requires explicit TAR_ALLOWED_ORIGINS")
    if any(not origin.startswith("https://") for origin in origins):
        errors.append("production origins must use HTTPS")
    if settings.llm_provider != "echo" and (not settings.llm_base_url or not settings.llm_model):
        errors.append("configured LLM provider requires TAR_LLM_BASE_URL and TAR_LLM_MODEL")
    backend = os.getenv("TAR_ARTIFACT_BACKEND", "local").lower()
    if backend == "s3" and not os.getenv("TAR_S3_BUCKET", "").strip():
        errors.append("S3 artifact backend requires TAR_S3_BUCKET")
    if backend not in {"local", "s3"}:
        errors.append("TAR_ARTIFACT_BACKEND must be local or s3")
    if os.getenv("TAR_ENABLE_PUBLIC_IPFS", "false").lower() in {"1", "true", "yes"} and not settings.ipfs_api_url:
        errors.append("public IPFS publication requires TAR_IPFS_API_URL")
    return errors


def validate_production_config() -> None:
    errors = production_errors()
    if errors:
        raise ConfigurationError("Invalid production configuration: " + "; ".join(errors))

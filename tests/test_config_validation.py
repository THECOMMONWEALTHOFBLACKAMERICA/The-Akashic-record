from backend.app import config_validation


def test_development_config_does_not_require_production_secrets(monkeypatch):
    monkeypatch.setattr(config_validation.settings, "env", "development")
    assert config_validation.production_errors() == []


def test_production_config_rejects_unsafe_defaults(monkeypatch):
    monkeypatch.setattr(config_validation.settings, "env", "production")
    monkeypatch.setattr(config_validation.settings, "database_url", "sqlite:///./tar.db")
    monkeypatch.setattr(config_validation.settings, "allowed_origins_raw", "*")
    monkeypatch.setenv("TAR_REQUIRE_API_KEY", "false")
    monkeypatch.setenv("TAR_ADMIN_KEY", "short")
    monkeypatch.setenv("TAR_WORKER_KEY", "short")
    monkeypatch.setenv("TAR_ENABLE_CODE_EXECUTION", "true")
    errors = config_validation.production_errors()
    assert any("PostgreSQL" in e for e in errors)
    assert any("TAR_REQUIRE_API_KEY" in e for e in errors)
    assert any("code execution" in e for e in errors)

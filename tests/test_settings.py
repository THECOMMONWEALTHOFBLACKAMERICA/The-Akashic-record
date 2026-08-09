from backend.app.settings import Settings


def test_allowed_origins_uses_documented_environment_name(monkeypatch):
    monkeypatch.setenv("TAR_ALLOWED_ORIGINS", "https://one.example,https://two.example")
    config = Settings(_env_file=None)
    assert config.allowed_origins == ["https://one.example", "https://two.example"]

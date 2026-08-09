from backend.app.provider_status import provider_status


def test_provider_status_only_reports_configuration(monkeypatch):
    monkeypatch.setenv("TAR_IMAGE_API_URL", "https://provider.invalid/images")
    monkeypatch.setenv("TAR_IMAGE_MODEL", "image-model")
    monkeypatch.setenv("TAR_IMAGE_API_KEY", "super-secret-value")
    status = provider_status()
    assert status["configured"]["image"] is True
    assert "super-secret-value" not in repr(status)


def test_unconfigured_provider_is_false(monkeypatch):
    monkeypatch.delenv("TAR_VIDEO_API_URL", raising=False)
    monkeypatch.delenv("TAR_VIDEO_MODEL", raising=False)
    assert provider_status()["configured"]["video"] is False

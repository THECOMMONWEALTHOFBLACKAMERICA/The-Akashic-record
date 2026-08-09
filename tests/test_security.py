import pytest
from fastapi import HTTPException

from backend.app.security import require_admin


def test_admin_fails_closed_without_key(monkeypatch):
    monkeypatch.delenv("TAR_ADMIN_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_admin(None)
    assert exc.value.status_code == 503


def test_admin_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("TAR_ADMIN_KEY", "correct-secret")
    with pytest.raises(HTTPException) as exc:
        require_admin("wrong-secret")
    assert exc.value.status_code == 403


def test_admin_accepts_correct_key(monkeypatch):
    monkeypatch.setenv("TAR_ADMIN_KEY", "correct-secret")
    result = require_admin("correct-secret")
    assert result["role"] == "admin"

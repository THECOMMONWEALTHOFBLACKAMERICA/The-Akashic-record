from backend.app.artifacts import get_artifact, save_artifact
from backend.app.tools import run_python


def test_artifact_round_trip():
    saved = save_artifact("hello.txt", b"hello TAR", "text/plain", {"test": True})
    found = get_artifact(saved["artifact_id"])
    assert found is not None
    row, data = found
    assert row.sha256 == saved["sha256"]
    assert data == b"hello TAR"


def test_code_execution_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TAR_ENABLE_CODE_EXECUTION", raising=False)
    result = run_python("print('hello')")
    assert result["ok"] is False
    assert "disabled" in result["error"].lower()

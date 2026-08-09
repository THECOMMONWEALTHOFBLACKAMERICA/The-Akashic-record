from pathlib import Path

from backend.app.version import VERSION


def test_version_file_matches_runtime_version():
    root_version = Path("VERSION").read_text(encoding="utf-8").strip()
    assert root_version == VERSION

from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from PIL import Image

from .artifacts import save_artifact


def run_python(code: str, timeout: int = 10) -> dict:
    if os.getenv("TAR_ENABLE_CODE_EXECUTION", "false").lower() not in {"1", "true", "yes"}:
        return {"ok": False, "error": "Code execution is disabled. Set TAR_ENABLE_CODE_EXECUTION=true only inside an isolated worker/container."}
    with tempfile.TemporaryDirectory(prefix="tar-code-") as tmp:
        script = Path(tmp) / "main.py"
        script.write_text(code, encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", "HOME": tmp}
        try:
            p = subprocess.run([os.getenv("TAR_PYTHON_BIN", "python"), "-I", str(script)], cwd=tmp, env=env, capture_output=True, text=True, timeout=max(1, min(timeout, 30)), check=False)
            return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:]}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Execution timed out"}


def analyze_csv(data: bytes, name: str = "data.csv") -> dict:
    df = pd.read_csv(io.BytesIO(data))
    summary = {
        "rows": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "missing": {str(k): int(v) for k, v in df.isna().sum().items()},
        "describe": json.loads(df.describe(include="all").fillna("").to_json()),
    }
    artifact = save_artifact(name.rsplit(".", 1)[0] + "-analysis.json", json.dumps(summary, indent=2).encode(), "application/json", {"tool": "analyze_csv"})
    return {"summary": summary, "artifact": artifact}


def image_metadata(data: bytes, name: str = "image") -> dict:
    with Image.open(io.BytesIO(data)) as image:
        result = {"format": image.format, "mode": image.mode, "width": image.width, "height": image.height, "frames": getattr(image, "n_frames", 1)}
    artifact = save_artifact(name + "-metadata.json", json.dumps(result, indent=2).encode(), "application/json", {"tool": "image_metadata"})
    return {"metadata": result, "artifact": artifact}

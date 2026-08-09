from __future__ import annotations

import os
import sys
import time

import httpx

BASE = os.getenv("TAR_SMOKE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("TAR_SMOKE_API_KEY", "")
HEADERS = {"X-TAR-API-Key": API_KEY} if API_KEY else {}


def check(response: httpx.Response, label: str) -> dict:
    if response.status_code >= 400:
        raise RuntimeError(f"{label} failed: {response.status_code} {response.text[:1000]}")
    if "application/json" in response.headers.get("content-type", ""):
        return response.json()
    return {"bytes": len(response.content)}


def main() -> int:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=90) as client:
        health = check(client.get("/health"), "health")
        check(client.get("/ready"), "readiness")
        caps = check(client.get("/v1/system/capabilities"), "capabilities")
        if not caps.get("autonomy", {}).get("enabled"):
            raise RuntimeError("bounded autonomy is not enabled")
        if "epub" not in caps.get("ingestion", []):
            raise RuntimeError("EPUB ingestion is not advertised")

        ask = check(client.post("/v1/ask", json={"query": "T.A.R. release smoke test", "research": False}), "ask")
        if "answer" not in ask:
            raise RuntimeError("ask response did not contain an answer")

        ingest = check(
            client.post(
                "/v1/ingest/file",
                files={"file": ("smoke.txt", b"Akashic smoke marker 8e83a1. Provenance and recall validation.", "text/plain")},
                data={"title": "Release Smoke Document", "source": "release_smoke"},
            ),
            "ingest",
        )
        document_id = ingest.get("document_id")
        if not document_id:
            raise RuntimeError("ingestion produced no document_id")

        recall = check(client.post("/v1/memory/recall", json={"query": "8e83a1 provenance recall", "limit": 10}), "recall")
        if not recall.get("results"):
            raise RuntimeError("ingested marker was not retrievable")

        library = check(
            client.put(
                f"/v1/library/{document_id}",
                json={"favorite": True, "progress": 0.5, "locator": {"section": "smoke"}, "notes": "qualification"},
            ),
            "library update",
        )
        if library.get("document_id") != document_id or library.get("progress") != 0.5:
            raise RuntimeError("library state did not persist")

        agent = check(client.post("/v1/agents/run", json={"goal": "Recall the 8e83a1 smoke evidence"}), "bounded agent")
        if agent.get("status") != "completed" or not agent.get("run_id"):
            raise RuntimeError(f"bounded agent did not complete: {agent}")
        saved_agent = check(client.get(f"/v1/agents/runs/{agent['run_id']}"), "agent history")
        if saved_agent.get("status") != "completed":
            raise RuntimeError("agent history was not persisted")

        pdf = check(
            client.post("/v1/doc-tools/pdf", json={"title": "TAR Smoke", "text": "Release candidate artifact validation."}),
            "pdf creation",
        )
        artifact_id = pdf.get("artifact_id")
        if not artifact_id:
            raise RuntimeError("PDF creation produced no artifact_id")
        artifact = client.get(f"/v1/artifacts/{artifact_id}")
        if artifact.status_code != 200 or not artifact.content.startswith(b"%PDF"):
            raise RuntimeError("artifact retrieval did not return a PDF")

        audit = check(client.get("/v1/audit/verify"), "audit verification")
        if audit.get("valid") is False:
            raise RuntimeError(f"audit chain invalid: {audit}")

        job = check(
            client.post("/v1/jobs", json={"kind": "text", "prompt": "distributed smoke job", "options": {"research": False}}),
            "job enqueue",
        )
        job_id = job.get("job_id") or job.get("id")
        if job_id:
            deadline = time.time() + float(os.getenv("TAR_SMOKE_JOB_TIMEOUT", "30"))
            while time.time() < deadline:
                status = check(client.get(f"/v1/jobs/{job_id}"), "job status")
                if status.get("status") in {"completed", "failed"}:
                    if status.get("status") != "completed":
                        raise RuntimeError(f"worker job failed: {status}")
                    break
                time.sleep(1)
            else:
                raise RuntimeError("worker job did not finish before timeout")

        print(f"T.A.R. smoke test passed; service={health.get('service')} version={health.get('version')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)

from backend.app.jobs import claim, complete, enqueue, get_job


def test_job_claim_and_complete():
    queued = enqueue("research", "test prompt", {"research": False}, "default")
    claimed = claim("node-test", ["research"])
    assert claimed is not None
    assert claimed["job_id"] == queued["job_id"]
    assert claimed["assigned_node"] == "node-test"
    done = complete(queued["job_id"], "node-test", {"answer": "ok"})
    assert done["status"] == "completed"
    assert get_job(queued["job_id"])["result"] == {"answer": "ok"}

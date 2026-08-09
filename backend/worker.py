from __future__ import annotations

import asyncio
import os
import socket

from app.agent_router import execute_task
from app.control import heartbeat_node, register_node
from app.jobs import claim, complete, fail


async def main():
    name = os.getenv("TAR_NODE_NAME", socket.gethostname())
    endpoint = os.getenv("TAR_NODE_ENDPOINT", "")
    capabilities = [x.strip() for x in os.getenv("TAR_NODE_CAPABILITIES", "research,text,image,video,code").split(",") if x.strip()]
    poll_seconds = float(os.getenv("TAR_WORKER_POLL_SECONDS", "2"))
    node = register_node(name, endpoint, capabilities)
    node_id = node["node_id"]
    print(f"T.A.R. worker {name} registered as {node_id} with {capabilities}")
    while True:
        heartbeat_node(node_id)
        job = claim(node_id, capabilities)
        if not job:
            await asyncio.sleep(poll_seconds)
            continue
        try:
            result = await execute_task(job["kind"], job["prompt"], job.get("options") or {})
            complete(job["job_id"], node_id, {"kind": result.kind, "output": result.output})
        except Exception as exc:
            fail(job["job_id"], node_id, str(exc), retry=True)


if __name__ == "__main__":
    asyncio.run(main())

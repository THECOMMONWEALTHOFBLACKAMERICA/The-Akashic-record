from backend.app.control import audit, audit_tail, create_api_key, create_workspace, heartbeat_node, register_node, verify_api_key


def test_workspace_and_api_key():
    ws = create_workspace("Test Workspace", "tester")
    created = create_api_key("test-key", ws["id"])
    identity = verify_api_key(created["api_key"])
    assert identity is not None
    assert identity["workspace_id"] == ws["id"]


def test_audit_chain_links():
    first = audit("test.first", "test", "1", {"x": 1})
    second = audit("test.second", "test", "2", {"x": 2})
    assert second["prev_hash"] == first["event_hash"]
    assert audit_tail(2)


def test_node_heartbeat():
    node = register_node("test-node", "http://localhost:9999", ["research"])
    heartbeat = heartbeat_node(node["node_id"])
    assert heartbeat is not None
    assert heartbeat["node_id"] == node["node_id"]

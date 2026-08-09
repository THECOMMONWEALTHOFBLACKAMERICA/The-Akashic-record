from backend.app.commission_access import accessible_case_ids, grant_case_access, has_case_access, revoke_case_access


def test_case_access_is_key_scoped():
    case_id = "case-access-test"
    workspace = "default"
    grant_case_access(case_id, workspace, "key-owner", "owner")
    grant_case_access(case_id, workspace, "key-read", "readonly")

    assert has_case_access(case_id, workspace, "key-owner", write=True)
    assert has_case_access(case_id, workspace, "key-owner", review=True)
    assert has_case_access(case_id, workspace, "key-read")
    assert not has_case_access(case_id, workspace, "key-read", write=True)
    assert case_id in accessible_case_ids(workspace, "key-owner")
    assert not has_case_access(case_id, workspace, "different-key")

    assert revoke_case_access(case_id, workspace, "key-read") is True
    assert not has_case_access(case_id, workspace, "key-read")
    revoke_case_access(case_id, workspace, "key-owner")

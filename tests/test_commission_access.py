from backend.app.commission_access import accessible_case_ids, grant_case_access, has_case_access, revoke_case_access


def test_case_access_is_key_scoped_and_role_bounded():
    case_id = "case-access-test"
    workspace = "default"
    grant_case_access(case_id, workspace, "key-owner", "owner")
    grant_case_access(case_id, workspace, "key-staff", "staff")
    grant_case_access(case_id, workspace, "key-review", "reviewer")
    grant_case_access(case_id, workspace, "key-read", "readonly")

    assert has_case_access(case_id, workspace, "key-owner", manage=True)
    assert has_case_access(case_id, workspace, "key-owner", review=True)
    assert has_case_access(case_id, workspace, "key-staff", write=True)
    assert not has_case_access(case_id, workspace, "key-staff", manage=True)
    assert has_case_access(case_id, workspace, "key-review", review=True)
    assert not has_case_access(case_id, workspace, "key-review", manage=True)
    assert has_case_access(case_id, workspace, "key-read")
    assert not has_case_access(case_id, workspace, "key-read", write=True)
    assert case_id in accessible_case_ids(workspace, "key-owner")
    assert not has_case_access(case_id, workspace, "different-key")

    for key in ["key-read", "key-review", "key-staff", "key-owner"]:
        revoke_case_access(case_id, workspace, key)

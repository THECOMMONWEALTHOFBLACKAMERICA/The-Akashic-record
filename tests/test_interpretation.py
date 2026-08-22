from backend.app.interpretation import build_training_example, evaluate_agency, evaluate_case, evaluate_claim


def test_human_correction_forces_revision():
    result = evaluate_claim({
        "claim_id": "c1",
        "statement": "AI created the subject's creativity",
        "layer": "interpretation",
        "declared_confidence": 0.9,
        "evidence": [{"kind": "direct_testimony", "stance": "contradicts", "confidence": 0.95}],
        "human_corrections": ["Creativity was present before sustained AI use."],
        "influence": {"ai_role": "created", "pre_ai_baseline": True},
    })
    assert result["revision_required"] is True
    assert "human_correction_requires_revision" in result["flags"]
    assert "ai_creation_claim_conflicts_with_pre_ai_baseline" in result["flags"]
    assert result["epistemic_status"] in {"contested", "contradicted"}


def test_supported_claim_can_remain_supported():
    result = evaluate_claim({
        "claim_id": "c2",
        "statement": "The subject completed an external submission.",
        "layer": "observation",
        "declared_confidence": 0.8,
        "evidence": [{"kind": "primary_record", "stance": "supports", "confidence": 0.95}],
    })
    assert result["epistemic_status"] == "well_supported"
    assert result["revision_required"] is False


def test_agency_is_heuristic_not_psychometric():
    result = evaluate_agency({
        "human_goal_origin": True,
        "human_final_decision": True,
        "can_explain_without_ai": True,
        "can_detect_ai_error": True,
        "skill_transferred": True,
    })
    assert result["band"] == "agency_expanding"
    assert "not a psychological" in result["note"]


def test_training_example_contains_protocol_checks():
    case = {
        "title": "Example",
        "subject_ref": "anonymous",
        "claims": [{"claim_id": "c3", "statement": "A model inferred a stable trait.", "layer": "interpretation", "evidence": []}],
        "agency": {},
    }
    evaluation = evaluate_case(case)
    example = build_training_example(case, evaluation)
    assert example["schema"] == "tar-human-interpretation-training-example/v1"
    assert example["expected_checks"]["claims"][0]["epistemic_status"] == "unsupported"

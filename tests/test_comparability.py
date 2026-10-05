"""The comparability registry is authoritative. Pipeline keys stay families."""

from pdoom_pipeline.belief.comparability import load_comparability_registry, question_by_key
from pdoom_pipeline.belief.taxonomy import KEY_TOPIC, QUESTION_KEYS, TOPICS


def test_pipeline_keys_remain_families_without_a_fixed_horizon():
    registry = load_comparability_registry()
    assert registry["policy_version"] == "comparability/1.0.0"
    assert QUESTION_KEYS
    for key in QUESTION_KEYS:
        question = question_by_key(key)
        assert question is not None, key
        assert question["key"] == key
        assert question["role"] == "family"
        assert question["deadline"] is None
        assert "pipeline" in question["sources"]
    assert set(KEY_TOPIC) == set(QUESTION_KEYS)
    assert TOPICS


def test_registry_does_not_rewrite_stored_keys():
    questions = load_comparability_registry()["questions"]
    keys = [question["key"] for question in questions]
    assert keys.count("extinction_unconditional") == 1
    assert "ai_extinction_unconditional_by_2070" in keys
    extinction = question_by_key("extinction_unconditional")
    dated = question_by_key("ai_extinction_unconditional_by_2070")
    assert extinction is not None and dated is not None
    assert extinction["family_id"] == dated["family_id"]
    assert extinction["key"] != dated["key"]
    assert dated["deadline"]["end"] == "2070-12-31"

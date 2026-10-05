"""The collector status note matches belief collection on main."""

from pathlib import Path

NOTE = Path(__file__).resolve().parents[1] / "docs" / "COLLECTOR_STATUS.md"

UNWIRED_MODULES = (
    "arxiv",
    "bluesky",
    "crossref",
    "forum_magnum",
    "github",
    "huggingface",
    "openalex_works",
    "openreview",
    "semantic_scholar",
    "youtube_metadata",
)

COHORT_LIMIT = "The tracked set is a defined cohort, not all AI researchers."


def _note() -> str:
    return NOTE.read_text(encoding="utf-8")


def test_required_collector_status_sentences_are_present():
    text = _note()
    assert "Belief collection calls RssCollector only." in text
    assert "are not wired into collect_beliefs" in text
    for module in UNWIRED_MODULES:
        assert f"`{module}`" in text
    assert "ForumMagnum and Bluesky stay unwired." in text
    assert COHORT_LIMIT in text


def test_note_does_not_claim_coverage_of_all_ai_researchers():
    text = _note()
    assert "consensus" not in text.lower()
    lines = [line.strip() for line in text.splitlines() if "all AI researchers" in line]
    assert lines == [COHORT_LIMIT]
    lowered = text.lower()
    for claim in (
        "coverage of all ai researchers",
        "covers all ai researchers",
        "all ai researchers are tracked",
        "tracks all ai researchers",
        "the frontier believes",
    ):
        assert claim not in lowered

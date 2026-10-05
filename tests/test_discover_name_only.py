"""A social or code profile stays unresolved when the only evidence is a similar name."""

from pdoom_pipeline.enrich.discover import discover_from_page

VERIFIED_AT = "2026-10-05T00:00:00Z"


def _discover(*, person_id, display_name, page_url, text, links=None, verification_method):
    return discover_from_page(
        person_id=person_id,
        display_name=display_name,
        variants=[],
        page_url=page_url,
        parsed={"text": text, "links": links or []},
        verification_method=verification_method,
        verified_at=VERIFIED_AT,
    )


def test_similar_name_does_not_attach_social_or_code_profile():
    code = _discover(
        person_id="person:john-schulman",
        display_name="John Schulman",
        page_url="https://github.com/jschulman-smith",
        text="John Schulman-Smith",
        verification_method="orcid_researcher_url",
    )
    assert code["identities"] == []
    assert code["sources"] == []
    assert code["feeds"] == []
    assert code["decision"]["name_confirmed"] is False
    assert code["decision"]["reason"] == "name_similar_not_equal"

    other_code = _discover(
        person_id="person:john-schulman",
        display_name="John Schulman",
        page_url="https://github.com/jonathanschulman",
        text="Jonathan Schulman",
        verification_method="orcid_researcher_url",
    )
    assert other_code["identities"] == []
    assert other_code["sources"] == []
    assert other_code["decision"]["reason"] == "name_not_on_page"

    huggingface = _discover(
        person_id="person:thomas-wolf",
        display_name="Thomas Wolf",
        page_url="https://huggingface.co/twolf",
        text="Thomas Wolfe",
        verification_method="orcid_researcher_url",
    )
    assert huggingface["identities"] == []
    assert huggingface["sources"] == []
    assert huggingface["decision"]["reason"] == "name_not_on_page"

    social = _discover(
        person_id="person:joseph-carlsmith",
        display_name="Joseph Carlsmith",
        page_url="https://bsky.app/profile/joe.bsky.social",
        text="Joe Carlsmith",
        verification_method="claimed_url_page_name",
    )
    assert social["identities"] == []
    assert social["sources"] == []
    assert social["decision"]["name_confirmed"] is False
    assert social["decision"]["reason"] == "name_not_on_page"

    linked_from_similar = _discover(
        person_id="person:john-schulman",
        display_name="John Schulman",
        page_url="https://example.com/notes/schulman-smith",
        text="John Schulman-Smith",
        links=[
            {"rel": "me", "href": "https://github.com/joschu"},
            {"rel": "me", "href": "https://bsky.app/profile/joschu.bsky.social"},
        ],
        verification_method="claimed_url_page_name",
    )
    assert linked_from_similar["identities"] == []
    assert linked_from_similar["sources"] == []
    assert linked_from_similar["decision"]["reason"] == "name_similar_not_equal"

    kept_code = _discover(
        person_id="person:john-schulman",
        display_name="John Schulman",
        page_url="https://github.com/joschu",
        text="John Schulman. Not John Schulman-Smith.",
        verification_method="orcid_researcher_url",
    )
    assert [(row["namespace"], row["external_id"]) for row in kept_code["identities"]] == [("github", "joschu")]
    assert kept_code["identities"][0]["verification_method"] == "orcid_researcher_url"
    assert kept_code["sources"][0]["canonical_url"] == "https://github.com/joschu"
    assert kept_code["decision"]["name_confirmed"] is True

    kept_social = _discover(
        person_id="person:john-schulman",
        display_name="John Schulman",
        page_url="https://joschu.net/",
        text="John Schulman is chief scientist.",
        links=[{"rel": "me", "href": "https://bsky.app/profile/joschu.bsky.social"}],
        verification_method="claimed_url_page_name",
    )
    bluesky = [row for row in kept_social["identities"] if row["namespace"] == "bluesky"]
    assert len(bluesky) == 1
    assert bluesky[0]["external_id"] == "joschu.bsky.social"
    assert bluesky[0]["verification_method"] == "rel_me"
    assert kept_social["decision"]["reason"] == "name_confirmed"

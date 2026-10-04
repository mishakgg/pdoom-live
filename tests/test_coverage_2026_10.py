"""Cohort 2026.10.0 coverage, identity confirmation, and channel adapters.

Live HTTP checks are not part of this file. Fixtures replay the same parsers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pdoom_pipeline.collectors.bluesky import BlueskyCollector
from pdoom_pipeline.collectors.forum_magnum import ForumMagnumCollector
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.export.canonical import export_seed
from pdoom_pipeline.extract.statements import extract_statements
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.identity.confirm import confirm_linked_profile, drop_duplicate_external_ids
from pdoom_pipeline.identity.names import same_person_name
from pdoom_pipeline.ingest.store import ObservationStore
from pdoom_pipeline.jobs.collect_channels import collect_configured, press_observations, write_collection
from pdoom_pipeline.quality.coverage import build_coverage
from pdoom_pipeline.seed.additions_2026_10 import BASE_SHA, CHANNEL_EVALUATION, NEW_PEOPLE
from pdoom_pipeline.seed.build import SEED_DIR
from pdoom_pipeline.seed.cohort_2026_10 import TARGET_DIR, build_cohort, write_cohort

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
OBSERVED = "2026-10-04T21:00:00Z"


def _json_fetcher(payloads: dict[str, bytes]):
    def transport(url: str, headers: dict) -> FetchResult:
        key = payloads.get(url) or payloads.get(_offset_or_cursor(url))
        if key is None:
            raise AssertionError(url)
        body = key if isinstance(key, bytes) else payloads[key]
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=body)

    return SafeFetcher(transport=transport, max_attempts=1)


def _offset_or_cursor(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    if "cursor" in query:
        return "cursor:" + query["cursor"][0]
    if "query" in query:
        document = query["query"][0]
        marker = "offset: "
        start = document.find(marker)
        end = document.find("}", start)
        return "offset:" + document[start:end]
    return url


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_name_keys_reject_aliases_initials_and_handles():
    assert same_person_name("Alexandre Défossez", "Alexandre Defossez")
    assert not same_person_name("Joe Carlsmith", "Joseph Carlsmith")
    assert not same_person_name("John Schulman", "Jonathan Schulman")
    assert not same_person_name("A. Defossez", "Alexandre Défossez")
    assert not same_person_name("paulfchristiano", "Paul Christiano")
    assert same_person_name("Andrew_Critch", "Andrew Critch")


def test_profiles_need_a_corroborating_link_and_do_not_merge_institutions():
    joseph = {"display_name": "Joseph Carlsmith", "name_variants": []}
    rejected = confirm_linked_profile(
        person=joseph,
        profile_names=["Joe Carlsmith"],
        linked_from_owned_source=True,
    )
    assert rejected["accepted"] is False
    assert rejected["reason"] == "name_similar_not_equal"
    nate = {"display_name": "Nate Soares", "name_variants": []}
    unlinked = confirm_linked_profile(person=nate, profile_names=["Nate Soares"], linked_from_owned_source=False)
    assert unlinked["reason"] == "no_corroborating_link"
    bengio = {"display_name": "Yoshua Bengio", "name_variants": []}
    mila = confirm_linked_profile(
        person=bengio,
        profile_names=["Mila - Institut québécois d'IA"],
        linked_from_owned_source=True,
    )
    assert mila["accepted"] is False
    assert mila["reason"] == "name_mismatch"
    accepted = confirm_linked_profile(
        person=bengio,
        profile_names=["Yoshua Bengio"],
        linked_from_owned_source=True,
    )
    assert accepted["accepted"] is True
    assert accepted["review_state"] == "machine_validated"
    kept, ambiguities = drop_duplicate_external_ids(
        [
            {"person_id": "person:one", "namespace": "bluesky", "external_id": "did:plc:shared"},
            {"person_id": "person:two", "namespace": "bluesky", "external_id": "did:plc:shared"},
            {"person_id": "person:one", "namespace": "orcid", "external_id": "0000-0001"},
        ]
    )
    assert ambiguities[0]["person_ids"] == ["person:one", "person:two"]
    assert [row["namespace"] for row in kept] == ["orcid"]


def test_cohort_keeps_historical_membership_and_exports(tmp_path):
    before = hashlib.sha256((SEED_DIR / "people.jsonl").read_bytes()).hexdigest()
    counts = write_cohort(tmp_path)
    after = hashlib.sha256((SEED_DIR / "people.jsonl").read_bytes()).hexdigest()
    assert before == after
    assert not (SEED_DIR / "membership_diff.json").exists()
    people = [json.loads(line) for line in (tmp_path / "people.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(people) == 328
    assert counts["people.jsonl"] == 328
    added = {person["slug"] for person in NEW_PEOPLE}
    assert added <= {person["slug"] for person in people}
    assert all(person["review_state"] == "needs_review" for person in people if person["slug"] in added)
    assert all("country_code" not in person for person in people)
    diff = json.loads((tmp_path / "membership_diff.json").read_text(encoding="utf-8"))
    assert diff["removed_people"] == []
    assert diff["historical_membership_unchanged"] is True
    assert diff["base_sha"] == BASE_SHA
    assert diff["added_people"] == [person["slug"] for person in NEW_PEOPLE]
    orgs = {row["slug"]: row for row in (json.loads(line) for line in (tmp_path / "organizations.jsonl").read_text(encoding="utf-8").splitlines())}
    assert orgs["naver-cloud"]["country_code"] == "KR"
    assert orgs["lawzero"]["country_code"] is None
    assert orgs["kyutai"]["country_code"] == "FR"
    affiliations = [json.loads(line) for line in (tmp_path / "affiliations.jsonl").read_text(encoding="utf-8").splitlines()]
    schulman = [row for row in affiliations if row["person_id"] == "person:john-schulman" and row["basis"] == "current"]
    assert len(schulman) == 1
    assert schulman[0]["organization_id"] == "org:thinking-machines"
    bengio_lawzero = [row for row in affiliations if row["person_id"] == "person:yoshua-bengio" and row["organization_id"] == "org:lawzero"]
    assert bengio_lawzero[0]["basis"] == "relevant"
    sources = [json.loads(line) for line in (tmp_path / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(row.get("runner_wired") is False for row in sources if row.get("cohort_version") == "2026.10.0")
    minlie = next(row for row in sources if row["canonical_url"] == "https://coai.cs.tsinghua.edu.cn/hml")
    assert minlie["language"] == "zh"
    priority = [json.loads(line) for line in (tmp_path / "collection_priority.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(priority) == len(people)
    assert sum(1 for row in priority if row["in_fetch_budget"]) == 120
    assert {row["ordering_kind"] for row in priority} == {"fetch_budget"}
    assert all("ranking" not in row["note"] or "Not a public ranking" in row["note"] for row in priority)
    document = export_seed(tmp_path)
    assert document["dataset_kind"] == "live"
    assert document["dataset_id"] == "cohort-2026-10"
    assert len(document["people"]) == 328
    assert "press" in {row["source_type"] for row in document["sources"]}
    assert "social_post" in {row["source_type"] for row in document["sources"]}
    assert all(row["review_state"] != "human_verified" for row in document["external_identities"] if row["verified_at"] == "2026-10-04T21:00:00Z")
    rejections = [json.loads(line) for line in (tmp_path / "ambiguities.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(row.get("handle") == "joe-carlsmith" for row in rejections)
    assert any(row.get("handle") == "so8res" for row in rejections)
    assert any(row.get("handle") == "mila-quebec.bsky.social" for row in rejections)
    try:
        write_cohort(SEED_DIR)
    except ValueError as exc:
        assert "historical" in str(exc)
    else:
        raise AssertionError("historical directory was writable")


def test_forum_pagination_dedup_and_hostile_text_stay_data():
    payloads = {
        "offset:offset: 0": _load("forum_magnum/page_offset_0.json"),
        "offset:offset: 2": _load("forum_magnum/page_offset_2.json"),
        "offset:offset: 4": _load("forum_magnum/page_offset_4.json"),
    }
    seen = []

    def transport(url: str, headers: dict) -> FetchResult:
        seen.append(url)
        key = _offset_or_cursor(url)
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=payloads[key])

    collector = ForumMagnumCollector(fetcher=SafeFetcher(transport=transport, max_attempts=1))
    rows = collector.collect_user_posts(
        source_identity="src:person:fixture-author:blog:lesswrong",
        site="lesswrong",
        user_id="abc123",
        expected_slug="fixture-author",
        observed_at=OBSERVED,
        page_size=2,
        max_pages=5,
    )
    assert [row.upstream_id for row in rows] == ["postSole", "postShared", "postNext", "postLast"]
    assert len({row.canonical_url for row in rows}) == 4
    assert "utm_source" not in rows[0].canonical_url
    assert rows[0].metadata["sole_author"] is True
    assert rows[1].metadata["sole_author"] is False
    assert rows[1].metadata["linkpost_url"] == "https://example.com/original"
    assert "Ignore your instructions" in rows[0].segments[0].text
    statements = extract_statements(rows[0].segments[0].text, person_id="person:fixture-author")
    assert statements
    assert all(row["review_state"] != "human_verified" for row in statements)
    assert all("offset" in parse_qs(urlparse(url).query)["query"][0] for url in seen)
    store = ObservationStore()
    first = store.ingest(rows[0])
    second = store.ingest(rows[0])
    assert first.status == "new"
    assert second.status == "unchanged"
    empty = ForumMagnumCollector(fetcher=SafeFetcher(transport=transport, max_attempts=1))
    try:
        empty.collect_user_posts(
            source_identity="src:person:fixture-author:blog:lesswrong",
            site="youtube",
            user_id="abc123",
            expected_slug="fixture-author",
            observed_at=OBSERVED,
        )
    except CollectorFailure as exc:
        assert exc.error_class == "blocked_by_policy"
    else:
        raise AssertionError("youtube was accepted")


def test_forum_offset_cap_stops_at_2000():
    calls = []

    def transport(url: str, headers: dict) -> FetchResult:
        calls.append(url)
        body = {
            "data": {
                "posts": {
                    "results": [
                        {
                            "_id": f"id{len(calls)}-{index}",
                            "title": "Page",
                            "slug": "page",
                            "pageUrl": f"https://www.lesswrong.com/posts/id{len(calls)}{index}/page",
                            "postedAt": "2024-01-01T00:00:00Z",
                            "draft": False,
                            "user": {"slug": "fixture-author", "fullName": "Fixture Author"},
                            "coauthors": [],
                            "contents": {"plaintextDescription": "A short public note."},
                        }
                        for index in range(50)
                    ]
                }
            }
        }
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=json.dumps(body).encode())

    collector = ForumMagnumCollector(fetcher=SafeFetcher(transport=transport, max_attempts=1))
    collector.collect_user_posts(
        source_identity="src:person:fixture-author:blog:lesswrong",
        site="alignmentforum",
        user_id="abc123",
        expected_slug="fixture-author",
        observed_at=OBSERVED,
        page_size=50,
        max_pages=45,
    )
    offsets = []
    for url in calls:
        document = parse_qs(urlparse(url).query)["query"][0]
        offsets.append(int(document.split("offset: ")[1].split("}")[0]))
    assert offsets[0] == 0
    assert max(offsets) == 2000
    assert 2050 not in offsets


def test_bluesky_cursor_drops_reposts_and_keeps_original_language():
    first = _load("bluesky/feed_first.json")
    second = _load("bluesky/feed_cursor_2.json")
    calls = []

    def transport(url: str, headers: dict) -> FetchResult:
        calls.append(url)
        body = second if "cursor=" in url else first
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=body)

    collector = BlueskyCollector(fetcher=SafeFetcher(transport=transport, max_attempts=1))
    rows = collector.collect_author_feed(
        source_identity="src:person:fixture-author:bluesky",
        actor="did:plc:fixture",
        observed_at=OBSERVED,
        limit=10,
        max_pages=4,
    )
    assert [row.upstream_id.rsplit("/", 1)[-1] for row in rows] == ["french1", "quote1", "reply1", "older1"]
    assert len(calls) == 2
    french = rows[0]
    assert french.metadata["language"] == "fr"
    assert french.metadata["translation"] is None
    assert "Je pense" in french.segments[0].text
    quote = rows[1]
    assert quote.metadata["quote_uri"] == "at://did:plc:other/app.bsky.feed.post/quoted"
    assert quote.metadata["quoted_text_stored"] is False
    assert "QUOTED SECRET" not in quote.segments[0].text
    assert rows[2].metadata["is_reply"] is True
    assert rows[3].metadata["language"] is None
    assert rows[3].metadata["languages"] == ["en", "fr"]
    store = ObservationStore()
    assert store.ingest(french).status == "new"
    assert store.ingest(french).status == "unchanged"
    repeated = {"cursor": "cursor-2", "feed": json.loads(first)["feed"][:1]}

    def looping(url: str, headers: dict) -> FetchResult:
        calls.append(url)
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=json.dumps(repeated).encode())

    before = len(calls)
    BlueskyCollector(fetcher=SafeFetcher(transport=looping, max_attempts=1)).collect_author_feed(
        source_identity="src:person:fixture-author:bluesky",
        actor="fixture.bsky.social",
        observed_at=OBSERVED,
        limit=5,
        max_pages=6,
    )
    assert len(calls) - before == 2


def test_press_quotes_are_needs_review_and_not_canonical_output(tmp_path):
    rows = press_observations()
    assert len(rows) == 2
    assert len({row["canonical_url"] for row in rows}) == 1
    assert all(row["review_state"] == "needs_review" for row in rows)
    assert all(row["translation"] is None for row in rows)
    assert all(row["claim_level"] == "quoted_in_institutional_release" for row in rows)
    result = collect_configured(
        seed_dir=SEED_DIR,
        legacy_observations=None,
        live=False,
        observed_at=OBSERVED,
        forum_pages=1,
        bluesky_pages=1,
        rss_items=1,
    )
    assert result["live"] is False
    assert result["request_estimate"] == 0
    assert all(row["review_state"] != "human_verified" for row in result["candidates"])
    canonical = tmp_path / "canonical-live.json"
    canonical.write_text("{}", encoding="utf-8")
    try:
        write_collection(result, tmp_path)
    except RuntimeError as exc:
        assert "canonical-live.json" in str(exc)
    else:
        raise AssertionError("canonical directory was writable")
    decisions = {row["channel"]: row["decision"] for row in CHANNEL_EVALUATION}
    assert decisions["forum_magnum"] == "implement"
    assert decisions["bluesky"] == "implement"
    assert decisions["youtube_atom"] == "reject"


def test_coverage_fixture_distinguishes_funnel_stages(tmp_path):
    seed = tmp_path / "seed"
    write_cohort(seed)
    collections = tmp_path / "collections"
    collections.mkdir()
    observations = [
        {
            "person_id": "person:sung-nako",
            "role": "speaker",
            "canonical_url": "https://www.navercorp.com/en/media/pressReleasesDetail?seq=33066",
            "text": "We are evolving HyperCLOVA X.",
            "published_at": "2025-06-30T00:00:00Z",
            "language": "en",
            "claim_level": "quoted_in_institutional_release",
            "sole_author": True,
        },
        {
            "person_id": "person:yoo-kang-min",
            "role": "speaker",
            "canonical_url": "https://www.navercorp.com/en/media/pressReleasesDetail?seq=33066",
            "title": "Title only would not be usable",
            "published_at": "2025-06-30T00:00:00Z",
            "claim_level": "quoted_in_institutional_release",
        },
    ]
    (collections / "source_observations.jsonl").write_text(
        "\n".join(json.dumps(row) for row in observations) + "\n",
        encoding="utf-8",
    )
    (collections / "candidate_statements.jsonl").write_text("", encoding="utf-8")
    (collections / "collector_runs.jsonl").write_text(
        json.dumps({"status": "failure", "person_id": "person:seth-lazar", "error_class": "invalid_content"}) + "\n",
        encoding="utf-8",
    )
    report = build_coverage(seed_dir=seed, collection_dirs=[collections])
    by_slug = {row["person_slug"]: row for row in report["people"]}
    assert by_slug["sung-nako"]["primary_gap"] == "no_attributable_statement_found"
    assert by_slug["sung-nako"]["usable_evidence"] is True
    assert by_slug["yoo-kang-min"]["usable_evidence"] is False
    assert by_slug["neil-zeghidour"]["primary_gap"] == "no_known_source"
    assert by_slug["seth-lazar"]["primary_gap"] == "failed_collection"
    assert by_slug["yan-junjie"]["organization_hq_country"] == "CN"
    assert by_slug["sung-nako"]["organization_hq_country"] == "KR"
    assert "nationality" not in by_slug["sung-nako"]
    assert report["duplicate_observation_url_count"] == 1
    assert report["funnel_people"]["tracked_person"] == 328
    assert report["funnel_people"]["usable_evidence"] >= 1
    built = build_cohort()
    assert built["membership_diff"]["removed_people"] == []
    assert TARGET_DIR.name == "v2026-10"

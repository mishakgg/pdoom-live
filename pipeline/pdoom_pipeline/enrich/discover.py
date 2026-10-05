"""Turn a confirmed page or ORCID URL list into identities and sources.

Social accounts are accepted only from rel=me on a name-confirmed page.
Name search is not performed here. A similar name, including a hyphenated
longer name, does not confirm the page.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from pdoom_pipeline.enrich.html_page import (
    classify_profile_url,
    discover_feeds,
    feed_is_acceptable,
    host_is_blocked,
    is_generic_homepage,
    page_confirms_person,
    rel_me_profiles,
    source_type_for_url,
    youtube_feed_url,
)
from pdoom_pipeline.enrich.merge import identity_record, source_record
from pdoom_pipeline.identity.names import name_key
from pdoom_pipeline.urls import canonicalize_url

SOCIAL_SOURCE_TYPES = {"github", "huggingface", "bluesky", "mastodon", "x"}


def discover_from_page(
    *,
    person_id: str,
    display_name: str,
    variants: list[str] | None,
    page_url: str,
    parsed: dict,
    verification_method: str,
    verified_at: str,
    org_hosts: set[str] | None = None,
) -> dict:
    """Return identities, sources, and a decision. Unconfirmed pages add nothing."""
    text = parsed.get("text") or ""
    confirmed = _exact_name_on_page(text, display_name, variants)
    decision = {
        "person_id": person_id,
        "page_url": page_url,
        "name_confirmed": confirmed,
        "verification_method": verification_method,
    }
    if not confirmed:
        decision["reason"] = (
            "name_similar_not_equal" if page_confirms_person(text, display_name, variants) else "name_not_on_page"
        )
        return {"identities": [], "sources": [], "feeds": [], "decision": decision}
    try:
        canonical = canonicalize_url(page_url)
    except ValueError:
        decision["reason"] = "unsafe_or_invalid_url"
        decision["name_confirmed"] = False
        return {"identities": [], "sources": [], "feeds": [], "decision": decision}
    identities: list[dict] = []
    sources: list[dict] = []
    feeds: list[dict] = []
    if host_is_blocked(canonical):
        decision["name_confirmed"] = False
        decision["reason"] = "blocked_host"
        return {"identities": identities, "sources": sources, "feeds": feeds, "decision": decision}
    profile = classify_profile_url(canonical)
    personal_page = False
    if profile is not None:
        identities.append(
            identity_record(
                person_id=person_id,
                namespace=profile["namespace"],
                external_id=profile["external_id"],
                canonical_url=profile["canonical_url"],
                handle=profile.get("handle"),
                verification_method=verification_method,
                confidence="high",
                verified_at=verified_at,
                evidence={"page_url": canonical, "name_confirmed": True, "matched_name": display_name},
            )
        )
        sources.append(_profile_source(person_id, profile, verified_at))
    else:
        kind = "lab_profile" if _host_in(canonical, org_hosts or set()) or _directory_page(canonical) else "personal_website"
        personal_page = kind == "personal_website"
        source_type = "lab_page" if kind == "lab_profile" else "personal_website"
        identities.append(
            identity_record(
                person_id=person_id,
                namespace=kind,
                external_id=canonical,
                canonical_url=canonical,
                handle=None,
                verification_method=verification_method,
                confidence="high",
                verified_at=verified_at,
                evidence={"page_url": canonical, "name_confirmed": True, "matched_name": display_name},
            )
        )
        sources.append(
            _page_source(person_id, source_type, canonical, verification_method, enabled=False)
        )
    for profile in rel_me_profiles(parsed.get("links") or []):
        if host_is_blocked(profile["canonical_url"]):
            continue
        identities.append(
            identity_record(
                person_id=person_id,
                namespace=profile["namespace"],
                external_id=profile["external_id"],
                canonical_url=profile["canonical_url"],
                handle=profile.get("handle"),
                verification_method="rel_me",
                confidence="high",
                verified_at=verified_at,
                evidence={"page_url": canonical, "rel": "me"},
            )
        )
        sources.append(_profile_source(person_id, profile, verified_at))
        feed = youtube_feed_url(profile)
        if feed:
            feeds.append({"person_id": person_id, "feed_url": feed, "source_type": "youtube"})
            sources.append(
                source_record(
                    person_id=person_id,
                    source_type="youtube",
                    name=f"YouTube uploads {profile['external_id']}",
                    canonical_url=feed,
                    platform="youtube",
                    collection_method="rss_feed",
                    enabled=True,
                    verification_method="rel_me",
                    rights_notes="YouTube public Atom feed linked by rel=me. Store metadata and short excerpts only.",
                )
            )
    for feed_url in discover_feeds(parsed.get("links") or []):
        try:
            feed_canonical = canonicalize_url(feed_url)
        except ValueError:
            continue
        if is_generic_homepage(feed_canonical) or not feed_is_acceptable(feed_canonical):
            continue
        feeds.append({"person_id": person_id, "feed_url": feed_canonical, "source_type": "rss"})
        sources.append(
            source_record(
                person_id=person_id,
                source_type="rss",
                name=f"Feed {feed_canonical}",
                canonical_url=feed_canonical,
                platform="rss",
                collection_method="rss_feed",
                enabled=True,
                verification_method=verification_method,
                rights_notes="Public RSS or Atom feed linked from a name-confirmed page. Excerpts only.",
            )
        )
    if personal_page:
        for link in parsed.get("links") or []:
            href = link.get("href") or ""
            if host_is_blocked(href):
                continue
            attached = _linked_channel(person_id, href, verification_method)
            if attached:
                sources.append(attached)
    decision["reason"] = "name_confirmed"
    return {"identities": identities, "sources": sources, "feeds": feeds, "decision": decision}


def discover_from_orcid_urls(*, person_id: str, urls: list[dict], verified_at: str) -> dict:
    """Register newsletter and podcast URLs that the linked ORCID record lists.

    Other ORCID URLs stay candidates for a later page fetch. They are not identities
    until a page confirms the person's name.
    """
    sources = []
    pending_pages = []
    for item in urls:
        url = item["url"]
        kind = source_type_for_url(url)
        if kind in {"newsletter", "podcast"}:
            sources.append(
                source_record(
                    person_id=person_id,
                    source_type=kind,
                    name=item.get("label") or url,
                    canonical_url=url,
                    platform=kind,
                    collection_method="reference_only",
                    enabled=False,
                    verification_method="orcid_researcher_url",
                    rights_notes="URL listed on the ORCID record already linked to this person. Not fetched as a full work.",
                )
            )
            continue
        pending_pages.append(item)
    return {"sources": sources, "pending_pages": pending_pages}


def _page_source(person_id: str, source_type: str, url: str, verification_method: str, *, enabled: bool) -> dict:
    return source_record(
        person_id=person_id,
        source_type=source_type,
        name=url,
        canonical_url=url,
        platform=source_type,
        collection_method="reference_only",
        enabled=enabled,
        verification_method=verification_method,
        rights_notes="Page confirmed by the person's display name. Full page text is not stored.",
    )


def _profile_source(person_id: str, profile: dict, _verified_at: str) -> dict:
    namespace = profile["namespace"]
    collect_github = namespace == "github"
    return source_record(
        person_id=person_id,
        source_type=namespace,
        name=profile["canonical_url"],
        canonical_url=profile["canonical_url"],
        platform=namespace,
        collection_method="github_api" if collect_github else "reference_only",
        enabled=collect_github,
        verification_method="rel_me",
        rights_notes=(
            "GitHub public repository metadata for a rel=me account. Descriptions only."
            if collect_github
            else "Identity reference from rel=me. No collector runs for this channel in this version."
        ),
    )


def _linked_channel(person_id: str, href: str, verification_method: str) -> dict | None:
    try:
        canonical = canonicalize_url(href)
    except ValueError:
        return None
    if is_generic_homepage(canonical):
        return None
    kind = source_type_for_url(canonical)
    if kind not in {"newsletter", "podcast"}:
        return None
    return source_record(
        person_id=person_id,
        source_type=kind,
        name=canonical,
        canonical_url=canonical,
        platform=kind,
        collection_method="reference_only",
        enabled=False,
        verification_method=verification_method,
        rights_notes="Linked from a name-confirmed page or ORCID record. Registered as a source reference.",
    )


def _directory_page(url: str) -> bool:
    path = (urlparse(url).path or "").lower()
    return any(part in path.split("/") for part in {"team", "people", "faculty", "staff", "equipo", "about"})


def _host_in(url: str, hosts: set[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == item or host.endswith("." + item) for item in hosts)


def _exact_name_on_page(text: str, display_name: str, variants: list[str] | None) -> bool:
    """True when an accepted name appears as itself, not as part of a longer hyphenated name."""
    for name in [display_name, *(variants or [])]:
        if _bounded_name(text, name):
            return True
    return False


def _bounded_name(text: str, name: str) -> bool:
    if not name_key(name):
        return False
    pattern = rf"(?<![\w-]){re.escape(name)}(?![\w-])"
    return re.search(pattern, text or "", flags=re.IGNORECASE) is not None

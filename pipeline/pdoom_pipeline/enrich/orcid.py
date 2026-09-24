"""ORCID public records supply URLs only for the ORCID already linked to a person."""

from __future__ import annotations

from pdoom_pipeline.enrich.html_page import host_is_blocked, is_generic_homepage
from pdoom_pipeline.urls import canonicalize_url


def researcher_urls(record: dict) -> list[dict]:
    person = record.get("person") or {}
    block = ((person.get("researcher-urls") or {}).get("researcher-url")) or []
    if isinstance(block, dict):
        block = [block]
    urls = []
    for item in block:
        if not isinstance(item, dict):
            continue
        raw = ((item.get("url") or {}).get("value")) or ""
        name = item.get("url-name") or ""
        if not raw or is_generic_homepage(raw) or host_is_blocked(raw):
            continue
        try:
            canonical = canonicalize_url(raw)
        except ValueError:
            continue
        urls.append({"url": canonical, "label": str(name), "verification_method": "orcid_researcher_url"})
    return urls

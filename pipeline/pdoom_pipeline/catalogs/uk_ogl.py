"""Metadata for UK government AI safety pages that state the Open Government Licence.

Each row keeps the title, publisher, canonical URL, publication date, licence,
and the attribution notice taken from the page. Full documents are not stored.
A page that does not state the Open Government Licence is rejected.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

LICENSE = "open_government_licence"
CATALOG_ID = "uk_ogl_ai_safety"
OGL_PHRASE = "open government licence"
REQUIRED_FIELDS = ("title", "publisher", "canonical_url", "date", "license", "attribution")
MAX_ATTRIBUTION_CHARS = 600

_TAG = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>|<[^>]+>")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PUBLICATION_NOTICE = re.compile(
    r"© Crown copyright \d{4}\s+"
    r"This publication is licensed under the terms of the Open Government Licence v3\.0 except where otherwise stated\. "
    r"To view this licence, visit nationalarchives\.gov\.uk/doc/open-government-licence/version/3 "
    r"or write to the Information Policy Team, The National Archives, Kew, London TW9 4DU, "
    r"or email: psi@nationalarchives\.gov\.uk\. "
    r"Where we have identified any third party copyright information you will need to obtain permission from the copyright holders concerned\."
)
_FOOTER_NOTICE = re.compile(
    r"All content is available under the Open Government Licence v3\.0, except where otherwise stated"
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


class CatalogError(ValueError):
    """A catalog row or page failed the Open Government Licence checks."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / "uk_ogl_ai_safety.json"


def load_catalog() -> dict:
    document = json.loads(catalog_path().read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def states_open_government_licence(page_text: str) -> bool:
    return OGL_PHRASE in _plain_text(page_text).casefold()


def attribution_from_page(page_text: str) -> str:
    """Return the page's Open Government Licence notice.

    Raises CatalogError when the page does not state that licence, or when the
    only match is too long to keep as an attribution rather than the document.
    """

    plain = _plain_text(page_text)
    if OGL_PHRASE not in plain.casefold():
        raise CatalogError("page does not state the Open Government Licence")
    publication = _PUBLICATION_NOTICE.search(plain)
    if publication:
        return publication.group(0)
    footer = _FOOTER_NOTICE.search(plain)
    if footer:
        return footer.group(0)
    sentences = [sentence.strip() for sentence in _SENTENCE.split(plain) if OGL_PHRASE in sentence.casefold()]
    if len(sentences) == 1 and 0 < len(sentences[0]) <= MAX_ATTRIBUTION_CHARS:
        return sentences[0]
    raise CatalogError("page does not state a bounded Open Government Licence attribution")


def validate_catalog(document: dict) -> None:
    if set(document) != {"catalog", "entries"}:
        raise CatalogError("catalog document has unexpected fields")
    if document["catalog"] != CATALOG_ID:
        raise CatalogError("unexpected catalog id")
    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        raise CatalogError("catalog has no entries")
    seen: set[str] = set()
    for entry in entries:
        _validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)


def _validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != set(REQUIRED_FIELDS):
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, license, and attribution")
    if not str(entry["title"]).strip() or not str(entry["publisher"]).strip():
        raise CatalogError("title and publisher are required")
    _validate_url(entry["canonical_url"])
    if entry["date"] != "unknown":
        if not isinstance(entry["date"], str) or not _DATE.fullmatch(entry["date"]):
            raise CatalogError("date must be YYYY-MM-DD or unknown")
        date.fromisoformat(entry["date"])
    if entry["license"] != LICENSE:
        raise CatalogError("license must be open_government_licence")
    attribution = entry["attribution"]
    if not isinstance(attribution, str) or OGL_PHRASE not in attribution.casefold():
        raise CatalogError("attribution must state the Open Government Licence")
    if len(attribution) > MAX_ATTRIBUTION_CHARS:
        raise CatalogError("attribution is too long to be a notice")


def _validate_url(url: str) -> None:
    if not isinstance(url, str):
        raise CatalogError("canonical URL must be a string")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "www.gov.uk":
        raise CatalogError("canonical URL must be an https www.gov.uk URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CatalogError("canonical URL must not include userinfo, a query, or a fragment")
    if not parsed.path.startswith("/government/publications/"):
        raise CatalogError("canonical URL must be a GOV.UK publication")


def _plain_text(page_text: str) -> str:
    text = _TAG.sub(" ", page_text)
    text = unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()

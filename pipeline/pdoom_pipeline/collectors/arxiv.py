"""arXiv API metadata collector.

Stores titles, authors, and abstract excerpts from the export API.
Descriptive metadata is CC0. PDF and source files are not fetched.
An item is redistributable only when its license is a Creative Commons
license that allows copying. The default arXiv non-exclusive license is not.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode, urlparse

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.safe_xml import XmlParseError, fromstring
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import arxiv_id_from_url, canonicalize_url

COLLECTOR_VERSION = "arxiv-0.1.1"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
API = "https://export.arxiv.org/api/query"
# arXiv applies CC0 to the metadata record. It does not apply to the PDF.
METADATA_LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
# by, by-sa, by-nc, by-nd, by-nc-sa, by-nc-nd, CC0, and the public-domain mark.
_CC_COPYING_PATH = re.compile(
    r"(?i)^/(?:licenses/(?:by(?:-nc)?(?:-sa|-nd)?|publicdomain)|publicdomain/(?:zero|mark))(?:/|$)"
)


class ArxivCollector:
    collector = "arxiv"
    platform = "arxiv"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/atom+xml", "text/xml", "application/xml"),
            max_bytes=1_000_000,
        )

    def collect_query(self, *, source_identity: str, search_query: str, observed_at: str, max_results: int = 25) -> list[SourceObservation]:
        if max_results < 1 or max_results > 50:
            raise CollectorFailure("invalid_content", "max_results must be between 1 and 50")
        url = API + "?" + urlencode({"search_query": search_query, "start": 0, "max_results": max_results})
        result = self.fetcher.get(url)
        return self.parse(result.body, source_identity=source_identity, observed_at=observed_at)

    def parse(self, payload: bytes, *, source_identity: str, observed_at: str) -> list[SourceObservation]:
        try:
            root = fromstring(payload)
        except XmlParseError as exc:
            raise CollectorFailure("invalid_content", f"malformed arxiv feed: {exc}") from exc
        if root.tag != f"{ATOM}feed":
            raise CollectorFailure("invalid_content", "arxiv response is not an Atom feed")
        observations: list[SourceObservation] = []
        for entry in list(root):
            if entry.tag != f"{ATOM}entry":
                if entry.tag.split("}")[-1] == "entry":
                    raise CollectorFailure("invalid_content", "arxiv entry has an invalid namespace")
                continue
            observations.append(_entry(entry, source_identity=source_identity, observed_at=observed_at))
        return observations


def _entry(entry, *, source_identity: str, observed_at: str) -> SourceObservation:
    id_url = _child_text(entry, f"{ATOM}id")
    versioned = _versioned_id(id_url)
    bare = arxiv_id_from_url(id_url) or versioned
    if not bare:
        raise CollectorFailure("invalid_content", "arxiv entry missing id")
    title = _child_text(entry, f"{ATOM}title")
    summary = _child_text(entry, f"{ATOM}summary")
    published = _normalize_time(_child_text(entry, f"{ATOM}published"))
    updated = _normalize_time(_child_text(entry, f"{ATOM}updated"))
    authors = []
    for author in entry.findall(f"{ATOM}author"):
        name = _child_text(author, f"{ATOM}name")
        if name:
            authors.append(
                AuthorCandidate(
                    name=name,
                    role="author",
                    attribution_method="arxiv_author_metadata",
                    confidence="high",
                )
            )
    text, truncated = excerpt(summary, 1500)
    canonical = canonicalize_url(f"https://arxiv.org/abs/{bare}")
    license_url = _license_url(entry)
    observation = SourceObservation(
        source_identity=source_identity,
        platform="arxiv",
        upstream_id=versioned or bare,
        canonical_url=canonical,
        observed_at=observed_at,
        published_at=published,
        author_candidates=authors,
        title=title or None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "upstream_version": versioned or bare,
            "updated_at_source": updated,
            "truncated": truncated,
            "arxiv_id": bare,
            "license_url": license_url,
            "redistributable": _work_redistributable(license_url),
            "metadata_license_url": METADATA_LICENSE_URL,
        },
        collection_method="arxiv_api",
        collector="arxiv",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def _child_text(parent, tag: str) -> str:
    element = parent.find(tag)
    if element is None or element.text is None:
        return ""
    return " ".join(element.text.split())


def _versioned_id(id_url: str) -> str:
    if not id_url:
        return ""
    tail = id_url.rstrip("/").split("/")[-1]
    return tail


def _normalize_time(value: str) -> str | None:
    if not value:
        return None
    if value.endswith("Z"):
        return value
    if "+" in value[10:] or value.endswith("Z"):
        return value.replace("+00:00", "Z")
    return value


def _license_url(entry) -> str | None:
    """Read arxiv:license, then dc:rights, then an Atom link rel=license."""
    found: list[tuple[int, int, str]] = []
    for child in list(entry):
        local = child.tag.split("}")[-1].lower()
        if local == "license":
            rank = 0
        elif local == "rights":
            rank = 1
        else:
            continue
        text = " ".join("".join(child.itertext()).split())
        if text:
            found.append((rank, len(found), text))
    found.sort()
    for _rank, _index, text in found:
        url = _http_url(text)
        if url:
            return url
    for child in list(entry):
        if child.tag.split("}")[-1].lower() != "link":
            continue
        if (child.attrib.get("rel") or "").lower() != "license":
            continue
        return _http_url(child.attrib.get("href") or "")
    return None


def _http_url(value: str) -> str | None:
    cleaned = " ".join(value.split())
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"} or parsed.username or parsed.password:
        return None
    if not parsed.hostname:
        return None
    return cleaned


def _work_redistributable(license_url: str | None) -> bool:
    """True only for a Creative Commons license that allows copying the work."""
    if not license_url:
        return False
    parsed = urlparse(license_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if host != "creativecommons.org":
        return False
    return _CC_COPYING_PATH.match(parsed.path) is not None

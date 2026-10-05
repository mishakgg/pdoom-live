"""PubMed article metadata from the public NCBI E-utilities.

Confirms one esearch lookup and the matching esummary. The query is a title
search for artificial intelligence and existential risk, with retmax 1 and
relevance sort. The captured first hit is PMID 39719305, "Artificial
intelligence, existential risk and equity: the need for multigenerational
bioethics.", in the Journal of medical ethics, 2024. That title is about
artificial intelligence and existential risk. The record is an editorial in
a bioethics journal.

esummary is requested with version 2.0. The summary payload has no abstract.
This collector reads esearch and esummary only, so the abstract is not
requested and is not stored. efetch, PMC full text, and PDFs are not
requested.

Publication year is the leading year of ``pubdate``. A missing or unreadable
pubdate stays unknown. Journal is ``fulljournalname``. A missing journal
stays unknown. Author names stay as separate names.

Belief collection does not import this module.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "pubmed-metadata-0.1.0"
API_ORIGIN = "https://eutils.ncbi.nlm.nih.gov"
ESEARCH_PATH = "/entrez/eutils/esearch.fcgi"
ESUMMARY_PATH = "/entrez/eutils/esummary.fcgi"
CONFIRMED_QUERY = '("artificial intelligence"[Title]) AND ("existential risk"[Title])'
RETMAX = 1
TOOL = "pdoom-live"
EMAIL = "collector@pdoom.live"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_JOURNAL_CHARS = 500
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MIN_REQUEST_INTERVAL = 0.34
UNKNOWN = "unknown"

_PMID = re.compile(r"^[1-9][0-9]{0,8}$")
_PUBDATE_YEAR = re.compile(r"^(\d{4})(?:$|[\s/.-])")
_METADATA_PATHS = frozenset({ESEARCH_PATH, ESUMMARY_PATH})


@dataclass(frozen=True)
class PubmedArticle:
    pmid: str
    title: str
    journal: str
    year: int | str
    authors: tuple[str, ...]
    canonical_url: str

    def as_record(self) -> dict[str, object]:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "journal": self.journal,
            "year": self.year,
            "authors": list(self.authors),
            "canonical_url": self.canonical_url,
        }


class PubmedCollector:
    """Retrieve the one confirmed PubMed search hit. The default fetcher makes one attempt per call."""

    collector = "pubmed"
    platform = "pubmed"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        if fetcher is None:
            fetcher = SafeFetcher(
                allowed_content_types=("application/json",),
                max_bytes=MAX_RESPONSE_BYTES,
                timeout=10.0,
                max_redirects=0,
                max_attempts=1,
            )
            fetcher.host_interval = MIN_REQUEST_INTERVAL
        self.fetcher = fetcher

    def retrieve(self) -> PubmedArticle:
        search_url = confirmed_esearch_url()
        pmid = parse_esearch(self._get_metadata(search_url))
        article = parse_esummary(self._get_metadata(esummary_url(pmid)))
        if article.pmid != pmid:
            raise CollectorFailure("invalid_content", "pubmed summary pmid does not match the search hit")
        return article

    def _get_metadata(self, url: str) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "eutils.ncbi.nlm.nih.gov" or parsed.path not in _METADATA_PATHS:
            raise CollectorFailure("unsafe_url", "pubmed retrieval stays on the eutilities api")
        if _forbidden_target(url):
            raise CollectorFailure("blocked_by_policy", "pubmed abstract and pdf are not requested")
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url] or result.url != url:
            raise CollectorFailure("blocked_by_policy", "pubmed retrieval does not follow another url")
        if _forbidden_target(result.url) or result.body.lstrip().startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        return result.body


def confirmed_esearch_url() -> str:
    """URL for the single confirmed search. It does not address efetch, PMC, or a PDF."""
    query = urlencode(
        (
            ("db", "pubmed"),
            ("term", CONFIRMED_QUERY),
            ("retmode", "json"),
            ("retmax", str(RETMAX)),
            ("retstart", "0"),
            ("sort", "relevance"),
            ("tool", TOOL),
            ("email", EMAIL),
        )
    )
    return _metadata_url(ESEARCH_PATH, query)


def esummary_url(pmid: str) -> str:
    """Summary URL for one PMID. Version 2.0 keeps author names as separate objects."""
    query = urlencode(
        (
            ("db", "pubmed"),
            ("id", _pmid(pmid)),
            ("retmode", "json"),
            ("version", "2.0"),
            ("tool", TOOL),
            ("email", EMAIL),
        )
    )
    return _metadata_url(ESUMMARY_PATH, query)


def parse_esearch(payload: bytes) -> str:
    """Return the single PMID from an esearch payload."""
    data = _load_json(payload)
    result = data.get("esearchresult")
    if not isinstance(result, dict):
        raise CollectorFailure("invalid_content", "pubmed esearch missing esearchresult")
    _reject_result_error(result)
    idlist = result.get("idlist")
    if not isinstance(idlist, list):
        raise CollectorFailure("invalid_content", "pubmed esearch missing idlist")
    if len(idlist) == 0:
        raise CollectorFailure("not_found", "pubmed esearch returned no record")
    if len(idlist) > RETMAX:
        raise CollectorFailure("content_too_large", "pubmed esearch exceeds one record")
    return _pmid(idlist[0])


def parse_esummary(payload: bytes) -> PubmedArticle:
    """Read PMID, title, journal, publication year, separate author names, and the PubMed URL.

    Year is read from ``pubdate`` only. ``epubdate`` and ``sortpubdate`` are not
    substituted. Journal is read from ``fulljournalname`` only. Abstract fields
    are ignored.
    """
    data = _load_json(payload)
    result = data.get("result")
    if not isinstance(result, dict):
        raise CollectorFailure("invalid_content", "pubmed esummary missing result")
    uids = result.get("uids")
    if not isinstance(uids, list):
        raise CollectorFailure("invalid_content", "pubmed esummary missing uids")
    if len(uids) == 0:
        raise CollectorFailure("not_found", "pubmed esummary returned no record")
    if len(uids) > RETMAX:
        raise CollectorFailure("content_too_large", "pubmed esummary exceeds one record")
    pmid = _pmid(uids[0])
    item = result.get(pmid)
    if not isinstance(item, dict):
        raise CollectorFailure("invalid_content", "pubmed esummary record is missing")
    if "error" in item and "title" not in item:
        raise CollectorFailure("not_found", "pubmed esummary record is unavailable")
    if _pmid(item.get("uid")) != pmid:
        raise CollectorFailure("invalid_content", "pubmed esummary uid does not match")
    return PubmedArticle(
        pmid=pmid,
        title=_title(item.get("title")),
        journal=_journal(item.get("fulljournalname")),
        year=_year(item.get("pubdate")),
        authors=_authors(item.get("authors")),
        canonical_url=_canonical_url(pmid),
    )


def _metadata_url(path: str, query: str) -> str:
    url = f"{API_ORIGIN}{path}?{query}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "eutils.ncbi.nlm.nih.gov" or parsed.path != path:
        raise CollectorFailure("unsafe_url", "pubmed retrieval stays on the eutilities api")
    if parsed.fragment or parsed.username or parsed.password or _forbidden_target(url):
        raise CollectorFailure("blocked_by_policy", "pubmed abstract and pdf are not requested")
    return url


def _load_json(payload: bytes) -> dict:
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "pubmed payload exceeds limit")
    if payload.lstrip().startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed pubmed payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "pubmed payload is not an object")
    _reject_api_error(data)
    return data


def _reject_api_error(data: dict) -> None:
    error = data.get("error")
    if error is None:
        return
    if not isinstance(error, str):
        raise CollectorFailure("invalid_content", "pubmed response returned an error")
    if "rate limit" in error.lower() or "too many requests" in error.lower():
        raise CollectorFailure("rate_limited", "pubmed rate limit")
    raise CollectorFailure("invalid_content", "pubmed response returned an error")


def _reject_result_error(result: dict) -> None:
    error = result.get("ERROR")
    if not isinstance(error, str) or not error.strip():
        return
    if "rate" in error.lower():
        raise CollectorFailure("rate_limited", "pubmed rate limit")
    raise CollectorFailure("invalid_content", "pubmed esearch returned an error")


def _pmid(value: object) -> str:
    if isinstance(value, bool):
        raise CollectorFailure("invalid_content", "pubmed pmid is missing")
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise CollectorFailure("invalid_content", "pubmed pmid is missing")
    if _PMID.fullmatch(text):
        return text
    raise CollectorFailure("invalid_content", "pubmed pmid is not numeric")


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "pubmed title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "pubmed title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "pubmed title exceeds limit")
    return title


def _journal(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    journal = " ".join(value.split())
    if not journal:
        return UNKNOWN
    if len(journal) > MAX_JOURNAL_CHARS:
        raise CollectorFailure("content_too_large", "pubmed journal exceeds limit")
    return journal


def _year(value: object) -> int | str:
    if not isinstance(value, str):
        return UNKNOWN
    match = _PUBDATE_YEAR.match(" ".join(value.split()))
    if match is None:
        return UNKNOWN
    year = int(match.group(1))
    if 1000 <= year <= 9999:
        return year
    return UNKNOWN


def _authors(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "pubmed authors are not a list")
    if len(value) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "pubmed author list exceeds limit")
    names: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            raise CollectorFailure("invalid_content", "pubmed author was not an object")
        raw = author.get("name")
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise CollectorFailure("invalid_content", "pubmed author name is not text")
        name = " ".join(raw.split())
        if not name:
            continue
        if len(name) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "pubmed author name exceeds limit")
        names.append(name)
    return tuple(names)


def _canonical_url(pmid: str) -> str:
    try:
        url = canonicalize_url(f"https://pubmed.ncbi.nlm.nih.gov/{pmid}")
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "pubmed canonical url is invalid") from exc
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "pubmed.ncbi.nlm.nih.gov" or parsed.path != f"/{pmid}":
        raise CollectorFailure("unsafe_url", "pubmed canonical url left the pubmed host")
    if parsed.query or parsed.fragment or _forbidden_target(url):
        raise CollectorFailure("blocked_by_policy", "pubmed canonical url is the record page")
    return url


def _forbidden_target(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in (".pdf", "/pdf", "efetch", "fulltext", "pmc/articles"))

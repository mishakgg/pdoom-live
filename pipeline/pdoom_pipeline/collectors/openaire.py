"""OpenAIRE Graph research-product metadata.

Confirms one record from the public Graph API at
https://api.openaire.eu/graph/v3/research-products. The request is one
publication search for "AI catastrophic risk" with pageSize 1. On 2026-10-05
that search returned 717 publications, and the first hit was "Actionable
Guidance for High-Consequence AI Risk Management: Towards Standards
Addressing AI Catastrophic Risks" (DOI 10.48550/arxiv.2206.08966). The title
is about standards addressing AI catastrophic risks. It is stored as
returned and is not relabeled.

The parser keeps the title, each author name separately, the publication
date, the DOI, a canonical URL, and the license string when the payload has
one. A missing license, date, or DOI stays unknown. Descriptions, abstracts,
and PDFs are not stored or downloaded. Author names are not merged. This
collector is not wired into belief collection.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "openaire-metadata-0.1.0"
API_ORIGIN = "https://api.openaire.eu"
PRODUCTS_PATH = "/graph/v3/research-products"
CONFIRMED_SEARCH = "AI catastrophic risk"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_INSTANCES = 100
MAX_LICENSE_CHARS = 200

_DATE = re.compile(r"\A(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?\Z")
_DOI_VALUE = re.compile(r"\A10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\Z")
_OPENAIRE_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.:-]{7,199}\Z")
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


@dataclass(frozen=True)
class OpenAireRecord:
    """Bibliographic fields from one research product. No abstract and no PDF."""

    title: str
    authors: tuple[str, ...]
    publication_date: str
    doi: str
    canonical_url: str
    license: str
    openaire_id: str

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "authors": list(self.authors),
            "publication_date": self.publication_date,
            "doi": self.doi,
            "canonical_url": self.canonical_url,
            "license": self.license,
            "openaire_id": self.openaire_id,
        }


class OpenAireCollector:
    """Retrieve the one confirmed search hit. This collector is not wired into belief collection."""

    collector = "openaire"
    platform = "openaire"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self) -> OpenAireRecord:
        """Fetch metadata for the fixed search. Does not follow redirects or file links."""
        url = research_product_search_url()
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url]:
            raise CollectorFailure("blocked_by_policy", "refusing a redirected openaire fetch")
        if _looks_like_pdf(result.url) or result.body.startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        return parse_research_product(result.body)


def research_product_search_url() -> str:
    """JSON search URL for the one confirmed publication. It does not address a PDF."""
    query = urlencode(
        (
            ("search", CONFIRMED_SEARCH),
            ("type", "publication"),
            ("page", "1"),
            ("pageSize", "1"),
        )
    )
    url = f"{API_ORIGIN}{PRODUCTS_PATH}?{query}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.openaire.eu" or parsed.path != PRODUCTS_PATH:
        raise CollectorFailure("unsafe_url", "openaire retrieval stays on the graph api")
    if _looks_like_pdf(url):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    return url


def parse_research_product(payload: bytes) -> OpenAireRecord:
    """Read title, author names, date, DOI, canonical URL, and license.

    A missing license, publication date, or DOI is the string ``unknown``.
    Descriptions and instance file URLs are ignored.
    """
    if payload.startswith(b"%PDF") or payload.startswith(b"\xef\xbb\xbf%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "openaire payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed openaire payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "openaire payload was not an object")
    product = _one_product(data)
    title = _title(product.get("mainTitle"))
    openaire_id = _openaire_id(product.get("id"))
    doi = _doi(product)
    return OpenAireRecord(
        title=title,
        authors=_authors(product.get("authors")),
        publication_date=_publication_date(product.get("publicationDate")),
        doi=doi,
        canonical_url=_canonical_url(doi, openaire_id),
        license=_license(product),
        openaire_id=openaire_id,
    )


def _one_product(data: dict) -> dict:
    if "results" in data:
        results = data.get("results")
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
            raise CollectorFailure("invalid_content", "expected exactly one openaire research product")
        return results[0]
    if data.get("mainTitle") or data.get("id"):
        return data
    raise CollectorFailure("invalid_content", "openaire payload is not a research product")


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "openaire research product title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "openaire research product title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "openaire title exceeds limit")
    return title


def _openaire_id(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    if not text or "://" in text or _looks_like_pdf(text) or not _OPENAIRE_ID.fullmatch(text):
        return UNKNOWN
    return text


def _authors(value: object) -> tuple[str, ...]:
    """Keep each author entry as its own name. Ranks and identifiers do not merge entries."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "openaire authors are not a list")
    if len(value) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "openaire author list exceeds limit")
    names: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _author_name(item)
        if not name:
            continue
        if len(name) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "openaire author name exceeds limit")
        names.append(name)
    return tuple(names)


def _author_name(item: dict) -> str:
    full = item.get("fullName")
    if isinstance(full, str):
        cleaned = " ".join(full.split())
        if cleaned:
            return cleaned
    parts: list[str] = []
    for key in ("name", "surname"):
        piece = item.get(key)
        if isinstance(piece, str):
            cleaned = " ".join(piece.split())
            if cleaned:
                parts.append(cleaned)
    return " ".join(parts)


def _publication_date(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    match = _DATE.fullmatch(text)
    if not match:
        return UNKNOWN
    year = int(match.group(1))
    if year < 1000 or year > 2100:
        return UNKNOWN
    month_text = match.group(2)
    if month_text is not None and not 1 <= int(month_text) <= 12:
        return UNKNOWN
    day_text = match.group(3)
    if day_text is not None and not 1 <= int(day_text) <= 31:
        return UNKNOWN
    return text


def _doi(product: dict) -> str:
    for candidate in _doi_candidates(product):
        bare = _bare_doi(candidate)
        if not bare or _looks_like_pdf(bare) or not _DOI_VALUE.fullmatch(bare):
            continue
        return bare
    return UNKNOWN


def _doi_candidates(product: dict) -> list[str]:
    found = _pid_doi_values(product.get("pids"))
    instances = product.get("instances")
    if not isinstance(instances, list):
        return found
    for instance in instances[:MAX_INSTANCES]:
        if not isinstance(instance, dict):
            continue
        found.extend(_pid_doi_values(instance.get("pids")))
        found.extend(_pid_doi_values(instance.get("alternateIdentifiers")))
    return found


def _pid_doi_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    found: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        scheme = item.get("scheme")
        raw = item.get("value")
        if not isinstance(scheme, str) or scheme.strip().lower() != "doi":
            continue
        if isinstance(raw, str) and raw.strip():
            found.append(raw.strip())
    return found


def _bare_doi(value: str) -> str:
    text = value.strip()
    lowered = text.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _canonical_url(doi: str, openaire_id: str) -> str:
    if doi != UNKNOWN:
        candidate = f"https://doi.org/{doi}"
        if not _looks_like_pdf(candidate):
            try:
                return canonicalize_url(candidate)
            except ValueError:
                pass
    if openaire_id == UNKNOWN:
        return UNKNOWN
    path = f"{PRODUCTS_PATH}/{quote(openaire_id, safe=':')}"
    url = f"{API_ORIGIN}{path}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.openaire.eu" or _looks_like_pdf(parsed.path):
        return UNKNOWN
    return url


def _license(product: dict) -> str:
    """Use an instance license string. Access-right labels such as OPEN are not a license."""
    instances = product.get("instances")
    if instances is None:
        return UNKNOWN
    if not isinstance(instances, list):
        raise CollectorFailure("invalid_content", "openaire instances are not a list")
    if len(instances) > MAX_INSTANCES:
        raise CollectorFailure("content_too_large", "openaire instance list exceeds limit")
    for instance in instances:
        if not isinstance(instance, dict):
            continue
        raw = instance.get("license")
        if not isinstance(raw, str):
            continue
        license_name = " ".join(raw.split())
        if not license_name or _looks_like_pdf(license_name):
            continue
        if len(license_name) > MAX_LICENSE_CHARS:
            raise CollectorFailure("content_too_large", "openaire license exceeds limit")
        return license_name
    return UNKNOWN


def _looks_like_pdf(value: str) -> bool:
    lowered = value.lower().split("?", 1)[0].split("#", 1)[0]
    return lowered.endswith(".pdf") or "/pdf/" in lowered or lowered.startswith("%pdf")

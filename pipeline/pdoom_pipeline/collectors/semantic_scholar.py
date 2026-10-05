"""Semantic Scholar paper metadata.

Looks up one paper on the public Graph API and reads title, id, URL, year,
authors, and an open-access or license flag when the payload has one. A
missing license stays unknown. This module does not download PDFs and is not
wired into belief collection or the web app.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "semantic-scholar-metadata-0.1.0"
API_ORIGIN = "https://api.semanticscholar.org"
PAPER_PATH = "/graph/v1/paper/"
FIELDS = (
    "paperId",
    "title",
    "url",
    "year",
    "authors",
    "isOpenAccess",
    "openAccessPdf",
    "externalIds",
)
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_LICENSE_CHARS = 80
UNKNOWN = "unknown"

_PAPER_KEY = re.compile(
    r"^(?:"
    r"[0-9a-fA-F]{40}"
    r"|ARXIV:\d{4}\.\d{4,5}(?:v\d+)?"
    r"|ARXIV:[A-Za-z\-]+/\d{7}(?:v\d+)?"
    r"|CorpusId:\d{1,12}"
    r"|DOI:10\.\d{4,9}/[-._;()/:A-Za-z0-9]+"
    r")$"
)
_PAPER_ID = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class SemanticScholarAuthor:
    name: str
    author_id: str | None = None

    def as_dict(self) -> dict[str, str]:
        row = {"name": self.name}
        if self.author_id:
            row["author_id"] = self.author_id
        return row


@dataclass(frozen=True)
class SemanticScholarPaper:
    title: str
    paper_id: str
    url: str
    year: int | str
    authors: tuple[SemanticScholarAuthor, ...]
    license: str
    open_access: bool | None = None

    def as_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "title": self.title,
            "paper_id": self.paper_id,
            "url": self.url,
            "year": self.year,
            "authors": [author.as_dict() for author in self.authors],
            "license": self.license,
        }
        if self.open_access is not None:
            record["open_access"] = self.open_access
        return record


class SemanticScholarCollector:
    """Retrieve one paper's metadata. The default fetcher makes a single attempt."""

    collector = "semantic_scholar"
    platform = "semantic_scholar"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, paper_key: str) -> SemanticScholarPaper:
        return parse_paper(self.fetch_payload(paper_key))

    def fetch_payload(self, paper_key: str) -> bytes:
        url = paper_request_url(paper_key)
        result = self.fetcher.get(url)
        if _looks_like_pdf_target(result.url) or result.body.startswith(b"%PDF"):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        return result.body


def paper_request_url(paper_key: str) -> str:
    key = _validated_key(paper_key)
    query = urlencode({"fields": ",".join(FIELDS)})
    return f"{API_ORIGIN}{PAPER_PATH}{quote(key, safe='')}?{query}"


def parse_paper(payload: bytes) -> SemanticScholarPaper:
    if payload.startswith(b"%PDF"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "semantic scholar payload exceeds limit")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed semantic scholar payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "semantic scholar payload is not an object")
    raw_id = data.get("paperId")
    paper_id = raw_id.lower() if isinstance(raw_id, str) else ""
    if not _PAPER_ID.fullmatch(paper_id):
        raise CollectorFailure("invalid_content", "semantic scholar paper id is missing")
    title = _title(data.get("title"))
    return SemanticScholarPaper(
        title=title,
        paper_id=paper_id,
        url=_paper_url(paper_id, data.get("url")),
        year=_year(data.get("year")),
        authors=_authors(data.get("authors")),
        license=_license(data),
        open_access=_open_access(data),
    )


def _validated_key(paper_key: str) -> str:
    key = (paper_key or "").strip()
    if _looks_like_pdf_target(key) or not _PAPER_KEY.fullmatch(key):
        raise CollectorFailure("invalid_content", "semantic scholar paper key is not a paper id")
    return key


def _looks_like_pdf_target(value: str) -> bool:
    lowered = value.lower()
    return lowered.endswith(".pdf") or "/pdf/" in lowered or lowered.startswith("%pdf")


def _title(value: object) -> str:
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "semantic scholar paper title is missing")
    title = " ".join(value.split())
    if not title:
        raise CollectorFailure("invalid_content", "semantic scholar paper title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "semantic scholar title exceeds limit")
    return title


def _year(value: object) -> int | str:
    if isinstance(value, bool):
        return UNKNOWN
    if isinstance(value, int) and 1900 <= value <= 2100:
        return value
    if isinstance(value, str) and value.isdigit():
        year = int(value)
        if 1900 <= year <= 2100:
            return year
    return UNKNOWN


def _authors(value: object) -> tuple[SemanticScholarAuthor, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "semantic scholar authors are not a list")
    if len(value) > MAX_AUTHORS:
        raise CollectorFailure("content_too_large", "semantic scholar author list exceeds limit")
    authors: list[SemanticScholarAuthor] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str):
            continue
        cleaned = " ".join(name.split())
        if not cleaned:
            continue
        if len(cleaned) > MAX_AUTHOR_NAME_CHARS:
            raise CollectorFailure("content_too_large", "semantic scholar author name exceeds limit")
        author_id = item.get("authorId")
        if not isinstance(author_id, str) or not author_id.strip():
            authors.append(SemanticScholarAuthor(name=cleaned))
            continue
        author_id = author_id.strip()
        if len(author_id) > 32 or not author_id.isdigit():
            authors.append(SemanticScholarAuthor(name=cleaned))
            continue
        authors.append(SemanticScholarAuthor(name=cleaned, author_id=author_id))
    return tuple(authors)


def _license(data: dict) -> str:
    candidates: list[object] = []
    if "license" in data:
        candidates.append(data.get("license"))
    pdf = data.get("openAccessPdf")
    if isinstance(pdf, dict) and "license" in pdf:
        candidates.append(pdf.get("license"))
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        license_name = " ".join(candidate.split())
        if not license_name:
            continue
        if len(license_name) > MAX_LICENSE_CHARS:
            raise CollectorFailure("content_too_large", "semantic scholar license exceeds limit")
        return license_name
    return UNKNOWN


def _open_access(data: dict) -> bool | None:
    if "isOpenAccess" not in data:
        return None
    value = data.get("isOpenAccess")
    if isinstance(value, bool):
        return value
    return None


def _paper_url(paper_id: str, payload_url: object) -> str:
    fallback = f"https://www.semanticscholar.org/paper/{paper_id}"
    if not isinstance(payload_url, str) or not payload_url.strip():
        return fallback
    if _looks_like_pdf_target(payload_url):
        return fallback
    try:
        canonical = canonicalize_url(payload_url.strip())
    except ValueError:
        return fallback
    parsed = urlparse(canonical)
    host = parsed.hostname or ""
    if host not in {"www.semanticscholar.org", "semanticscholar.org"}:
        return fallback
    if not parsed.path.startswith("/paper/"):
        return fallback
    return canonical

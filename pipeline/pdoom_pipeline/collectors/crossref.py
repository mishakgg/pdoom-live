"""Crossref work metadata.

Retrieves one bibliographic record from the public works API. The response
is JSON metadata only. Publisher PDFs and full texts are not requested.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher

COLLECTOR_VERSION = "crossref-0.1.0"
API_ORIGIN = "https://api.crossref.org"
WORKS_PATH = "/works"
SELECT_FIELDS = "DOI,title,author,issued,URL,license"
MAILTO = "collector@pdoom.live"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000


@dataclass(frozen=True)
class CrossrefWork:
    title: str
    doi: str
    url: str
    issued: str
    authors: tuple[str, ...]
    license_url: str

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "doi": self.doi,
            "url": self.url,
            "issued": self.issued,
            "authors": list(self.authors),
            "license_url": self.license_url,
        }


class CrossrefCollector:
    """Fetch and parse one Crossref work. This collector is not wired into belief collection."""

    collector = "crossref"
    platform = "crossref"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10,
            max_attempts=1,
        )

    def work_url(self, doi: str) -> str:
        return crossref_work_url(doi)

    def retrieve(self, doi: str) -> CrossrefWork:
        url = self.work_url(doi)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        return self.parse(result.body)

    def parse(self, payload: bytes) -> CrossrefWork:
        return parse_crossref_work(payload)


def crossref_work_url(doi: str) -> str:
    """JSON works URL for one DOI.

    ``select`` is valid on ``/works?filter=doi:`` and is rejected on ``/works/{doi}``.
    ``rows=1`` keeps the call to a single record. The URL is the API record, never a publisher PDF.
    Commas in ``select`` stay literal because Crossref splits that parameter on commas.
    """
    bare = _request_doi(doi)
    if _path_is_pdf(bare):
        raise CollectorFailure("blocked_by_policy", "publisher pdf is not downloaded")
    encoded_doi = quote(bare, safe="/")
    query = f"filter=doi:{encoded_doi}&rows=1&select={SELECT_FIELDS}&mailto={quote(MAILTO)}"
    url = f"{API_ORIGIN}{WORKS_PATH}?{query}"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.crossref.org" or parsed.path != WORKS_PATH:
        raise CollectorFailure("unsafe_url", "crossref retrieval stays on the works api")
    if _path_is_pdf(parsed.path) or ".pdf" in parsed.query.lower():
        raise CollectorFailure("blocked_by_policy", "publisher pdf is not downloaded")
    return url


def parse_crossref_work(payload: bytes) -> CrossrefWork:
    """Return title, DOI, URL, issued date, author names, and license URL.

    Issued date and license URL are the string ``unknown`` when Crossref omits them.
    """
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed crossref payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "crossref payload was not an object")
    work = _one_work(data)
    title = _title(work.get("title"))
    doi = _response_doi(work.get("DOI") or work.get("doi"))
    url = _http_url(work.get("URL") or work.get("url"))
    return CrossrefWork(
        title=title,
        doi=doi,
        url=url,
        issued=_issued_date(work.get("issued")),
        authors=_authors(work.get("author")),
        license_url=_license_url(work.get("license")),
    )


def _one_work(data: dict) -> dict:
    status = data.get("status")
    if status is not None and status != "ok":
        raise CollectorFailure("invalid_content", f"crossref status {status}")
    message = data.get("message", data)
    if not isinstance(message, dict):
        raise CollectorFailure("invalid_content", "crossref message was not an object")
    if "items" in message:
        items = message.get("items")
        if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
            raise CollectorFailure("invalid_content", "expected exactly one crossref work")
        return items[0]
    if not (message.get("DOI") or message.get("doi")):
        raise CollectorFailure("invalid_content", "crossref work missing doi")
    return message


def _title(value: object) -> str:
    if isinstance(value, str):
        parts = [value]
    elif isinstance(value, list):
        parts = [item for item in value if isinstance(item, str)]
    else:
        parts = []
    for part in parts:
        text = " ".join(part.split())
        if text:
            return text
    raise CollectorFailure("invalid_content", "crossref work missing title")


def _request_doi(value: str) -> str:
    text = _strip_doi_prefix(value.strip())
    if not text or any(character.isspace() for character in text) or "/" not in text:
        raise CollectorFailure("invalid_content", "invalid crossref doi")
    if text.lower().startswith(("http://", "https://", "file:")):
        raise CollectorFailure("invalid_content", "invalid crossref doi")
    return text


def _response_doi(value: object) -> str:
    text = _strip_doi_prefix(str(value or "").strip())
    if not text or any(character.isspace() for character in text):
        raise CollectorFailure("invalid_content", "crossref work missing doi")
    return text


def _strip_doi_prefix(text: str) -> str:
    lowered = text.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _http_url(value: object) -> str:
    text = str(value or "").strip()
    if text.startswith("https://") or text.startswith("http://"):
        return text
    return UNKNOWN


def _issued_date(value: object) -> str:
    if not isinstance(value, dict):
        return UNKNOWN
    parts = value.get("date-parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list) or not parts[0]:
        return UNKNOWN
    numbers = parts[0][:3]
    if not all(isinstance(number, int) and not isinstance(number, bool) for number in numbers):
        return UNKNOWN
    year = numbers[0]
    if year < 1000 or year > 9999:
        return UNKNOWN
    if len(numbers) == 1:
        return f"{year:04d}"
    month = numbers[1]
    if month < 1 or month > 12:
        return UNKNOWN
    if len(numbers) == 2:
        return f"{year:04d}-{month:02d}"
    day = numbers[2]
    if day < 1 or day > 31:
        return UNKNOWN
    return f"{year:04d}-{month:02d}-{day:02d}"


def _authors(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "crossref author list was not a list")
    names: list[str] = []
    for entry in value:
        name = _author_name(entry)
        if name:
            names.append(name)
    return tuple(names)


def _author_name(entry: object) -> str:
    if not isinstance(entry, dict):
        return ""
    literal = " ".join(str(entry.get("name") or "").split())
    if literal:
        return literal
    parts: list[str] = []
    for key in ("given", "family", "suffix"):
        piece = " ".join(str(entry.get(key) or "").split())
        if piece:
            parts.append(piece)
    return " ".join(parts)


def _license_url(value: object) -> str:
    if value is None:
        return UNKNOWN
    if isinstance(value, dict):
        entries = [value]
    elif isinstance(value, list):
        entries = value
    else:
        return UNKNOWN
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        url = _http_url(entry.get("URL") or entry.get("url"))
        if url != UNKNOWN:
            return url
    return UNKNOWN


def _path_is_pdf(path: str) -> bool:
    return path.lower().split("?", 1)[0].endswith(".pdf")

"""ACL Anthology bibliographic metadata.

Retrieves one paper's public MODS XML citation file from
``https://aclanthology.org/{anthology_id}.xml``. That response is bibliography
metadata. This module does not download PDFs, does not follow redirects, and
is not wired into belief collection. ``RssCollector`` stays the only belief
collector.

The captured paper is anthology id ``2024.findings-acl.235``, titled
"SALAD-Bench: A Hierarchical and Comprehensive Safety Benchmark for Large
Language Models". The title concerns LLM safety. Authors stay separate names.
A missing year stays ``unknown``. The public MODS file for this paper has no
abstract element, so none is stored. An abstract already present on the MODS
record is kept as metadata and is not treated as the paper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.safe_xml import XmlParseError, declares_xml_type, fromstring
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "acl-anthology-metadata-0.1.0"
API_HOST = "aclanthology.org"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_TITLE_CHARS = 2_000
MAX_AUTHORS = 200
MAX_AUTHOR_NAME_CHARS = 300
MAX_ABSTRACT_CHARS = 4_000
MODS_NS = "http://www.loc.gov/mods/v3"

_NEW_ID = re.compile(r"^\d{4}\.[a-z0-9]+(?:-[a-z0-9]+)*\.\d+$")
_OLD_ID = re.compile(r"^[A-Z]\d{2}-\d{4}$")
_ISSUED = re.compile(r"^(?P<year>\d{4})(?:-(?P<month>\d{2})(?:-(?P<day>\d{2}))?)?$")
_PDF_SUFFIXES = (".pdf", ".xml", ".bib", ".endf")


@dataclass(frozen=True)
class AclAnthologyPaper:
    anthology_id: str
    title: str
    authors: tuple[str, ...]
    year: int | str
    canonical_url: str
    abstract: str | None = None

    def as_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "anthology_id": self.anthology_id,
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "canonical_url": self.canonical_url,
        }
        if self.abstract is not None:
            record["abstract"] = self.abstract
        return record


class AclAnthologyCollector:
    """Retrieve one paper's MODS citation. The default fetcher makes one attempt."""

    collector = "acl_anthology"
    platform = "acl_anthology"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("text/plain", "application/xml", "text/xml"),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, anthology_id: str) -> AclAnthologyPaper:
        paper_id = require_anthology_id(anthology_id)
        url = metadata_url(paper_id)
        result = self.fetcher.get(url, headers={"Accept": "application/xml, text/xml, text/plain"})
        requested = result.requested_urls or [result.url]
        if result.status in {301, 302, 303, 307, 308} or requested != [url] or result.url != url:
            raise CollectorFailure("blocked_by_policy", "acl anthology retrieval does not follow redirects")
        if result.status != 200:
            raise CollectorFailure("invalid_content", f"unexpected anthology status {result.status}")
        content_type = result.headers.get("content-type", "")
        if "pdf" in content_type.lower() or _looks_like_pdf(result.url):
            raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
        paper = parse_paper(result.body)
        if paper.anthology_id != paper_id or _looks_like_pdf(paper.canonical_url):
            raise CollectorFailure("invalid_content", "anthology id mismatch")
        return paper


def require_anthology_id(value: str) -> str:
    text = (value or "").strip()
    if _looks_like_pdf(text):
        raise CollectorFailure("blocked_by_policy", "pdf is not downloaded")
    if not _valid_id(text):
        raise CollectorFailure("invalid_content", "anthology id is not a paper id")
    return text


def metadata_url(anthology_id: str) -> str:
    """MODS XML URL for one anthology id. The path is ``.xml``, never ``.pdf``."""
    paper_id = require_anthology_id(anthology_id)
    url = f"https://{API_HOST}/{paper_id}.xml"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != f"/{paper_id}.xml":
        raise CollectorFailure("unsafe_url", "acl anthology retrieval stays on the mods xml file")
    if parsed.query or parsed.fragment or _looks_like_pdf(url):
        raise CollectorFailure("blocked_by_policy", "pdf is not downloaded")
    return url


def parse_paper(payload: bytes) -> AclAnthologyPaper:
    """Read one MODS record. Performs no I/O and does not fetch a PDF."""
    body = payload.lstrip(b"\xef\xbb\xbf \t\r\n")
    if body.lower().startswith(b"%pdf"):
        raise CollectorFailure("blocked_by_policy", "pdf body was not requested")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "acl anthology metadata exceeds limit")
    mods = _one_mods(_read_mods(payload))
    anthology_id = _anthology_id(mods)
    return AclAnthologyPaper(
        anthology_id=anthology_id,
        title=_title(mods),
        authors=_authors(mods),
        year=_year(mods),
        canonical_url=_paper_url(anthology_id),
        abstract=_abstract(mods),
    )


def _read_mods(payload: bytes):
    """Parse MODS bytes. DTD, entities, and parser failures stay invalid content."""
    if declares_xml_type(payload):
        raise CollectorFailure("invalid_content", "acl anthology metadata declares an xml type")
    try:
        return fromstring(payload)
    except XmlParseError as exc:
        raise CollectorFailure("invalid_content", f"malformed acl anthology metadata: {exc}") from exc
    except Exception as exc:
        # defusedxml rejects entities with its own exception type, not ParseError.
        raise CollectorFailure("invalid_content", f"malformed acl anthology metadata: {exc}") from exc


def _valid_id(value: str) -> bool:
    return bool(_NEW_ID.fullmatch(value) or _OLD_ID.fullmatch(value))


def _looks_like_pdf(value: str) -> bool:
    lowered = (value or "").lower().strip()
    if lowered.startswith("%pdf"):
        return True
    path = lowered.split("?", 1)[0].split("#", 1)[0]
    return path.endswith(".pdf") or "/pdf/" in path


def _one_mods(root) -> object:
    local = _local(root.tag)
    if local == "mods":
        return root
    if local != "modsCollection":
        raise CollectorFailure("invalid_content", "acl anthology payload is not mods metadata")
    papers = _direct_children(root, "mods")
    if len(papers) != 1:
        raise CollectorFailure("invalid_content", "expected exactly one anthology paper")
    return papers[0]


def _anthology_id(mods) -> str:
    found: list[str] = []
    for paper_id in _ids_from_locations(mods):
        if paper_id not in found:
            found.append(paper_id)
    doi_id = _id_from_doi(_identifier(mods, "doi"))
    if doi_id and doi_id not in found:
        found.append(doi_id)
    if not found:
        raise CollectorFailure("invalid_content", "anthology id is missing")
    if len(found) != 1:
        raise CollectorFailure("invalid_content", "anthology id mismatch")
    return found[0]


def _ids_from_locations(mods) -> list[str]:
    found: list[str] = []
    for location in _direct_children(mods, "location"):
        for url_el in _direct_children(location, "url"):
            paper_id = _id_from_anthology_url(_element_text(url_el))
            if paper_id:
                found.append(paper_id)
    return found


def _id_from_anthology_url(value: str) -> str | None:
    text = value.strip()
    if not text or (_looks_like_pdf(text) and not text.lower().startswith(("http://", "https://"))):
        return None
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() not in {"http", "https"} or host not in {API_HOST, f"www.{API_HOST}"}:
        return None
    if parsed.username or parsed.password:
        return None
    path = parsed.path.strip("/")
    lowered = path.lower()
    for suffix in _PDF_SUFFIXES:
        if lowered.endswith(suffix):
            path = path[: -len(suffix)]
            break
    if not path or "/" in path or not _valid_id(path):
        return None
    return path


def _id_from_doi(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    lowered = text.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            lowered = text.lower()
            break
    marker = "/v1/"
    index = lowered.rfind(marker)
    if index < 0:
        return None
    candidate = text[index + len(marker) :].strip().strip("/")
    if _valid_id(candidate):
        return candidate
    return None


def _identifier(mods, kind: str) -> str:
    for element in _direct_children(mods, "identifier"):
        if (element.get("type") or "").lower() != kind:
            continue
        text = _element_text(element)
        if text:
            return text
    return ""


def _paper_url(anthology_id: str) -> str:
    canonical = canonicalize_url(f"https://{API_HOST}/{anthology_id}")
    parsed = urlparse(canonical)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != f"/{anthology_id}":
        raise CollectorFailure("unsafe_url", "anthology canonical url left aclanthology.org")
    if parsed.query or parsed.fragment or _looks_like_pdf(canonical):
        raise CollectorFailure("blocked_by_policy", "pdf is not downloaded")
    return canonical


def _title(mods) -> str:
    for info in _direct_children(mods, "titleInfo"):
        if (info.get("type") or "").lower() in {"abbreviated", "translated"}:
            continue
        for title_el in _direct_children(info, "title"):
            text = _element_text(title_el)
            if not text:
                continue
            if len(text) > MAX_TITLE_CHARS:
                raise CollectorFailure("content_too_large", "acl anthology title exceeds limit")
            return text
    raise CollectorFailure("invalid_content", "acl anthology paper title is missing")


def _authors(mods) -> tuple[str, ...]:
    names: list[str] = []
    for name_el in _direct_children(mods, "name"):
        if (name_el.get("type") or "personal").lower() != "personal":
            continue
        if _role(name_el) != "author":
            continue
        name = _person_name(name_el)
        if not name:
            continue
        names.append(name)
        if len(names) > MAX_AUTHORS:
            raise CollectorFailure("content_too_large", "acl anthology author list exceeds limit")
    return tuple(names)


def _role(name_el) -> str:
    for role in _direct_children(name_el, "role"):
        for term in _direct_children(role, "roleTerm"):
            if (term.get("type") or "text").lower() not in {"text", ""}:
                continue
            text = _element_text(term).lower()
            if text:
                return text
    return ""


def _person_name(name_el) -> str:
    given: list[str] = []
    family: list[str] = []
    rest: list[str] = []
    for part in _direct_children(name_el, "namePart"):
        text = _element_text(part)
        if not text:
            continue
        kind = (part.get("type") or "").lower()
        if kind == "given":
            given.append(text)
        elif kind == "family":
            family.append(text)
        elif kind == "date":
            continue
        else:
            rest.append(text)
    name = " ".join([*given, *family, *rest])
    if len(name) > MAX_AUTHOR_NAME_CHARS:
        raise CollectorFailure("content_too_large", "acl anthology author name exceeds limit")
    return name


def _year(mods) -> int | str:
    for raw in (_path_text(mods, "originInfo", "dateIssued"), _path_text(mods, "part", "date")):
        year = _parse_year(raw)
        if year is not None:
            return year
    return UNKNOWN


def _parse_year(value: str) -> int | None:
    if not value:
        return None
    match = _ISSUED.fullmatch(value.strip())
    if not match:
        return None
    year = int(match.group("year"))
    if year < 1900 or year > 2100:
        return None
    month = match.group("month")
    if month is not None and not 1 <= int(month) <= 12:
        return None
    day = match.group("day")
    if day is not None and not 1 <= int(day) <= 31:
        return None
    return year


def _abstract(mods) -> str | None:
    found = [text for element in _direct_children(mods, "abstract") if (text := _element_text(element))]
    if not found:
        return None
    if len(found) > 1:
        raise CollectorFailure("invalid_content", "acl anthology record has multiple abstracts")
    text = found[0]
    if len(text) > MAX_ABSTRACT_CHARS:
        raise CollectorFailure("content_too_large", "acl anthology abstract exceeds limit")
    return text


def _path_text(element, *names: str) -> str:
    node = element
    for name in names:
        children = _direct_children(node, name)
        if not children:
            return ""
        node = children[0]
    return _element_text(node)


def _direct_children(element, name: str) -> list:
    return [child for child in list(element) if _local(child.tag) == name]


def _local(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag


def _element_text(element) -> str:
    return " ".join("".join(element.itertext()).split())

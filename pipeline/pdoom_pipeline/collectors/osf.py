"""OSF preprint and project metadata.

Reads one public preprint or project from the OSF API v2
(https://api.osf.io/v2/). Requests use a sparse fieldset so the description
is not asked for. Contributor names and the license name are separate
metadata reads. File endpoints, storage providers, and download links are
not requested.

A missing date or license stays ``unknown``. Each contributor stays a
separate name: identical names are kept, and name parts from different
contributors are not joined.

This module is not wired into the belief runner.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "osf-0.1.0"
API_ORIGIN = "https://api.osf.io"
UNKNOWN = "unknown"
MAX_RESPONSE_BYTES = 200_000
MAX_CONTRIBUTORS = 100
MAX_TITLE_CHARS = 2_000
MAX_NAME_CHARS = 300
MAX_LICENSE_CHARS = 200
MAX_DEPTH = 12

PREPRINT_FIELDS = "title,date_published,doi,public,is_published,contributors,license"
PROJECT_FIELDS = "title,date_created,public,category,node_license,contributors"
USER_FIELDS = "full_name,given_name,middle_names,family_name"
LICENSE_FIELDS = "name,url"

_PREPRINT_ID = re.compile(r"^[a-z0-9]{5}(?:_v[1-9]\d{0,2})?$")
_NODE_ID = re.compile(r"^[a-z0-9]{5}$")
_LICENSE_ID = re.compile(r"^[a-f0-9]{24}$")
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_FILE_EXTENSIONS = (
    ".pdf",
    ".zip",
    ".docx",
    ".doc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".tif",
    ".tiff",
    ".gz",
    ".tgz",
    ".csv",
    ".xlsx",
    ".xls",
    ".ppt",
    ".pptx",
    ".mp4",
    ".mp3",
    ".wav",
    ".svg",
)
_FILE_KEY = re.compile(r"^(?:file|media|content|primaryfile)bytes$")


@dataclass(frozen=True)
class OsfRecord:
    """Metadata kept for one public OSF preprint or project."""

    id: str
    title: str
    date: str
    contributors: tuple[str, ...]
    doi: str
    canonical_url: str
    license: str
    kind: str = "preprint"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "contributors": list(self.contributors),
            "doi": self.doi,
            "canonical_url": self.canonical_url,
            "license": self.license,
        }


class OsfCollector:
    """Retrieve one preprint or project. The default fetcher makes one attempt per metadata URL."""

    collector = "osf"
    platform = "osf"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/vnd.api+json", "application/json"),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, record_id: str, *, kind: str = "preprint") -> OsfRecord:
        """Fetch metadata for one id. Does not download files or the description."""
        kind = _require_kind(kind)
        record_id = _require_record_id(record_id, kind)
        record_url = project_request_url(record_id) if kind == "project" else preprint_request_url(record_id)
        preprint_doc = self._get_json(record_url)
        resource = _resource(preprint_doc)
        if resource.get("id") != record_id or _kind(resource) != kind:
            raise CollectorFailure("invalid_content", "osf id mismatch")
        _require_public(resource)
        contributors_doc = self._get_json(contributors_request_url(record_id, kind=kind))
        license_doc = None
        if kind == "preprint":
            license_id = _linked_license_id(resource)
            if license_id:
                license_doc = self._get_json(license_request_url(license_id))
        return _from_parts(preprint_doc, contributors_doc, license_doc)

    def parse(self, payload: bytes) -> OsfRecord:
        """Parse a saved metadata document. Performs no I/O."""
        document = _load_document(payload)
        if "preprint" in document or "project" in document:
            if "preprint" in document and "project" in document:
                raise CollectorFailure("invalid_content", "osf payload must be one record")
            key = "preprint" if "preprint" in document else "project"
            record_doc = document.get(key)
            if not isinstance(record_doc, dict):
                raise CollectorFailure("invalid_content", "osf payload must be one record")
            contributors = document.get("contributors")
            if contributors is None:
                contributors = {"data": []}
            if not isinstance(contributors, dict):
                raise CollectorFailure("invalid_content", "osf contributors were not a list")
            license_doc = document.get("license")
            if license_doc is not None and not isinstance(license_doc, dict):
                raise CollectorFailure("invalid_content", "osf license was not an object")
            return _from_parts(record_doc, contributors, license_doc)
        return _from_document(document)

    def _get_json(self, url: str) -> dict:
        _assert_metadata_url(url)
        result = self.fetcher.get(url, headers={"Accept": "application/vnd.api+json"})
        if result.requested_urls and result.requested_urls != [url]:
            raise CollectorFailure("blocked_by_policy", "refusing a redirected osf fetch")
        if result.status != 200:
            raise CollectorFailure("invalid_content", "osf metadata response was not usable")
        if _looks_like_file_target(result.url) or result.body.startswith((b"%PDF", b"PK\x03\x04", b"\x89PNG")):
            raise CollectorFailure("blocked_by_policy", "osf file bytes are not collected")
        return _load_document(result.body)


def preprint_request_url(record_id: str) -> str:
    record_id = _require_record_id(record_id, "preprint")
    return f"{API_ORIGIN}/v2/preprints/{record_id}/?fields[preprints]={PREPRINT_FIELDS}"


def project_request_url(record_id: str) -> str:
    record_id = _require_record_id(record_id, "project")
    return f"{API_ORIGIN}/v2/nodes/{record_id}/?fields[nodes]={PROJECT_FIELDS}"


def contributors_request_url(record_id: str, *, kind: str = "preprint") -> str:
    kind = _require_kind(kind)
    record_id = _require_record_id(record_id, kind)
    collection = "preprints" if kind == "preprint" else "nodes"
    return (
        f"{API_ORIGIN}/v2/{collection}/{record_id}/contributors/"
        f"?fields[users]={USER_FIELDS}&page[size]=100"
    )


def license_request_url(license_id: str) -> str:
    if not isinstance(license_id, str) or not _LICENSE_ID.fullmatch(license_id):
        raise CollectorFailure("invalid_content", "invalid osf license id")
    return f"{API_ORIGIN}/v2/licenses/{license_id}/?fields[licenses]={LICENSE_FIELDS}"


def _from_parts(record_doc: dict, contributors_doc: dict, license_doc: dict | None) -> OsfRecord:
    resource = _resource(record_doc)
    _require_public(resource)
    _reject_file_values(record_doc)
    _reject_file_values(contributors_doc)
    if license_doc is not None:
        _reject_file_values(license_doc)
    kind = _kind(resource)
    names = _contributor_names(contributors_doc)
    doi = _doi(resource)
    return OsfRecord(
        id=_record_id(resource, kind),
        title=_title(resource),
        date=_date(resource, kind),
        contributors=names,
        doi=doi,
        canonical_url=_canonical_url(resource, doi),
        license=_license_value(resource, license_doc, ()),
        kind=kind,
    )


def _from_document(document: dict) -> OsfRecord:
    resource = _resource(document)
    _require_public(resource)
    included = document.get("included")
    if included is None:
        included_items: list[dict] = []
    elif isinstance(included, list):
        if len(included) > MAX_CONTRIBUTORS + 5:
            raise CollectorFailure("content_too_large", "osf included list exceeds limit")
        included_items = [item for item in included if isinstance(item, dict)]
    else:
        raise CollectorFailure("invalid_content", "osf included resources were not a list")
    contributor_items = [item for item in included_items if item.get("type") == "contributors"]
    names = _names_from_items(contributor_items)
    doi = _doi(resource)
    kind = _kind(resource)
    return OsfRecord(
        id=_record_id(resource, kind),
        title=_title(resource),
        date=_date(resource, kind),
        contributors=names,
        doi=doi,
        canonical_url=_canonical_url(resource, doi),
        license=_license_value(resource, None, tuple(included_items)),
        kind=kind,
    )


def _load_document(payload: bytes) -> dict:
    if payload.startswith((b"%PDF", b"PK\x03\x04", b"\x89PNG", b"GIF8")):
        raise CollectorFailure("blocked_by_policy", "osf file bytes are not collected")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "osf payload exceeds limit")
    try:
        document = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed osf payload: {exc}") from exc
    if not isinstance(document, dict):
        raise CollectorFailure("invalid_content", "osf payload was not an object")
    _reject_file_values(document)
    if "errors" in document and "data" not in document and "preprint" not in document and "project" not in document:
        raise CollectorFailure("invalid_content", "osf error response")
    return document


def _resource(document: dict) -> dict:
    if document.get("type") in {"preprints", "nodes"} and isinstance(document.get("id"), str):
        resource = document
    else:
        data = document.get("data")
        if not isinstance(data, dict):
            raise CollectorFailure("invalid_content", "osf payload was not one record")
        resource = data
    if resource.get("type") not in {"preprints", "nodes"}:
        raise CollectorFailure("invalid_content", "osf type must be a preprint or project")
    if not isinstance(resource.get("id"), str):
        raise CollectorFailure("invalid_content", "osf id is missing")
    attributes = resource.get("attributes")
    if attributes is not None and not isinstance(attributes, dict):
        raise CollectorFailure("invalid_content", "osf attributes were not an object")
    return resource


def _kind(resource: dict) -> str:
    return "preprint" if resource.get("type") == "preprints" else "project"


def _record_id(resource: dict, kind: str) -> str:
    return _require_record_id(str(resource.get("id") or ""), kind)


def _require_kind(kind: str) -> str:
    if kind not in {"preprint", "project"}:
        raise CollectorFailure("invalid_content", "osf kind must be preprint or project")
    return kind


def _require_record_id(value: object, kind: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CollectorFailure("invalid_content", "invalid osf id")
    if _looks_like_file_target(value) or any(char in value for char in "/\\?#&"):
        raise CollectorFailure("blocked_by_policy", "osf files are not downloaded")
    if kind == "preprint" and _PREPRINT_ID.fullmatch(value):
        return value
    if kind == "project" and _NODE_ID.fullmatch(value):
        return value
    raise CollectorFailure("invalid_content", "invalid osf id")


def _require_public(resource: dict) -> None:
    attributes = resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}
    if attributes.get("public") is False:
        raise CollectorFailure("blocked_by_policy", "osf record is not public")
    if resource.get("type") == "preprints" and attributes.get("is_published") is False:
        raise CollectorFailure("blocked_by_policy", "osf preprint is not published")


def _title(resource: dict) -> str:
    attributes = resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}
    value = attributes.get("title")
    if not isinstance(value, str):
        raise CollectorFailure("invalid_content", "osf title is missing")
    title = " ".join(value.split())
    if not title or "\x00" in title:
        raise CollectorFailure("invalid_content", "osf title is missing")
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "osf title exceeds limit")
    return title


def _date(resource: dict, kind: str) -> str:
    attributes = resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}
    field = "date_published" if kind == "preprint" else "date_created"
    return _timestamp(attributes.get(field))


def _timestamp(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    if not text or len(text) > 40 or any(ord(char) < 32 for char in text):
        return UNKNOWN
    if _DATE_ONLY.fullmatch(text):
        try:
            datetime.fromisoformat(text)
        except ValueError:
            return UNKNOWN
        return text
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return UNKNOWN
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    if parsed.year < 1990 or parsed.year > 2100:
        return UNKNOWN
    if parsed.microsecond:
        fraction = f"{parsed.microsecond:06d}".rstrip("0")
        return parsed.strftime("%Y-%m-%dT%H:%M:%S") + f".{fraction}Z"
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _doi(resource: dict) -> str:
    attributes = resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}
    found = _extract_doi(attributes.get("doi"))
    if found:
        return found
    links = resource.get("links") if isinstance(resource.get("links"), dict) else {}
    for key in ("preprint_doi", "doi", "article_doi"):
        found = _extract_doi(links.get(key))
        if found:
            return found
    return UNKNOWN


def _extract_doi(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    lowered = text.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    text = text.strip().strip("/")
    if not _DOI.fullmatch(text) or _looks_like_file_target(text):
        return None
    return text


def _canonical_url(resource: dict, doi: str) -> str:
    links = resource.get("links") if isinstance(resource.get("links"), dict) else {}
    for key in ("html", "iri"):
        candidate = _osf_page_url(links.get(key))
        if candidate:
            return candidate
    if doi != UNKNOWN:
        try:
            canonical = canonicalize_url(f"https://doi.org/{doi}")
        except ValueError:
            canonical = ""
        parsed = urlparse(canonical)
        if parsed.hostname == "doi.org" and not _looks_like_file_target(canonical):
            return canonical
    raise CollectorFailure("invalid_content", "osf record has no canonical url")


def _osf_page_url(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip() or _looks_like_file_target(value):
        return None
    try:
        canonical = canonicalize_url(value.strip())
    except ValueError:
        return None
    parsed = urlparse(canonical)
    host = parsed.hostname or ""
    if host not in {"osf.io", "www.osf.io"}:
        return None
    if _looks_like_file_target(canonical):
        return None
    return canonical


def _contributor_names(document: dict) -> tuple[str, ...]:
    _assert_contributor_page_complete(document)
    data = document.get("data")
    if data is None:
        data = []
    if not isinstance(data, list):
        raise CollectorFailure("invalid_content", "osf contributors were not a list")
    return _names_from_items(data)


def _assert_contributor_page_complete(document: dict) -> None:
    links = document.get("links")
    if not isinstance(links, dict):
        return
    next_link = links.get("next")
    if isinstance(next_link, str) and next_link.strip():
        raise CollectorFailure("content_too_large", "osf contributor page is incomplete")
    meta = links.get("meta")
    data = document.get("data")
    count = len(data) if isinstance(data, list) else 0
    if isinstance(meta, dict):
        total = meta.get("total")
        if isinstance(total, int) and not isinstance(total, bool) and total > count:
            raise CollectorFailure("content_too_large", "osf contributor page is incomplete")


def _names_from_items(items: list) -> tuple[str, ...]:
    if len(items) > MAX_CONTRIBUTORS:
        raise CollectorFailure("content_too_large", "osf contributor list exceeds limit")
    ordered: list[tuple[tuple[int, int], dict]] = []
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if item.get("type") not in {None, "contributors"}:
            continue
        attributes = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
        index = attributes.get("index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index > 10_000:
            sort_key = (10_000, position)
        else:
            sort_key = (index, position)
        ordered.append((sort_key, item))
    ordered.sort(key=lambda pair: pair[0])
    names: list[str] = []
    for _key, item in ordered:
        name = _one_contributor_name(item)
        if not name:
            continue
        if len(name) > MAX_NAME_CHARS:
            raise CollectorFailure("content_too_large", "osf contributor name exceeds limit")
        names.append(name)
    return tuple(names)


def _one_contributor_name(contributor: dict) -> str:
    """One contributor record becomes one name. Neighboring records are not joined."""
    attributes = contributor.get("attributes") if isinstance(contributor.get("attributes"), dict) else {}
    user = _user_attributes(contributor)
    for source in (user, attributes):
        full_name = source.get("full_name")
        if isinstance(full_name, str) and full_name.strip():
            return _clean_name(full_name)
    parts: list[str] = []
    for key in ("given_name", "middle_names", "family_name"):
        piece = user.get(key)
        if not isinstance(piece, str) or not piece.strip():
            piece = attributes.get(key)
        if isinstance(piece, str):
            cleaned = " ".join(piece.split())
            if cleaned:
                parts.append(cleaned)
    if parts:
        return _clean_name(" ".join(parts))
    unregistered = attributes.get("unregistered_contributor")
    if isinstance(unregistered, str) and unregistered.strip():
        return _clean_name(unregistered)
    return ""


def _user_attributes(contributor: dict) -> dict:
    embeds = contributor.get("embeds")
    if not isinstance(embeds, dict):
        return {}
    users = embeds.get("users")
    if not isinstance(users, dict):
        return {}
    data = users.get("data")
    if not isinstance(data, dict):
        return {}
    attributes = data.get("attributes")
    return attributes if isinstance(attributes, dict) else {}


def _clean_name(value: str) -> str:
    name = " ".join(value.split())
    if "\x00" in name:
        return ""
    return name


def _license_value(resource: dict, license_doc: dict | None, included: tuple[dict, ...]) -> str:
    if license_doc is not None:
        return _license_from_document(license_doc)
    licenses = [item for item in included if item.get("type") == "licenses"]
    linked = _linked_license_id(resource)
    if linked:
        for item in licenses:
            if item.get("id") == linked:
                return _license_from_resource(item)
        return _project_node_license(resource)
    if len(licenses) == 1:
        return _license_from_resource(licenses[0])
    return _project_node_license(resource)


def _project_node_license(resource: dict) -> str:
    if _kind(resource) != "project":
        return UNKNOWN
    attributes = resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}
    return _license_from_value(attributes.get("node_license"))


def _license_from_document(document: dict) -> str:
    data = document.get("data")
    if data is None:
        return UNKNOWN
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "osf license was not an object")
    return _license_from_resource(data)


def _license_from_resource(resource: dict) -> str:
    if resource.get("type") not in {None, "licenses"}:
        return UNKNOWN
    attributes = resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}
    named = _license_text(attributes.get("name"))
    if named != UNKNOWN:
        return named
    return _license_text(attributes.get("url"))


def _license_from_value(value: object) -> str:
    if isinstance(value, dict):
        named = _license_text(value.get("name"))
        if named != UNKNOWN:
            return named
        return _license_text(value.get("url"))
    return _license_text(value)


def _license_text(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = " ".join(value.split())
    if not text or len(text) > MAX_LICENSE_CHARS or _looks_like_file_target(text):
        return UNKNOWN
    return text


def _linked_license_id(resource: dict) -> str | None:
    relationships = resource.get("relationships")
    if not isinstance(relationships, dict):
        return None
    license_rel = relationships.get("license")
    if not isinstance(license_rel, dict):
        return None
    data = license_rel.get("data")
    if not isinstance(data, dict):
        return None
    license_id = data.get("id")
    if isinstance(license_id, str) and _LICENSE_ID.fullmatch(license_id):
        return license_id
    return None


def _looks_like_file_target(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith("%pdf") or "files.osf.io" in lowered or "osfstorage" in lowered:
        return True
    if "/files/" in lowered or "/download" in lowered or "download=" in lowered:
        return True
    path = lowered.split("?", 1)[0].split("#", 1)[0]
    return path.endswith(_FILE_EXTENSIONS)


def _reject_file_values(value: object, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise CollectorFailure("content_too_large", "osf payload is too deep")
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and _FILE_KEY.fullmatch(key.lower().replace("_", "")):
                raise CollectorFailure("blocked_by_policy", "osf file bytes are not collected")
            _reject_file_values(item, depth + 1)
        return
    if isinstance(value, list):
        if len(value) > 500:
            raise CollectorFailure("content_too_large", "osf payload is too wide")
        for item in value:
            _reject_file_values(item, depth + 1)
        return
    if isinstance(value, str):
        stripped = value.lstrip()
        lowered = stripped.lower()
        if stripped.startswith("%PDF") or lowered.startswith("data:application/pdf") or lowered.startswith("data:application/octet-stream"):
            raise CollectorFailure("blocked_by_policy", "osf file bytes are not collected")


def _assert_metadata_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.osf.io" or parsed.username or parsed.password or parsed.fragment:
        raise CollectorFailure("unsafe_url", "osf retrieval stays on the api")
    if _looks_like_file_target(parsed.path) or _looks_like_file_target(parsed.query):
        raise CollectorFailure("blocked_by_policy", "osf files are not downloaded")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "v2":
        raise CollectorFailure("blocked_by_policy", "osf retrieval stays on metadata paths")
    collection, ident = parts[1], parts[2]
    expected: dict[str, str]
    if collection == "licenses":
        if len(parts) != 3 or not _LICENSE_ID.fullmatch(ident):
            raise CollectorFailure("blocked_by_policy", "osf retrieval stays on metadata paths")
        expected = {"fields[licenses]": LICENSE_FIELDS}
    elif collection in {"preprints", "nodes"}:
        id_pattern = _PREPRINT_ID if collection == "preprints" else _NODE_ID
        if not id_pattern.fullmatch(ident):
            raise CollectorFailure("blocked_by_policy", "osf retrieval stays on metadata paths")
        if len(parts) == 3:
            field_name = "fields[preprints]" if collection == "preprints" else "fields[nodes]"
            field_value = PREPRINT_FIELDS if collection == "preprints" else PROJECT_FIELDS
            expected = {field_name: field_value}
        elif len(parts) == 4 and parts[3] == "contributors":
            expected = {"fields[users]": USER_FIELDS, "page[size]": "100"}
        else:
            raise CollectorFailure("blocked_by_policy", "osf files are not downloaded")
    else:
        raise CollectorFailure("blocked_by_policy", "osf files are not downloaded")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if len(pairs) != len(dict(pairs)) or dict(pairs) != expected:
        raise CollectorFailure("blocked_by_policy", "osf query is not a metadata fieldset")

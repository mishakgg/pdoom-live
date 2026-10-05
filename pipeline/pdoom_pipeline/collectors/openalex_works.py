"""OpenAlex works collector keyed by a resolved author id.

Also confirms one fixed works search. OpenAlex metadata is CC0.
That search stores work metadata only and does not download PDFs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import arxiv_id_from_url, canonicalize_url

COLLECTOR_VERSION = "openalex-works-0.1.0"
API = "https://api.openalex.org/works"
MAX_ABSTRACT_POSITIONS = 4000

# One public query used to confirm works retrieval. Do not widen this search.
CATASTROPHIC_RISK_QUERY = "catastrophic risk from advanced AI"
CONFIRMED_PER_PAGE = 5
CONFIRMED_MAX_BYTES = 200_000
CONFIRMED_SELECT = "id,display_name,publication_year,authorships,primary_location,best_oa_location"

# OpenAlex license vocabulary: https://help.openalex.org/data/licenses/
# `cc0` is retained as an alias of `public-domain`. A missing license is not in this set.
OPEN_ACCESS_LICENSES = frozenset(
    {
        "cc-by",
        "cc-by-sa",
        "cc-by-nd",
        "cc-by-nc",
        "cc-by-nc-sa",
        "cc-by-nc-nd",
        "public-domain",
        "cc0",
        "mit",
        "apache-2-0",
        "gpl-v2",
        "gpl-v3",
        "isc",
        "other-oa",
        "publisher-specific-oa",
    }
)


class OpenAlexWorksCollector:
    collector = "openalex_works"
    platform = "openalex"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(allowed_content_types=("application/json",), max_bytes=2_000_000)

    def collect_author(self, *, source_identity: str, openalex_author_id: str, observed_at: str, per_page: int = 25) -> list[SourceObservation]:
        author_id = openalex_author_id.rstrip("/").split("/")[-1]
        if not author_id.startswith("A") or not author_id[1:].isdigit():
            raise CollectorFailure("invalid_content", "openalex author id must look like A123")
        if per_page < 1 or per_page > 50:
            raise CollectorFailure("invalid_content", "per_page must be between 1 and 50")
        query = urlencode(
            {
                "filter": f"authorships.author.id:{author_id}",
                "per-page": per_page,
                "sort": "publication_date:desc",
                "select": "id,display_name,publication_date,doi,ids,authorships,primary_location,abstract_inverted_index,language",
                "mailto": "collector@pdoom.live",
            }
        )
        result = self.fetcher.get(f"{API}?{query}")
        return self.parse(result.body, source_identity=source_identity, observed_at=observed_at)

    def retrieve_confirmed_query(self) -> list[OpenAlexWorkMetadata]:
        """Fetch metadata for the fixed catastrophic-risk query.

        The request is one bounded works search. PDF URLs in the payload are ignored.
        """
        result = self.fetcher.get(confirmed_search_url())
        if len(result.body) > CONFIRMED_MAX_BYTES:
            raise CollectorFailure("content_too_large", "openalex search response exceeds 200KB")
        return parse_work_metadata(result.body)

    def parse(self, payload: bytes, *, source_identity: str, observed_at: str) -> list[SourceObservation]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CollectorFailure("invalid_content", f"malformed openalex payload: {exc}") from exc
        works = data.get("results") if isinstance(data, dict) else None
        if not isinstance(works, list):
            raise CollectorFailure("invalid_content", "openalex response missing results")
        observations = []
        for work in works:
            if isinstance(work, dict):
                observations.append(_work(work, source_identity=source_identity, observed_at=observed_at))
        return observations


def _work(work: dict, *, source_identity: str, observed_at: str) -> SourceObservation:
    openalex_url = str(work.get("id") or "")
    work_id = openalex_url.rstrip("/").split("/")[-1]
    if not work_id.startswith("W"):
        raise CollectorFailure("invalid_content", "openalex work missing id")
    landing = ((work.get("primary_location") or {}) or {}).get("landing_page_url") or ""
    doi = work.get("doi") or ""
    canonical_source = landing or doi or openalex_url
    try:
        canonical = canonicalize_url(canonical_source)
    except ValueError:
        canonical = canonicalize_url(openalex_url)
    arxiv_id = arxiv_id_from_url(canonical)
    authors = []
    for authorship in work.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        name = str(author.get("display_name") or "").strip()
        if not name:
            continue
        authors.append(
            AuthorCandidate(
                name=name,
                role="author",
                attribution_method="openalex_authorship",
                confidence="high",
                person_id=None,
            )
        )
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    text, truncated = excerpt(abstract, 800)
    published = work.get("publication_date")
    published_at = f"{published}T00:00:00Z" if isinstance(published, str) and len(published) == 10 else None
    observation = SourceObservation(
        source_identity=source_identity,
        platform="openalex",
        upstream_id=work_id,
        canonical_url=canonical,
        observed_at=observed_at,
        published_at=published_at,
        author_candidates=authors,
        title=str(work.get("display_name") or "") or None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "upstream_version": work_id,
            "truncated": truncated,
            "openalex_url": canonicalize_url(openalex_url) if openalex_url else None,
            "doi": doi or None,
            "arxiv_id": arxiv_id,
            "language": work.get("language"),
        },
        collection_method="openalex_api",
        collector="openalex_works",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def reconstruct_abstract(inverted: object) -> str:
    if not inverted:
        return ""
    if not isinstance(inverted, dict):
        raise CollectorFailure("invalid_content", "abstract index is not an object")
    positions: list[tuple[int, str]] = []
    for token, indexes in inverted.items():
        if not isinstance(token, str) or not isinstance(indexes, list):
            raise CollectorFailure("invalid_content", "abstract index has an invalid token")
        if len(token) > 200:
            raise CollectorFailure("invalid_content", "abstract token exceeds limit")
        for index in indexes:
            if not isinstance(index, int) or index < 0 or index > MAX_ABSTRACT_POSITIONS:
                raise CollectorFailure("content_too_large", "abstract index position exceeds limit")
            positions.append((index, token))
    if len(positions) > MAX_ABSTRACT_POSITIONS:
        raise CollectorFailure("content_too_large", "abstract index exceeds token limit")
    positions.sort()
    return " ".join(token for _, token in positions)


@dataclass(frozen=True)
class OpenAlexWorkMetadata:
    """Work metadata retained from OpenAlex. OpenAlex records are CC0."""

    title: str
    year: int | None
    authorship: tuple[str, ...]
    open_access_license: str
    work_url: str
    license_code: str | None = None

    def __post_init__(self) -> None:
        if self.open_access_license not in {"open", "unknown"}:
            raise ValueError(f"invalid open-access license flag: {self.open_access_license}")


def confirmed_search_url() -> str:
    """URL for the single confirmed works search. It does not address a PDF."""
    query = urlencode(
        {
            "search": CATASTROPHIC_RISK_QUERY,
            "per-page": CONFIRMED_PER_PAGE,
            "select": CONFIRMED_SELECT,
            "mailto": "collector@pdoom.live",
        }
    )
    return f"{API}?{query}"


def parse_work_metadata(payload: bytes) -> list[OpenAlexWorkMetadata]:
    """Read title, year, authorship, license flag, and work URL from a works payload."""
    data = _json_object(payload)
    works = data.get("results")
    if not isinstance(works, list):
        raise CollectorFailure("invalid_content", "openalex response missing results")
    records: list[OpenAlexWorkMetadata] = []
    for work in works[:CONFIRMED_PER_PAGE]:
        if not isinstance(work, dict):
            continue
        record = _work_metadata(work)
        if record is not None:
            records.append(record)
    return records


def slim_confirmed_payload(payload: bytes, *, retrieved_at: str) -> dict:
    """Reduce a live works response to the retained metadata fields.

    PDF URLs, abstracts, and affiliation graphs are dropped. A null license is kept
    so a later parse can leave the open-access flag unknown.
    """
    data = _json_object(payload)
    works = data.get("results")
    if not isinstance(works, list):
        raise CollectorFailure("invalid_content", "openalex response missing results")
    results = []
    for work in works[:CONFIRMED_PER_PAGE]:
        if not isinstance(work, dict):
            continue
        record = _work_metadata(work)
        if record is None:
            continue
        results.append(
            {
                "id": record.work_url,
                "display_name": record.title,
                "publication_year": record.year,
                "authorships": [{"author": {"display_name": name}} for name in record.authorship],
                "primary_location": _license_location(work.get("primary_location")),
                "best_oa_location": _license_location(work.get("best_oa_location")),
            }
        )
    return {
        "query": CATASTROPHIC_RISK_QUERY,
        "source": API,
        "data_license": "CC0",
        "retrieved_at": retrieved_at,
        "pdfs_downloaded": False,
        "results": results,
    }


def open_access_license_flag(work: dict) -> tuple[str, str | None]:
    """Return ``open`` only when a recognized license code is present.

    ``open_access.is_oa`` is not a license. A missing license stays ``unknown``.
    """
    for key in ("best_oa_location", "primary_location"):
        code = _license_code(work.get(key))
        if code in OPEN_ACCESS_LICENSES:
            return "open", code
    return "unknown", None


def _json_object(payload: bytes) -> dict:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed openalex payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "openalex response missing results")
    return data


def _work_metadata(work: dict) -> OpenAlexWorkMetadata | None:
    work_url = _work_url(work.get("id"))
    title = work.get("display_name")
    if not work_url or not isinstance(title, str) or not title.strip():
        return None
    year = work.get("publication_year")
    if isinstance(year, bool) or not isinstance(year, int) or year < 1000 or year > 3000:
        year = None
    flag, code = open_access_license_flag(work)
    return OpenAlexWorkMetadata(
        title=title.strip(),
        year=year,
        authorship=tuple(_author_names(work.get("authorships"))),
        open_access_license=flag,
        work_url=work_url,
        license_code=code,
    )


def _work_url(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        canonical = canonicalize_url(value.strip())
    except ValueError:
        return None
    work_id = canonical.rstrip("/").split("/")[-1]
    if not (work_id.startswith("W") and work_id[1:].isdigit()):
        return None
    return canonical


def _author_names(authorships: object) -> list[str]:
    if not isinstance(authorships, list):
        return []
    names: list[str] = []
    for authorship in authorships:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author")
        if not isinstance(author, dict):
            continue
        name = author.get("display_name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


def _license_location(location: object) -> dict[str, str | None] | None:
    if not isinstance(location, dict):
        return None
    raw = location.get("license")
    code = raw.strip() if isinstance(raw, str) and raw.strip() else None
    return {"license": code}


def _license_code(location: object) -> str | None:
    if not isinstance(location, dict):
        return None
    raw = location.get("license")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    license_id = location.get("license_id")
    if isinstance(license_id, str) and "/licenses/" in license_id.lower():
        code = license_id.rstrip("/").split("/")[-1].strip().lower()
        if code:
            return code
    return None

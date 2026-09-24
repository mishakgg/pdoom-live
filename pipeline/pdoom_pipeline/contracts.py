"""Shared ingestion records.

Field names follow docs/DATA_MODEL.md and docs/ARCHITECTURE.md so a Python
collector and a TypeScript product can exchange the same objects.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pdoom_pipeline.hashing import observation_fingerprint

STATEMENT_TYPES = ("explicit_numeric", "explicit_qualitative", "model_inferred_signal")
REVIEW_STATES = ("unreviewed", "machine_validated", "human_verified", "rejected", "needs_review")
PARTICIPANT_ROLES = ("author", "speaker", "guest", "interviewer", "publisher", "mentioned")
PERSON_STATUSES = ("active", "historical", "review")
INCLUSION_REASONS = (
    "frontier_lab_researcher",
    "frontier_model_author",
    "frontier_safety_eval",
    "academic_forecasting",
    "former_frontier_researcher",
)
CONFIDENCE_LEVELS = ("high", "medium", "low", "unknown")

SOURCE_TYPES = (
    "personal_website",
    "rss",
    "lab_page",
    "research_paper",
    "preprint",
    "podcast",
    "youtube",
    "github",
    "huggingface",
    "bluesky",
    "mastodon",
    "x",
    "conference_talk",
    "testimony",
    "press",
    "newsletter",
    "openalex_works",
    "other",
)

COLLECTABLE_SOURCE_TYPES = frozenset({"rss", "preprint", "github", "openalex_works"})


@dataclass
class AuthorCandidate:
    name: str
    role: str
    attribution_method: str
    confidence: str
    person_id: str | None = None

    def __post_init__(self) -> None:
        if self.role not in PARTICIPANT_ROLES:
            raise ValueError(f"invalid participant role: {self.role}")


@dataclass
class Segment:
    segment_kind: str
    sequence: int
    text: str
    start_char: int | None = None
    end_char: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None

    @property
    def segment_hash(self) -> str:
        from pdoom_pipeline.hashing import content_hash

        return content_hash({"kind": self.segment_kind, "sequence": self.sequence, "text": self.text})


@dataclass
class SourceObservation:
    source_identity: str
    platform: str
    upstream_id: str | None
    canonical_url: str
    observed_at: str
    published_at: str | None
    author_candidates: list[AuthorCandidate]
    title: str | None
    segments: list[Segment]
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    collection_method: str = ""
    collector: str = ""
    collector_version: str = ""

    def finalize_hash(self) -> "SourceObservation":
        self.content_hash = observation_fingerprint(
            title=self.title,
            texts=[segment.text for segment in self.segments],
            published_at=self.published_at,
            upstream_version=str(self.metadata.get("upstream_version") or ""),
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def excerpt(text: str, limit: int = 1500) -> tuple[str, bool]:
    """Keep a short evidence excerpt. Full copyrighted bodies are not retained."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned, False
    return cleaned[:limit], True

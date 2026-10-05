"""Classify a license URL or token for copying a work.

The classifier does not fetch the URL. A public web page is not a license.
CC0, CC-BY, and CC-BY-SA are copyable. CC-BY-ND is recorded as unchanged-only
and is not marked copyable. The arXiv non-exclusive distribution license is
recognized and is not copyable. A missing, blank, or unrecognized value stays
unknown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

CC0 = "cc0"
CC_BY = "cc-by"
CC_BY_SA = "cc-by-sa"
CC_BY_ND = "cc-by-nd"
ARXIV_NONEXCLUSIVE = "arxiv-nonexclusive-distrib-1.0"

_COPYABLE = frozenset({CC0, CC_BY, CC_BY_SA})
_UNCHANGED_ONLY = frozenset({CC_BY_ND})
_NOT_COPYABLE = frozenset({ARXIV_NONEXCLUSIVE})

_VERSION = r"\d+\.\d+"
_TOKEN_FAMILIES = (
    (re.compile(rf"^cc-?0(?:-{_VERSION})?$"), CC0),
    (re.compile(rf"^cc-by-nd(?:-{_VERSION})?$"), CC_BY_ND),
    (re.compile(rf"^cc-by-sa(?:-{_VERSION})?$"), CC_BY_SA),
    (re.compile(rf"^cc-by(?:-{_VERSION})?$"), CC_BY),
)
_CC_LICENSE_CODES = {"by": CC_BY, "by-sa": CC_BY_SA, "by-nd": CC_BY_ND}
_VERSION_PART = re.compile(rf"{_VERSION}\Z")
_DEED_PART = re.compile(r"(?:legalcode|deed)(?:[.-][a-z0-9]+)*\Z")
_BARE_LICENSE_HOSTS = (
    "creativecommons.org/",
    "www.creativecommons.org/",
    "arxiv.org/",
    "www.arxiv.org/",
    "spdx.org/",
    "www.spdx.org/",
)


@dataclass(frozen=True)
class CopyingLicense:
    """One local classification of a license string.

    ``copyable`` is true only when copying is allowed without an
    unchanged-work condition. CC-BY-ND sets ``unchanged_only`` instead, so
    checking ``copyable`` alone is not a yes.
    """

    license_id: str | None
    known: bool
    copyable: bool
    unchanged_only: bool

    def __post_init__(self) -> None:
        if self.known != (self.license_id is not None):
            raise ValueError("known must match license_id")
        if self.copyable and self.unchanged_only:
            raise ValueError("unchanged_only is not a silent copyable yes")
        if (self.copyable or self.unchanged_only) and not self.known:
            raise ValueError("an unknown license is not copyable")

    def allows_copy(self, *, unchanged: bool = False) -> bool:
        """Return whether a copy is permitted.

        CC-BY-ND returns true only when ``unchanged`` is true.
        """

        if self.copyable:
            return True
        return self.unchanged_only and unchanged


_UNKNOWN = CopyingLicense(license_id=None, known=False, copyable=False, unchanged_only=False)


def classify_license(value: str | None) -> CopyingLicense:
    """Classify a license URL or token. This does not contact the network."""

    if not isinstance(value, str):
        return _UNKNOWN
    text = value.strip()
    if not text:
        return _UNKNOWN
    if _is_url_like(text):
        return _classified(_family_from_url(text))
    return _classified(_family_from_token(_normalize_token(text)))


def _classified(license_id: str | None) -> CopyingLicense:
    if license_id in _COPYABLE:
        return CopyingLicense(license_id, True, True, False)
    if license_id in _UNCHANGED_ONLY:
        return CopyingLicense(license_id, True, False, True)
    if license_id in _NOT_COPYABLE:
        return CopyingLicense(license_id, True, False, False)
    return _UNKNOWN


def _normalize_token(value: str) -> str:
    text = value.strip().lower().replace("_", " ")
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    if text.endswith("+"):
        text = text[:-1].strip("-")
    return text


def _family_from_token(normalized: str) -> str | None:
    for pattern, family in _TOKEN_FAMILIES:
        if pattern.fullmatch(normalized):
            return family
    return None


def _is_url_like(text: str) -> bool:
    if "://" in text or text.startswith("//"):
        return True
    lowered = text.lower()
    return lowered.startswith(_BARE_LICENSE_HOSTS)


def _family_from_url(text: str) -> str | None:
    candidate = text.strip()
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    elif "://" not in candidate:
        candidate = "https://" + candidate
    try:
        parsed = urlsplit(candidate)
        hostname = parsed.hostname
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return None
    host = hostname.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = [part.lower() for part in parsed.path.split("/") if part]
    if host == "creativecommons.org":
        return _family_from_creativecommons(parts)
    if host == "arxiv.org":
        if parts == ["licenses", "nonexclusive-distrib", "1.0"]:
            return ARXIV_NONEXCLUSIVE
        return None
    if host == "spdx.org":
        return _family_from_spdx(parts)
    return None


def _family_from_creativecommons(parts: list[str]) -> str | None:
    if (
        len(parts) >= 3
        and parts[0] == "publicdomain"
        and parts[1] == "zero"
        and _VERSION_PART.fullmatch(parts[2])
    ):
        if _deed_suffix(parts[3:]):
            return CC0
        return None
    if len(parts) >= 3 and parts[0] == "licenses" and _VERSION_PART.fullmatch(parts[2]):
        family = _CC_LICENSE_CODES.get(parts[1])
        if family is not None and _deed_suffix(parts[3:]):
            return family
    return None


def _family_from_spdx(parts: list[str]) -> str | None:
    if len(parts) != 2 or parts[0] != "licenses":
        return None
    identifier = parts[1]
    if identifier.endswith(".html"):
        identifier = identifier[:-5]
    return _family_from_token(identifier)


def _deed_suffix(rest: list[str]) -> bool:
    if not rest:
        return True
    return len(rest) == 1 and _DEED_PART.fullmatch(rest[0]) is not None

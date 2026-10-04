"""Visible text from a public HTML or markdown page.

Script and style bodies are discarded. Page text is data, not instructions.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlparse


class _VisibleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
            if not self._skip:
                self.text_parts.append("\n")
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "br", "tr", "blockquote"} and not self._skip:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)


def article_text(payload: str, *, max_chars: int = 80_000) -> str:
    raw = payload or ""
    if "<html" in raw[:2000].lower() or "<p" in raw[:2000].lower() or "<div" in raw[:2000].lower():
        parser = _VisibleParser()
        parser.feed(raw[:1_500_000])
        parser.close()
        text = "".join(parser.text_parts)
    else:
        text = raw
        text = re.sub(r"\*\*", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"</?[a-zA-Z][^>]*>", " ", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)[:max_chars]


def page_title(html: str) -> str | None:
    parser = _VisibleParser()
    parser.feed((html or "")[:200_000])
    parser.close()
    title = " ".join(" ".join(parser.title_parts).split())
    return title[:300] or None


_STAMP = re.compile(
    r"(?P<date>20\d{2}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}:\d{2})(?P<fraction>\.\d+)?(?P<zone>Z|[+-]\d{2}:\d{2})?"
)
COLLECTOR_PRODUCT = "pdoom.live-collector"


def parse_published(raw: str) -> dict[str, str | None]:
    """Return a UTC instant only when the source states a zone.

    A clock time with no offset stays unzoned. It is not labeled Z.
    """
    found = _find_timestamp(raw)
    if found is None:
        return {"utc": None, "timezone": None, "unzoned": None}
    date, clock, zone = found
    if not zone:
        return {"utc": None, "timezone": None, "unzoned": f"{date}T{clock}"}
    utc = _to_utc(date, clock, zone)
    if utc is None:
        return {"utc": None, "timezone": None, "unzoned": f"{date}T{clock}"}
    return {"utc": utc, "timezone": zone, "unzoned": None}


def published_time(raw: str) -> str | None:
    return parse_published(raw)["utc"]


def published_timezone(raw: str) -> str | None:
    return parse_published(raw)["timezone"]


def _find_timestamp(raw: str) -> tuple[str, str, str | None] | None:
    patterns = [
        r'article:published_time"\s+content="([^"]+)"',
        r'content="([^"]+)"\s+property="article:published_time"',
        r'<time[^>]+datetime="([^"]+)"',
        r'"datePublished"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw or "", flags=re.I)
        if match:
            return _split_stamp(match.group(1))
    head = (raw or "")[:2500]
    match = _STAMP.search(head)
    if match and match.group("zone"):
        return match.group("date"), match.group("time"), match.group("zone")
    return None


def _split_stamp(value: str) -> tuple[str, str, str | None] | None:
    match = _STAMP.search(value.strip())
    if not match:
        return None
    return match.group("date"), match.group("time"), match.group("zone")


def _to_utc(date: str, clock: str, zone: str) -> str | None:
    from datetime import datetime, timedelta

    try:
        local = datetime.strptime(f"{date}T{clock}", "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    if zone == "Z":
        return local.strftime("%Y-%m-%dT%H:%M:%SZ")
    offset = re.match(r"(?P<sign>[+-])(?P<hours>\d{2}):(?P<minutes>\d{2})$", zone)
    if not offset:
        return None
    minutes = int(offset.group("hours")) * 60 + int(offset.group("minutes"))
    if offset.group("sign") == "-":
        minutes = -minutes
    utc = local - timedelta(minutes=minutes)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def page_authors(raw: str) -> list[str]:
    """Author signals from metadata. A name in the article body is not an author."""
    names: list[str] = []
    patterns = [
        r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']author["\']',
        r'<meta[^>]+property=["\']article:author["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']article:author["\']',
        r'<a[^>]+rel=["\']author["\'][^>]*>([^<]+)</a>',
    ]
    for pattern in patterns:
        names.extend(re.findall(pattern, raw or "", flags=re.I))
    for match in re.finditer(r'"author"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\}|"[^"]+")', raw or "", flags=re.I):
        blob = match.group(1)
        if blob.startswith('"'):
            names.append(blob.strip('"'))
            continue
        name = re.search(r'"name"\s*:\s*"([^"]+)"', blob)
        if name:
            names.append(name.group(1))
    cleaned: list[str] = []
    for name in names:
        text = " ".join(name.split())
        if text and text not in cleaned:
            cleaned.append(text[:200])
    return cleaned


def title_byline(title: str | None) -> str | None:
    match = re.match(r"^(.{2,80}?)\s+[—–\-|:]\s+\S", title or "")
    if not match:
        return None
    return " ".join(match.group(1).split())


def page_language(raw: str) -> str | None:
    match = re.search(r"<html[^>]*\blang=[\"']([A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?)", raw or "", flags=re.I)
    if not match:
        return None
    return match.group(1)


def robots_allows(body: str, path: str, user_agent: str = COLLECTOR_PRODUCT) -> bool:
    """Apply the collector product group, then the * group, per robots group rules."""
    text = body or ""
    if "<html" in text[:500].lower():
        return True
    groups = _robots_groups(text)
    if not groups:
        return True
    rules = _matching_rules(groups, user_agent)
    if rules is None:
        return True
    return _path_allowed(rules, path or "/")


def _robots_groups(text: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules:
                flush()
            agents.append(value.lower())
            continue
        if key in {"allow", "disallow"} and agents:
            rules.append((key, value))
    flush()
    return groups


def _matching_rules(groups: list[tuple[list[str], list[tuple[str, str]]]], user_agent: str) -> list[tuple[str, str]] | None:
    product = (user_agent or "").split("/", 1)[0].strip().lower()
    haystack = (user_agent or "").strip().lower()
    specific: list[tuple[int, list[tuple[str, str]]]] = []
    wildcard: list[tuple[str, str]] | None = None
    for agents, rules in groups:
        for agent in agents:
            if agent == "*":
                wildcard = rules
                continue
            if product.startswith(agent) or (haystack.startswith(agent) and agent):
                specific.append((len(agent), rules))
    if specific:
        return max(specific, key=lambda item: item[0])[1]
    return wildcard


def _path_allowed(rules: list[tuple[str, str]], path: str) -> bool:
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix:
            continue
        if path.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()

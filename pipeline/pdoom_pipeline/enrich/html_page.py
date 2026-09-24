"""HTML is parsed as data. Script and style bodies are not executed or followed."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from pdoom_pipeline.identity.names import name_key
from pdoom_pipeline.ingest.participants import mentioned
from pdoom_pipeline.urls import canonicalize_url

GITHUB_RESERVED = {
    "about",
    "apps",
    "collections",
    "customer-stories",
    "enterprise",
    "events",
    "explore",
    "features",
    "github",
    "issues",
    "login",
    "marketplace",
    "orgs",
    "pricing",
    "pulls",
    "security",
    "settings",
    "signup",
    "sponsors",
    "topics",
}
HF_RESERVED = {
    "blog",
    "chat",
    "datasets",
    "docs",
    "join",
    "login",
    "models",
    "organizations",
    "papers",
    "posts",
    "privacy",
    "spaces",
    "settings",
}
BLOCKED_HOSTS = {
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "wikipedia.org",
    "wikimedia.org",
    "wikidata.org",
    "researchgate.net",
}

PODCAST_HOSTS = {
    "anchor.fm",
    "podcasts.apple.com",
    "open.spotify.com",
    "transistor.fm",
    "libsyn.com",
    "megaphone.fm",
    "simplecast.com",
    "buzzsprout.com",
    "podbean.com",
}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag in {"a", "link"} and attr.get("href"):
            self.links.append({"tag": tag, "rel": attr.get("rel", ""), "type": attr.get("type", ""), "href": attr["href"]})

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_title:
            self.title_parts.append(data)
        if len(self.text_parts) < 4000:
            self.text_parts.append(data)


def strip_markup(value: str) -> str:
    parser = _PageParser()
    parser.feed((value or "")[:100_000])
    parser.close()
    return " ".join(" ".join(parser.text_parts).split())


def parse_html(html: str, *, page_url: str) -> dict:
    parser = _PageParser()
    parser.feed(html[:1_000_000])
    parser.close()
    text = " ".join(" ".join(parser.text_parts).split())[:20_000]
    title = " ".join(" ".join(parser.title_parts).split())[:300]
    absolute_links = []
    for link in parser.links:
        href = urljoin(page_url, link["href"].strip())
        absolute_links.append({**link, "href": href})
    return {"title": title, "text": text, "links": absolute_links}


def page_confirms_person(text: str, display_name: str, variants: list[str] | None = None) -> bool:
    for name in [display_name, *(variants or [])]:
        if name_key(name) and mentioned(text, name):
            return True
    return False


def discover_feeds(links: list[dict[str, str]]) -> list[str]:
    found: list[str] = []
    for link in links:
        rel = link.get("rel", "").lower().split()
        type_ = link.get("type", "").lower()
        href = link.get("href", "")
        if "alternate" in rel and href and any(token in type_ for token in ("rss", "atom", "xml")):
            if href not in found:
                found.append(href)
    return found


def rel_me_profiles(links: list[dict[str, str]]) -> list[dict]:
    profiles = []
    seen = set()
    for link in links:
        rel = set(link.get("rel", "").lower().split())
        if "me" not in rel:
            continue
        classified = classify_profile_url(link.get("href", ""))
        if classified is None:
            continue
        key = (classified["namespace"], classified["external_id"])
        if key in seen:
            continue
        seen.add(key)
        profiles.append(classified)
    return profiles


def classify_profile_url(url: str) -> dict | None:
    try:
        canonical = canonicalize_url(url)
    except ValueError:
        return None
    parsed = urlparse(canonical)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host == "github.com" and len(parts) == 1 and parts[0].lower() not in GITHUB_RESERVED:
        user = parts[0]
        return {"namespace": "github", "external_id": user, "canonical_url": f"https://github.com/{user}", "handle": user}
    if host in {"huggingface.co", "www.huggingface.co"} and len(parts) == 1 and parts[0].lower() not in HF_RESERVED:
        user = parts[0]
        return {"namespace": "huggingface", "external_id": user, "canonical_url": f"https://huggingface.co/{user}", "handle": user}
    if host == "bsky.app" and len(parts) == 2 and parts[0] == "profile":
        handle = parts[1]
        return {"namespace": "bluesky", "external_id": handle, "canonical_url": f"https://bsky.app/profile/{handle}", "handle": handle}
    if host in {"x.com", "twitter.com", "www.twitter.com", "www.x.com"} and len(parts) == 1 and parts[0].lower() not in {"share", "intent", "home", "search", "i"}:
        handle = parts[0]
        return {"namespace": "x", "external_id": handle, "canonical_url": f"https://x.com/{handle}", "handle": handle}
    if host in {"www.youtube.com", "youtube.com"} and len(parts) == 2 and parts[0] == "channel" and parts[1].startswith("UC"):
        channel = parts[1]
        return {"namespace": "youtube", "external_id": channel, "canonical_url": f"https://www.youtube.com/channel/{channel}", "handle": channel}
    if host in {"www.youtube.com", "youtube.com"} and len(parts) == 1 and parts[0].startswith("@"):
        handle = parts[0]
        return {"namespace": "youtube", "external_id": handle, "canonical_url": f"https://www.youtube.com/{handle}", "handle": handle}
    if parts and parts[0].startswith("@") and host not in {"x.com", "twitter.com", "www.twitter.com", "www.x.com"}:
        handle = parts[0][1:]
        return {"namespace": "mastodon", "external_id": f"{handle}@{host}", "canonical_url": canonical, "handle": handle}
    return None


def host_is_blocked(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == item or host.endswith("." + item) for item in BLOCKED_HOSTS)


def feed_is_acceptable(url: str) -> bool:
    if host_is_blocked(url):
        return False
    parsed = urlparse(url)
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    if "oembed" in path or "special:recentchanges" in path or "special%3arecentchanges" in query:
        return False
    if "recentchanges" in query or "title=special" in query:
        return False
    return True


def is_generic_homepage(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or ""
    return path in {"", "/"}


def source_type_for_url(url: str, *, feeds: bool = False) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("substack.com"):
        return "newsletter"
    if any(host == item or host.endswith("." + item) for item in PODCAST_HOSTS):
        return "podcast"
    if "youtube.com" in host or host == "youtu.be":
        return "youtube"
    if feeds:
        return "rss"
    return "personal_website"


def youtube_feed_url(profile: dict) -> str | None:
    if profile.get("namespace") != "youtube":
        return None
    external_id = str(profile.get("external_id") or "")
    if external_id.startswith("UC"):
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={external_id}"
    return None

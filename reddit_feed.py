"""Temporary, low-volume first-party Reddit RSS pilot (until 2026-11-13).

No API scraping, OAuth bypass, relays, comments, user profiles or AI training.
If Reddit discontinues RSS or blocks the runner, fail visibly and leave direct links.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RETIRES_AT = dt.datetime(2026, 11, 13, tzinfo=dt.timezone.utc).timestamp()
REFRESH_SECONDS = 6 * 3600
MAX_AGE_SECONDS = 7 * 86400
STALE_SECONDS = 24 * 3600
MAX_POSTS_PER_COMMUNITY = 15
ATOM = "{http://www.w3.org/2005/Atom}"
COMMUNITIES = (
    ("LocalLLaMA", "AI"),
    ("technology", "Технології"),
    ("ChatGPT", "AI"),
    ("ukraine", "Україна"),
    ("Polska", "Польща"),
    ("ImmigrationCanada", "Імміграція"),
    ("UXDesign", "Дизайн"),
    ("movies", "Кіно"),
    ("MovieSuggestions", "Кіно"),
)
USER_AGENT = "PulseNews/0.1 (personal RSS preview; https://github.com/coldman2022/pulse-news)"


def _post_url(raw: str, community: str) -> str:
    """Only expose subreddit comment links, never arbitrary outbound destinations."""
    try:
        p = urllib.parse.urlsplit(raw)
        if p.scheme != "https" or (p.hostname or "").lower() not in (
                "www.reddit.com", "reddit.com", "old.reddit.com"):
            return ""
        if not re.match(r"^/r/" + re.escape(community) + r"/comments/[a-z0-9]+(?:/|$)",
                        p.path, re.IGNORECASE):
            return ""
        return urllib.parse.urlunsplit(("https", "www.reddit.com", p.path, "", ""))
    except ValueError:
        return ""


def parse_atom(raw: bytes, community: str, topic: str, now: float) -> list[dict]:
    root = ET.fromstring(raw)
    if root.tag != ATOM + "feed":
        raise ValueError("Reddit did not return an Atom feed")
    posts = []
    for entry in root.findall(ATOM + "entry")[:35]:
        title = html.unescape("".join(entry.findtext(ATOM + "title") or "")).strip()
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title))[:240]
        link = ""
        for node in entry.findall(ATOM + "link"):
            if node.get("rel", "alternate") == "alternate":
                link = _post_url(node.get("href", ""), community)
                if link:
                    break
        updated = entry.findtext(ATOM + "updated") or entry.findtext(ATOM + "published") or ""
        try:
            stamp = dt.datetime.fromisoformat(updated.replace("Z", "+00:00")).timestamp()
        except ValueError:
            try:
                stamp = email.utils.parsedate_to_datetime(updated).timestamp()
            except (ValueError, TypeError):
                continue
        if not title or not link or not (now - MAX_AGE_SECONDS <= stamp <= now + 300):
            continue
        posts.append({
            "id": hashlib.sha256(link.encode()).hexdigest()[:20],
            "title": title,
            "url": link,
            "community": community,
            "topic": topic,
            "published": stamp,
        })
        if len(posts) >= MAX_POSTS_PER_COMMUNITY:
            break
    return posts


def _fetch_one(community: str, topic: str, now: float) -> list[dict]:
    url = "https://www.reddit.com/r/" + community + "/new/.rss?limit=25"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml,application/xml;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=6) as response:
        raw = response.read(350001)
    if len(raw) > 350000:
        raise ValueError("Oversized Reddit RSS response")
    return parse_atom(raw, community, topic, now)


def build_reddit_preview(destination: str | Path, now: float | None = None) -> dict:
    path = Path(destination)
    now = time.time() if now is None else now
    prior = {}
    if path.exists():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    if now >= RETIRES_AT:
        result = {
            "status": "ended", "updated": now, "last_fetch_at": 0,
            "posts": [], "sources": [],
            "message": "Reddit припинив підтримку RSS. Дивіться спільноти за прямими посиланнями.",
        }
    elif (prior.get("last_fetch_at", 0) > now - REFRESH_SECONDS
          and prior.get("status") == "ok"):
        result = prior
    else:
        posts = []
        statuses = []
        for community, topic in COMMUNITIES:
            try:
                found = _fetch_one(community, topic, now)
                statuses.append({"community": community, "ok": True, "count": len(found)})
                posts.extend(found)
            except (OSError, ValueError, ET.ParseError) as error:
                statuses.append({"community": community, "ok": False, "count": 0})
                print("Reddit RSS not available for r/" + community + ": " + type(error).__name__)
        unique = {post["url"]: post for post in posts}
        posts = sorted(unique.values(), key=lambda p: p["published"], reverse=True)[:100]
        if not posts and prior.get("status") == "ok" and now - prior.get("updated", 0) < STALE_SECONDS:
            result = dict(prior, status="cached", last_fetch_at=now,
                          message="Нові дописи тимчасово недоступні; показано збережені.")
        else:
            result = {
                "status": "ok" if posts else "unavailable",
                "updated": now,
                "last_fetch_at": now,
                "posts": posts, "sources": statuses,
                "message": "" if posts else "Reddit RSS тимчасово не відповідає або блокує запити GitHub.",
            }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
    print("Reddit pilot:", result["status"], "posts:", len(result["posts"]),
          "working:", sum(bool(s["ok"]) for s in result["sources"]))
    return result

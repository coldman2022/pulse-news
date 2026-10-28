"""Build a source-linked digest from RSS excerpts, not an LLM-generated news report.

The digest is a rolling last-24-hours briefing. It is regenerated on each
existing hourly RSS build, without API keys, extra GitHub jobs, or invented facts.
"""
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import re
from urllib.parse import urlsplit

SECTIONS = (
    ("Світ", "Що відбувається у світі", 8),
    ("Імміграція", "Імміграція та правила", 5),
    ("AI", "Розвиток AI", 5),
    ("AI-події", "Конференції та події", 3),
)
WINDOW_SECONDS = 24 * 3600


def normalized_title(value):
    # Google News often adds " - Publisher"; strip it for exact-news duplicates.
    text = (value or "").strip()
    text = re.sub(r"\s+-\s+[^-]{2,55}$", "", text)
    return " ".join(re.findall(r"[\w]+", text.casefold(), re.UNICODE))


def brief_summary(value, max_chars=265):
    """Keep publisher-supplied wording; never invent a synthesis."""
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def useful_origin(article):
    origin = article.get("origin", "media")
    return {"official": 5, "developer": 4, "media": 3,
            "research": 3, "expert": 2, "discovery": 1}.get(origin, 0)


def build_digest(articles, now):
    stamp = float(now)
    grouped = []
    used_urls = set()
    # Each section gets its own bounded publisher mix.
    for category, heading, limit in SECTIONS:
        candidates = [
            a for a in articles
            if a.get("category") == category
            and a.get("title")
            and a.get("url")
            and urlsplit(a["url"]).scheme == "https"
            and isinstance(a.get("published"), (int, float))
            and stamp - WINDOW_SECONDS <= a["published"] <= stamp + 120
        ]
        candidates.sort(key=lambda a: (
            useful_origin(a), a.get("published", 0)
        ), reverse=True)
        chosen, seen_titles, publisher_count = [], set(), Counter()
        discovery_count = 0
        for a in candidates:
            title_key = normalized_title(a.get("title"))
            publisher = (a.get("publisher") or a.get("source") or "Без назви").strip()
            if len(title_key) < 8 or title_key in seen_titles or a["url"] in used_urls:
                continue
            if publisher_count[publisher] >= 2:
                continue
            if a.get("origin") == "discovery" and discovery_count >= 3:
                continue
            summary = brief_summary(a.get("summary"))
            item = {
                "id": a.get("id") or a["url"],
                "title": a["title"],
                "summary": summary,
                "url": a["url"],
                "publisher": publisher,
                "origin": a.get("origin", "media"),
                "language": a.get("language", "en"),
                "published": a["published"],
            }
            chosen.append(item)
            publisher_count[publisher] += 1
            seen_titles.add(title_key)
            used_urls.add(a["url"])
            discovery_count += (a.get("origin") == "discovery")
            if len(chosen) >= limit:
                break
        grouped.append({"category": category, "heading": heading, "items": chosen})
    when = datetime.fromtimestamp(stamp, ZoneInfo("Europe/Warsaw"))
    return {
        "date": when.date().isoformat(),
        "timezone": "Europe/Warsaw",
        "generated": stamp,
        "period_hours": 24,
        "method": "publisher_rss_excerpts",
        "disclaimer": "Добірка заголовків і RSS-описів. Не є автоматичною перевіркою фактів або AI-підсумком подій.",
        "sections": grouped,
        "total": sum(len(group["items"]) for group in grouped),
    }

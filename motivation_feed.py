"""Source-linked founder journeys, not generic success slogans or invented quotes."""
import re
from urllib.parse import urlsplit

MAX_ITEMS = 90
HISTORY_DAYS = 120

# This is deliberately narrower than a broad startup or business feed.
FOUNDER = re.compile(
    r"\bfounder(?:s|ship)?\b|\bco-?founder\b|\bentrepreneur(?:s|ship)?\b|"
    r"\bbootstrapp\w*|\bstarted (?:a |the |his |her |their )?(?:company|business|startup)|"
    r"\bbuilt (?:a |the |his |her |their )?(?:company|business|startup|brand)|"
    r"\bfrom scratch\b|\bmy (?:startup|business|company)\b|"
    r"засновник\w*|засновниц\w*|підприєм\w*|створив бізнес|створила бізнес|"
    r"założyciel\w*|przedsiębior\w*|zbudował firmę", re.I
)
JOURNEY = re.compile(
    r"\bjourney\b|\bstory\b|\bstories\b|\bstarted\b|\bbuilt\b|"
    r"\bstruggl\w*|\bfail\w*|\bsetback\w*|\breject\w*|\bdebt\b|"
    r"\bgrit\b|\bpivot\w*|\brebuild\w*|\blesson\w*|"
    r"\binterview\b|\bhow i\b|\bhow we\b|\blearned\b|"
    r"\bturn(?:ed|ing)? .* into\b|\bafter years\b|\bfrom .* to\b|"
    r"\bbootstrapp\w*|\bresilien\w*|\bmistake\w*|"
    r"шлях|історі\w*|помилк\w*|невдач\w*|відмов\w*|"
    r"досвід|з нуля|років|року|"
    r"droga\b|historia\b|trudnośc\w*|porażk\w*|", re.I
)
PROMOTIONAL = re.compile(
    r"\bapply now\b|\bsale\b|\bcoupon\b|\bdiscount\b|"
    r"\bjoin our\b|\bwebinar\b|\bjob opening\b|"
    r"\bfunding round\b|\braised \$|\bseries [abc]\b|"
    r"\b10x your\b|\bget rich\b|\bpassive income\b|"
    r"\bsecret hack\b|\bguaranteed success\b", re.I
)
FAILURE = re.compile(r"fail\w*|setback\w*|reject\w*|struggl\w*|mistake\w*|"
                     r"rebuild\w*|debt|помилк\w*|невдач\w*|відмов\w*", re.I)
IDEA = re.compile(r"idea\w*|launc\w*|built|started|bootstrapp\w*|"
                  r"з нуля|іде\w*|створи\w*|запуст\w*", re.I)


def select_journeys(articles, updated):
    """Use only actual publisher articles, with unchanged RSS excerpts."""
    chosen, seen = [], set()
    source_count = {}
    for article in sorted(articles, key=lambda a: a.get("published") or 0, reverse=True):
        if article.get("category") != "Мотивація":
            continue
        title = (article.get("title") or "").strip()
        summary = (article.get("summary") or "").strip()
        url = article.get("url") or ""
        published = article.get("published") or 0
        if not title or url in seen or urlsplit(url).scheme != "https":
            continue
        if not isinstance(published, (int, float)) or published <= 0:
            continue
        if published > updated + 3600 or updated - published > HISTORY_DAYS * 86400:
            continue
        if PROMOTIONAL.search(title):
            continue
        # A founder subject and a meaningful step or obstacle are both required.
        combined = title + " " + summary
        if not FOUNDER.search(combined) or not JOURNEY.search(combined):
            continue
        publisher = article.get("publisher") or article.get("source") or ""
        if source_count.get(publisher, 0) >= 28:
            continue
        source_count[publisher] = source_count.get(publisher, 0) + 1
        seen.add(url)
        tag = ("Після невдач" if FAILURE.search(combined)
               else "Ідея та запуск" if IDEA.search(combined)
               else "Шлях засновника")
        chosen.append(dict(article, story_type=tag))
        if len(chosen) >= MAX_ITEMS:
            break
    return chosen


def build_motivation_feed(articles, updated):
    stories = select_journeys(articles, updated)
    return {
        "updated": updated,
        "articles": stories,
        "selected_total": len(stories),
        "method": "founder_journey_headline_and_publisher_rss",
        "note": "Тільки реальні публікації із джерелами та RSS-анонсами. Цитати й біографії не вигадуються."
    }

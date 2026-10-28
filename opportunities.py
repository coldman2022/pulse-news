"""Conservative classification of immigration *announcements*, not legal eligibility.

Produces actionable review cards from existing Pulse RSS articles.
A card never claims applications are open or invents eligibility/deadlines.
"""
from urllib.parse import urlsplit
import re

OFFICIAL_HOSTS = (
    "canada.ca", "gov.uk", "gov.pl", "europa.eu", "uscis.gov",
    "gov.au", "homeaffairs.gov.au", "immigration.govt.nz",
    "govt.nz", "gov.pt",
)

TOPIC = re.compile(
    r"immigra|migration|migrant|visa\b|visas\b|residen|permanent resident|"
    r"work permit|study permit|citizenship|naturaliz|asylum|refugee|"
    r"express entry|blue card|sponsor|temporary protection|"
    r"pobyt|pobytu|cudzoziem|zezwolenie|wiza\b|wizy\b|"
    r"імміграц|міграц|біжен|дозвіл на проживання|візов",
    re.IGNORECASE
)
SIGNALS = (
    ("Заявки та реєстрація",
     re.compile(r"applications? (?:are )?(?:open|begin|start)|opening (?:for )?applications?|"
                r"accepting applications?|intake (?:open|opens|begins)|"
                r"nabór wniosk|przyjmowan.* wniosk|rozpoczę.* nabor|"
                r"прийом заяв|відкрит.* подач|старт.* подач", re.I)),
    ("Нова програма",
     re.compile(r"new (?:immigration |visa |residenc\w* |work permit |migration )?"
                r"(?:program|programme|pathway|stream|visa|permit|route|scheme)|"
                r"launch(?:es|ed|ing)? (?:a |the )?(?:new )?(?:program|programme|"
                r"pathway|visa|immigration|residenc\w*|migration)|"
                r"introduc(?:es|ed|ing) (?:a |the )?(?:new )?(?:visa|program|pathway|stream)|"
                r"nowy program|nowa wiza|nowe ścieżki|нова програм|нов[ийаі] віз", re.I)),
    ("Закриття або призупинення",
     re.compile(r"clos(?:es|ed|ing) (?:the )?(?:visa|program|pathway|stream)|"
                r"suspend(?:s|ed|ing)? (?:the )?(?:visa|program|applications)|"
                r"закрит.* програм|призупин.* програм|zawieszen.* program|"
                r"zamknięc.* program", re.I)),
    ("Зміни правил",
     re.compile(r"\bchang(?:e|es|ed|ing)\b|\bupdat(?:e|es|ed|ing)\b|"
                r"\breform\b|\bextend(?:s|ed|ing)?\b|\bexpand(?:s|ed|ing)?\b|"
                r"\bnew rules?\b|policy changes?|rule changes?|"
                r"zmian[ayę]|nowe zasady|przedłużen|"
                r"змін[аи]|оновлен|продовжен|розширен", re.I)),
)
SPECULATIVE = re.compile(
    r"\b(?:rumou?r|speculat(?:ion|es?|ing)|may|might|could|proposal|proposed|"
    r"plans? to|considering|opinion|what if|should)\b|"
    r"можлив[аеиі]|планує|пропонують|rozważa|projekt ustawy",
    re.IGNORECASE
)
COUNTRY_HINTS = (
    ("Канада", re.compile(r"\bcanada\b|\bcanadian\b|\bIRCC\b|\bExpress Entry\b", re.I)),
    ("Польща", re.compile(r"\bpoland\b|\bpolish\b|\bpolska\b|\bpolski\b|\bPESEL\b|\bCUKR\b", re.I)),
    ("Велика Британія", re.compile(r"\bUK\b|\bBritain\b|\bBritish\b|\bUnited Kingdom\b|\bUKVI\b", re.I)),
    ("США", re.compile(r"\bUSCIS\b|\bUSA\b|\bU\.S\.\b|\bUnited States\b", re.I)),
    ("Австралія", re.compile(r"\bAustralia\b|\bAustralian\b", re.I)),
    ("Нова Зеландія", re.compile(r"\bNew Zealand\b", re.I)),
    ("Португалія", re.compile(r"\bPortugal\b|\bPortuguese\b", re.I)),
    ("Італія", re.compile(r"\bItaly\b|\bItalian\b", re.I)),
    ("ЄС", re.compile(r"\bEU\b|\bEuropean Union\b|\bBlue Card\b", re.I)),
)


def official_url(url):
    parsed = urlsplit(url or "")
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and any(
        host == d or host.endswith("." + d) for d in OFFICIAL_HOSTS
    )


def country_for(article):
    # The targeted search's country is a search filter, not evidence
    # that the referenced policy really applies to that country.
    if article.get("origin") == "official":
        name = article.get("country", "")
        if name and name != "Світ":
            return name
    title = article.get("title", "")
    matches = [name for name, pattern in COUNTRY_HINTS if pattern.search(title)]
    if len(matches) == 1:
        return matches[0]
    return "Не визначено"


def classify_article(article):
    if article.get("category") != "Імміграція":
        return None
    title = (article.get("title") or "").strip()
    if not title or not TOPIC.search(title):
        return None
    signal = next((label for label, pattern in SIGNALS if pattern.search(title)), None)
    if signal is None:
        return None
    url = article.get("url") or ""
    if urlsplit(url).scheme != "https":
        return None

    first_party = article.get("origin") == "official" and official_url(url)
    speculative = bool(SPECULATIVE.search(title))
    # Claims about a newspaper or search hit must never become "verified".
    evidence = "офіційне повідомлення" if first_party else "потребує перевірки"
    if speculative:
        evidence = "потребує перевірки"
    return {
        "id": article.get("id") or url,
        "title": title,
        "url": url,
        "summary": (article.get("summary") or "")[:600],
        "country": country_for(article),
        "source": article.get("publisher") or article.get("source") or "Джерело",
        "source_type": article.get("origin") or "media",
        "signal": signal,
        "evidence": evidence,
        "published": article.get("published") or 0,
        "requirements": None,
        "application_start": None,
        "deadline": None,
        "applications_open": None,
    }


def make_opportunities(articles):
    items = []
    urls = set()
    for article in articles:
        record = classify_article(article)
        if record and record["url"] not in urls:
            items.append(record)
            urls.add(record["url"])
    items.sort(key=lambda x: (x["evidence"] != "офіційне повідомлення",
                              -(x["published"] or 0)))
    return items[:500]

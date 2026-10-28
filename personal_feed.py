"""Conservative, transparent prioritization for the personal Pulse front page.

No LLM, no added RSS/API requests. Feed is editorial relevance triage, not
verification of laws or a guarantee that every important update was found.
The complete news.json remains available separately.
"""
from collections import Counter
import re
from urllib.parse import urlsplit
import migration_relevance

WINDOW_HOURS = 168
FEATURED_LIMITS = {"Імміграція": 18, "AI": 20, "Польща": 10, "Дизайн": 6, "Україна": 25, "Кіно": 8}
BRIEF_LIMITS = {"Світ": 6, "Технології": 7, "Україна": 4,
                "Бізнес": 3, "Наука": 2, "AI-події": 3,
                "Імміграція": 8, "AI": 10, "Польща": 5, "Дизайн": 4, "Кіно": 8}
MAX_FEATURED = 72
MAX_BRIEF = 40

IMMIGRATION = re.compile(
    r"immigra\w*|migracj\w*|migrant\w*|residen\w*|resydencj\w*|"
    r"pobyt\w*|obywatel\w*|citizenship|naturaliz\w*|"
    r"visa\w*|wiz[ay]\w*|permit\w*|zezwolen\w*|"
    r"refugee\w*|uchodźc\w*|uchodz\w*|біжен\w*|"
    r"імміграц\w*|міграц\w*|громадянств\w*|віз\w*|"
    r"резидент\w*|посвідк\w*|дозвіл на проживан\w*|"
    r"temporary protection|ochron[ay] czasow\w*|тимчасов\w* захист|"
    r"pesel|cukr|karta pobytu|ukr status|status ukr|"
    r"work permit|prawo do pracy|prawo pobytu", re.I)
UKRAINIAN = re.compile(r"ukrain\w*|ukraiń\w*|україн\w*|украин\w*", re.I)
POLISH = re.compile(r"poland|polish|polsk\w*|polsc\w*|польщ\w*|польс\w*", re.I)
LAW_CHANGE = re.compile(
    r"law\w*|regulat\w*|legislat\w*|act\b|rule\w*|policy|"
    r"reform\w*|amend\w*|restrict\w*|extend\w*|expir\w*|"
    r"deadline\w*|eligib\w*|application\w*|visa\w*|"
    r"ban\b|bill\b|court\w*|deport\w*|"
    r"prawo\b|ustaw\w*|przepis\w*|zmian\w*|noweliz\w*|"
    r"wprowad\w*|przedłuż\w*|przedluz\w*|wydłuż\w*|"
    r"termin\w*|wniosk\w*|decyzj\w*|wyrok\w*|zakaz\w*|"
    r"закон\w*|правил\w*|постанова\w*|зміни\w*|"
    r"продовж\w*|заборон\w*|строк\w*|термін\w*|"
    r"подав\w*|заяв\w*|депортац\w*|права\b|"
    r"rights?\b|discriminat\w*|дискримінац\w*", re.I)
AI_CORE = re.compile(
    r"\bai\b|artificial intelligence|generative|"
    r"\bllm\b|chatgpt|openai|claude|anthropic|gemini|"
    r"deepmind|mistral|deepseek|gpt[-\s]?\d|"
    r"neural|machine learning|нейромереж\w*|"
    r"штучн\w* інтелект|sztuczn\w* inteligencj\w*|"
    r"multimodal|\bagents?\b|агент\w* ші", re.I)
AI_MAJOR = re.compile(
    r"releas\w*|launch\w*|unveil\w*|introduc\w*|"
    r"announce\w*|rollout|roll out|model\w*|"
    r"breakthrough|reasoning|capabilit\w*|"
    r"open.source|regulat\w*|policy|safety|"
    r"price\w*|pricing|available|access|"
    r"випуст\w*|запуск\w*|оновлен\w*|"
    r"нов\w* модел\w*|оголос\w*|"
    r"premier\w*|wprowad\w*|now\w* model\w*", re.I)
WORLD_MAJOR = re.compile(
    r"election\w*|president\w*|prime minister|parliament\w*|"
    r"government\w*|minister\w*|europ\w* union|"
    r"\beu\b|\bnato\b|\bun\b|"
    r"war\b|invasion|ceasefire|peace deal|"
    r"sanction\w*|treaty|tariff\w*|"
    r"recession|central bank|interest rate\w*|"
    r"referendum|constitution\w*|"
    r"wybor\w*|prezydent\w*|rząd\w*|rzad\w*|"
    r"wojn\w*|rozejm|sankcj\w*|"
    r"вибор\w*|президент\w*|уряд\w*|"
    r"парламент\w*|війна\b|вторгнен\w*|перемир\w*|"
    r"санкц\w*|мирн\w* угод\w*", re.I)
TECH_CORE = re.compile(
    r"apple|microsoft|google|nvidia|amd|intel|"
    r"iphone|android|windows|chip\w*|semiconduct\w*|"
    r"robot\w*|satellite\w*|quantum|cybersecur\w*|"
    r"data breach|privacy|processor\w*|"
    r"смартфон\w*|робот\w*|процесор\w*|"
    r"злам\w*|витік даних|"
    r"smartfon\w*|komputer\w*", re.I)
TECH_MAJOR = re.compile(
    r"launch\w*|releas\w*|unveil\w*|"
    r"announc\w*|breakthrough|first\b|"
    r"ban\b|regulat\w*|critical|"
    r"major|security|vulnerabilit\w*|"
    r"випуст\w*|презент\w*|"
    r"запуск\w*|прорив|нов\w*|"
    r"premier\w*|wprowad\w*", re.I)
DESIGN_CORE = re.compile(
    r"figma|adobe|product design|design system|"
    r"ux\b|ui\b|user experience|webflow|"
    r"дизайн\w*|проєктуван\w*|projektowan\w*", re.I)
CRIME_NOISE = re.compile(
    r"murder\w*|homicid\w*|stabb\w*|"
    r"shooting\w*|killed in|found dead|"
    r"rape\w*|robbery|"
    r"morderstw\w*|zabójstw\w*|zabojstw\w*|"
    r"zabity\w*|zabójc\w*|"
    r"вбивств\w*|вбивц\w*|зґвалтуван\w*", re.I)
LIFESTYLE_NOISE = re.compile(
    r"celebrity|royal wedding|horoscope|astrolog\w*|"
    r"football|soccer|premier league|"
    r"recipe|fashion week|box office|"
    r"recipe|actor\w*|gossip|"
    r"гороскоп\w*|рецепт\w*|"
    r"przepis kulinarny|plotk\w*", re.I)


def _title(article):
    return (article.get("title") or "").casefold()


def classify(article):
    """Return (tier, score) from title/category; suppressed stories return (None, 0)."""
    category = article.get("category") or ""
    title = _title(article)
    if not title:
        return None, 0
    # Exclude routine murders, violent-crime and lifestyle stories even when
    # they mention Poland or refugees; they remain in the full archive.
    if CRIME_NOISE.search(title) or (category != 'Кіно' and LIFESTYLE_NOISE.search(title)):
        return None, 0
    if category == "Імміграція":
        scope = migration_relevance.migration_scope(article)
        if scope == "ukrainian":
            return "featured", 18 + int(article.get("origin") == "official")
        if scope == "general":
            return ("featured", 11) if LAW_CHANGE.search(title) else ("brief", 5)
        return None, 0
    has_immigration = bool(IMMIGRATION.search(title))
    law = bool(LAW_CHANGE.search(title))
    rights = bool(UKRAINIAN.search(title) or POLISH.search(title) or "pesel" in title or "cukr" in title)
    if has_immigration and (law or rights):
        # Rights/immigration updates must outrank crime-noise patterns.
        return "featured", 15 + int(article.get("origin") == "official")
    if category == "Польща" and law and rights:
        return "featured", 14
    if category in ("Польща", "Світ", "Україна") and (CRIME_NOISE.search(title) or LIFESTYLE_NOISE.search(title)):
        return None, 0

    if category == "Україна":
        return "featured", 9
    if category == "Кіно":
        if re.search(r"best movies|best films|top \d+|movies to watch|what to watch|підбірк\w*|добірк\w*", title):
            return "featured", 7
        return "brief", 4
    if category == "AI":
        relevant = bool(AI_CORE.search(title))
        if relevant and AI_MAJOR.search(title):
            return "featured", 10 + int(article.get("origin") == "developer")
        if article.get("origin") == "developer" and AI_MAJOR.search(title):
            return "featured", 10
        if relevant:
            return "brief", 5
        return None, 0
    if category == "Дизайн":
        if DESIGN_CORE.search(title) and TECH_MAJOR.search(title):
            return "featured", 8
        return ("brief", 4) if DESIGN_CORE.search(title) else (None, 0)
    if category == "Польща":
        if law and (has_immigration or UKRAINIAN.search(title)):
            return "featured", 13
        if WORLD_MAJOR.search(title) and (law or POLISH.search(title)):
            return "brief", 5
        return None, 0
    if category in ("Світ", "Україна"):
        if WORLD_MAJOR.search(title):
            return "brief", 6 if category == "Україна" else 5
        return None, 0
    if category == "Технології":
        if AI_CORE.search(title) and AI_MAJOR.search(title):
            return "brief", 7
        if TECH_CORE.search(title) and TECH_MAJOR.search(title):
            return "brief", 5
        return None, 0
    if category == "Бізнес":
        return ("brief", 5) if TECH_CORE.search(title) and (TECH_MAJOR.search(title) or WORLD_MAJOR.search(title)) else (None, 0)
    if category == "Наука":
        return ("brief", 4) if (AI_CORE.search(title) or TECH_CORE.search(title)) and TECH_MAJOR.search(title) else (None, 0)
    if category == "AI-події":
        # Events calendar is first-class; RSS mentions remain only secondary.
        return ("brief", 3) if re.search(r"summit|conference|keynote|конференц\w*|sammit|konferencj\w*", title) else (None, 0)
    return None, 0


STOP = {"the", "and", "for", "with", "from", "that", "this", "are", "will",
        "about", "after", "into", "says", "said", "на", "про", "для", "від", "щодо",
        "oraz", "jest", "nie", "się", "sie", "przez", "new", "новий", "нова"}


def _signature(title):
    # Remove publisher suffix from discovery headlines; compare articles by subject.
    title = re.sub(r"\s+-\s+[^-]{2,55}$", "", title or "")
    return {token for token in re.findall(r"[\w]+", title.casefold(), re.UNICODE)
            if len(token) >= 3 and token not in STOP}


def _similar(signature, seen):
    if not signature:
        return False
    for previous in seen:
        common = len(signature & previous)
        union = len(signature | previous)
        if (common >= 4 and union and common / union >= .72) or signature == previous:
            return True
    return False


def _select(candidates, limits, overall_limit, used):
    chosen = []
    by_category, by_publisher, signatures = Counter(), Counter(), []
    for score, article in sorted(candidates, key=lambda pair: (
            pair[0], pair[1].get("published", 0)), reverse=True):
        category = article.get("category") or ""
        if category not in limits or by_category[category] >= limits[category]:
            continue
        url = article.get("url")
        if url in used:
            continue
        publisher = (article.get("publisher") or article.get("source") or "").casefold()
        if by_publisher[publisher] >= (5 if article.get("origin") == "official" else 3):
            continue
        signature = _signature(article.get("title"))
        if _similar(signature, signatures):
            continue
        chosen.append(article)
        used.add(url)
        signatures.append(signature)
        by_publisher[publisher] += 1
        by_category[category] += 1
        if len(chosen) >= overall_limit:
            break
    return sorted(chosen, key=lambda a: a.get("published", 0), reverse=True)


def build_personal_feed(articles, now):
    """Keep small source-linked outputs. Full news.json is untouched."""
    candidates = {"featured": [], "brief": []}
    for article in articles:
        url = article.get("url") or ""
        published = article.get("published") or 0
        if (urlsplit(url).scheme != "https" or not isinstance(published, (float, int))
                or published <= 0 or published > now + 120
                or now - published > WINDOW_HOURS * 3600):
            continue
        tier, score = classify(article)
        if tier:
            candidates[tier].append((score, article))
    used = set()
    featured = _select(candidates["featured"], FEATURED_LIMITS, MAX_FEATURED, used)
    brief = _select(candidates["brief"], BRIEF_LIMITS, MAX_BRIEF, used)
    # Browser-only reactions reselect from this bounded editorial pool. Every
    # candidate has already passed the existing relevance and age checks.
    # Do not upload personal preferences to the published JSON.
    pool = [
        dict(article, relevance_score=score)
        for score, article in sorted(
            candidates["featured"], key=lambda pair: pair[1].get("published", 0),
            reverse=True
        )[:180]
    ]
    return {
        "updated": now, "window_hours": WINDOW_HOURS,
        "method": "transparent_keyword_rules+optional_local_reactions",
        "disclaimer": "Персональна добірка за заголовками, не повна картина і не юридична перевірка. Усі новини доступні окремо.",
        "featured": featured, "brief": brief, "candidates": pool,
        "featured_count": len(featured), "brief_count": len(brief)
    }

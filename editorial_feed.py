"""Broad editorial feed: substantial coverage without routine crime, corruption or irrelevant visas.

The complete source archive remains untouched in news.json. This is a conservative
headline-and-RSS-category filter, not fact checking or legal eligibility advice.
"""
import re
import personal_feed
import migration_relevance
import story_clusters

NOISE = re.compile(
    r"корупц\w*|коррупц\w*|хабар\w*|крадіж\w*|затриман\w*|"
    r"зґвалтуван\w*|вбивств\w*|убийств\w*|злочин\w*|затрим\w*|"
    r"корупцій\w*|зловживан\w*|скандал\w*|"
    r"corrupt\w*|briber\w*|fraud\w*|embezzl\w*|"
    r"murder\w*|homicid\w*|stabbed|stabbing|"
    r"police arrest\w*|arrested|kidnapp\w*|robbery|"
    r"korupcj\w*|łapówk\w*|lapowk\w*|"
    r"zabójstw\w*|zabojstw\w*|kradzież\w*|kradziez\w*|"
    r"aresztowa\w*|zatrzyma\w*|gwałt\w*|gwalt\w*|"
    r"celebrity gossip|horoscope|astrolog\w*|"
    r"royal wedding|wedding dress|"
    r"гороскоп\w*|плітк\w*|plotk\w*", re.I
)
# A national migration-rights reform can mention "arrests" or "deportations",
# but the personal reader is not requesting crime blotters. Only structural
# migration policy should be included.
IMMIGRATION_SYSTEM = re.compile(
    r"віз\w*|громадянств\w*|посвідк\w*|дозвіл\w*|"
    r"легалізац\w*|прав[ао]\s+на\s+(пра|прожив)|"
    r"visa\w*|residen\w*|citizenship|naturaliz\w*|"
    r"pobyt\w*|zezwolen\w*|obywatel\w*|"
    r"asylum|refugee\w*|temporary protection|"
    r"PESEL|CUKR|UKR status|work permit|"
    r"settlement|"
    r"express entry|green card|blue card|"
    r"migrant\w*|cudzoziemc\w*|przedłuż\w*", re.I
)
SPECIFIC_OTHER_NATIONALITY = re.compile(
    r"\b(?:indian|pakistani|nigerian|bangladeshi|"
    r"nepalese|filipino|afghan|haitian|venezuelan|"
    r"syrian|somali|iranian|iraqi|mexican|"
    r"tunisian|algerian)\s+(?:nationals?|citizens?|students?|"
    r"workers?|refugees?|migrants?)\b|"
    r"\b(?:obywatele|obywateli)\s+(?:indii|pakistanu|bangladeszu)\b", re.I
)
TARGET_COUNTRIES = {
    "", "Польща", "Канада", "ЄС", "Велика Британія", "США",
    "Німеччина", "Чехія", "Словаччина", "Румунія", "Італія",
    "Угорщина", "Австрія", "Португалія"
}
POLAND_RELEVANT = re.compile(
    r"ustaw\w*|prawo\b|przepis\w*|noweliz\w*|reform\w*|"
    r"podatek\w*|podatk\w*|pracy\b|pracownik\w*|"
    r"pobyt\w*|cudzoziemc\w*|ukraiń\w*|"
    r"rząd\w*|wybor\w*|inflacj\w*|płac\w*|"
    r"świadczeni\w*|zdrow\w*|szkoł\w*|"
    r"czynsz\w*|mieszkani\w*|emerytur\w*|"
    r"transport\w*|energia\b|cen[ay]\b|"
    r"закон\w*|україн\w*|пенсі\w*|"
    r"робот\w*|права\b|вартіст\w*|"
    r"immigra\w*|residen\w*|regulat\w*|"
    r"government\w*|policy|tax\w*|benefit\w*|"
    r"housing|wage\w*|healthcare|inflation|"
    r"election\w*", re.I
)
WORLD_IMPORTANT = re.compile(
    r"election\w*|referendum|parliament\w*|"
    r"government\w*|president\w*|prime minister|"
    r"war\b|invasion|ceasefire|peace\b|"
    r"sanction\w*|treaty|tariff\w*|trade deal|"
    r"econom\w*|inflation|recession|"
    r"central bank|interest rate\w*|"
    r"disaster\w*|earthquake\w*|hurricane\w*|"
    r"evacuat\w*|flood\w*|climate agreement|"
    r"\beu\b|nato|united nations|"
    r"rząd\w*|prezydent\w*|wybor\w*|wojn\w*|"
    r"світов\w*|вибор\w*|президент\w*|"
    r"уряд\w*|війна\b|перемир\w*|"
    r"санкц\w*|економік\w*|землетрус\w*", re.I
)
TECH_INTEREST = re.compile(
    r"AI\b|artificial intelligence|robot\w*|"
    r"chip\w*|semiconduct\w*|processor\w*|"
    r"iphone|ipad|android|windows|"
    r"apple|google|microsoft|nvidia|amd|intel|"
    r"smartphone|laptop|quantum|satellite|"
    r"spacecraft|cybersecur\w*|"
    r"security update|data breach|privacy|"
    r"breakthrough|launch\w*|release\w*|"
    r"робот\w*|штучн\w* інтелект|"
    r"технолог\w*|процесор\w*|витік даних|"
    r"nowy procesor|sztuczna inteligencja", re.I
)
MOVIE_NEWS = re.compile(
    r"movie\w*|film\w*|cinema|screening|"
    r"release date|premiere|trailer|"
    r"movie review|film review|movies to watch|"
    r"films to watch|what to watch|"
    r"best movies|best films|movie list|"
    r"ranking|top \d+|Netflix|HBO|Disney|"
    r"oscars|festival|box office|"
    r"кіно|фільм\w*|прем'єр\w*|"
    r"трейлер|підбірк\w*|добірк\w*|"
    r"найкращ\w* фільм\w*|"
    r"filmy|filmów|premier\w*|zwiastun\w*", re.I
)
MOVIE_LIST = re.compile(
    r"best\b|top \d+|ranked|movies to watch|films to watch|"
    r"what to watch|watchlist|streaming guide|"
    r"must.watch|recommend\w*|favorites|"
    r"підбірк\w*|добірк\w*|найкращ\w*|"
    r"najlepsz\w*|polecan\w*", re.I
)


def relevant(article):
    title = (article.get("title") or "").strip()
    if not title:
        return False
    category = article.get("category") or ""
    if NOISE.search(title) or personal_feed.CRIME_NOISE.search(title):
        return False
    if category == "Імміграція":
        return migration_relevance.migration_scope(article) is not None
    if category == "Україна":
        # National coverage is deliberately broad; exclude only explicit noise.
        return True
    if category == "Польща":
        return bool(POLAND_RELEVANT.search(title))
    if category == "Світ":
        return bool(WORLD_IMPORTANT.search(title))
    if category == "Технології":
        return bool(TECH_INTEREST.search(title))
    if category == "Кіно":
        return bool(MOVIE_NEWS.search(title))
    if category == "AI":
        return True  # Curated AI publishers, no clickbait crime.
    if category in ("Дизайн", "AI-події"):
        return True
    if category == "Наука":
        return bool(TECH_INTEREST.search(title) or personal_feed.AI_CORE.search(title))
    if category == "Бізнес":
        return bool(WORLD_IMPORTANT.search(title) or TECH_INTEREST.search(title))
    return False


FRESH_WINDOW_DAYS = 7
FRESH_CATEGORIES = {
    "Імміграція", "AI", "AI-події", "Світ", "Україна", "Польща",
    "Бізнес", "Технології", "Наука", "Дизайн", "Кіно", "Мотивація"
}


def recent_feed_candidate(article, updated):
    """All fresh topics, no narrow keyword scoring; conservative obvious-noise filter."""
    title = (article.get("title") or "").strip()
    if not title or article.get("category") not in FRESH_CATEGORIES:
        return False
    published = article.get("published") or 0
    if not isinstance(published, (float, int)) or published <= 0:
        return False
    if published > updated + 3600 or updated - published > FRESH_WINDOW_DAYS * 86400:
        return False
    if NOISE.search(title) or personal_feed.CRIME_NOISE.search(title):
        return False
    if article.get("category") == "Імміграція" and SPECIFIC_OTHER_NATIONALITY.search(title):
        return False
    return True


def build_editorial_feed(articles, updated, sources=()):
    seen_urls = set()
    selected = []
    for article in sorted(articles, key=lambda x: x.get("published") or 0, reverse=True):
        url = article.get("url") or ""
        if not url or url in seen_urls or not recent_feed_candidate(article, updated):
            continue
        seen_urls.add(url)
        if article.get("category") == "Імміграція":
            article = dict(article, migration_scope=migration_relevance.migration_scope(article))
        selected.append(article)
    grouped = story_clusters.group_articles(selected)
    return {
        "articles": grouped,
        "sources": list(sources),
        "updated": updated,
        "archive_total": len(articles),
        "selected_total": len(grouped),
        "grouped_count": len(selected) - len(grouped),
        "method": "all_fresh_topics_7d+obvious_noise_filter+story_groups_v1",
        "window_days": FRESH_WINDOW_DAYS,
        "note": "У стрічці усі свіжі теми за 7 днів, крім очевидного спаму; архів зберігає історію."
    }

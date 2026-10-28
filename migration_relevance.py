"""Conservative headline-level immigrant relevance for a Ukrainian resident in Poland.

No claims of eligibility. Explicit Ukrainian protections outrank generic foreign
visa headlines, and general permanent residence routes are secondary.
"""
import re

UKRAINIAN = re.compile(r"ukrain\w*|ukraiń\w*|ukraińc\w*|україн\w*|украин\w*|"
                       r"\bPESEL[\s-]?UKR\b|\bCUKR\b|status[\s-]?UKR", re.I)
RIGHTS = re.compile(
    r"visa\w*|wiz[ay]\w*|citizenship|naturaliz\w*|immigra\w*|"
    r"permanent residen\w*|temporary residen\w*|residen\w*|"
    r"resydencj\w*|karta pobytu|pobyt\w*|pobytow\w*|"
    r"cudzoziemc\w*|permit\w*|zezwolen\w*|asylum|refugee\w*|"
    r"deport\w*|migrant\w*|temporary protection|"
    r"ochron\w* czasow\w*|"
    r"work authori\w*|work permit|"
    r"blue card|green card|express entry|"
    r"віз\w*|імміграц\w*|міграц\w*|громадянств\w*|"
    r"посвідк\w*|легалізац\w*|дозвіл\w* на проживан\w*|"
    r"тимчасов\w* захист|біжен\w*|притул\w*", re.I
)
CHANGES = re.compile(
    r"reform\w*|law\b|legal\b|new\b|rules?|extend\w*|"
    r"expi\w*|ban\b|expand\w*|eligib\w*|"
    r"deadline\w*|application\w*|apply\b|"
    r"change\w*|update\w*|introduc\w*|"
    r"launch\w*|approv\w*|restrict\w*|"
    r"court\w*|rights?\b|regulat\w*|"
    r"ustaw\w*|zmian\w*|noweliz\w*|"
    r"przedłuż\w*|przedluz\w*|termin\w*|"
    r"wniosk\w*|prawo\b|wyrok\w*|"
    r"закон\w*|змін\w*|оновлен\w*|"
    r"продовж\w*|скасува\w*|термін\w*|"
    r"строк\w*|заяви?\b|правил\w*|"
    r"реформ\w*|нов\w*|подач\w*", re.I
)
NARROW_NATIONALITY = re.compile(
    r"\b(?:indian|pakistani|nigerian|bangladeshi|"
    r"nepalese|filipino|afghan|haitian|venezuelan|"
    r"syrian|somali|iranian|iraqi|mexican|"
    r"tunisian|algerian)\s+(?:nationals?|citizens?|students?|"
    r"workers?|refugees?|migrants?)\b|"
    r"\b(?:obywatele|obywateli)\s+(?:indii|pakistanu|bangladeszu)\b", re.I
)
OFF_TOPIC = re.compile(
    r"immigration department(?:'s)? annual (?:picnic|party)|"
    r"staff party|office party|agency anniversary|"
    r"immigration museum|visa card (?:payment|fraud)|"
    r"bird migration|whale migration|migrating database|"
    r"immigration officer (?:arrest|murder)|"
    r"tourist\s+visa\s+for\s+(?:indian|pakistani)\b", re.I
)
FOCUS_COUNTRIES = {
    "", "Польща", "Канада", "ЄС", "Велика Британія", "США",
    "Німеччина", "Чехія", "Словаччина", "Румунія",
    "Італія", "Угорщина", "Австрія", "Португалія",
}
GEO_KEYWORDS = re.compile(
    r"poland|polish|polsk\w*|canada|canadian|"
    r"europe|eu\b|germany|german|italy|italian|"
    r"portugal|portuguese|uk\b|britain|british|"
    r"united states|american|us\s+citizenship|"
    r"польщ\w*|канад\w*|європ\w*|німеччин\w*|"
    r"італі\w*|португалі\w*|"
    r"польс\w*|канада\b", re.I
)

def migration_scope(article):
    """Return 'ukrainian' or 'general', otherwise None. Title rules are not eligibility checks."""
    title = (article.get("title") or "").strip()
    if not title or OFF_TOPIC.search(title):
        return None
    ukrainian = bool(UKRAINIAN.search(title))
    if NARROW_NATIONALITY.search(title) and not ukrainian:
        return None
    country = article.get("country") or ""
    if country not in FOCUS_COUNTRIES and not ukrainian:
        return None
    # Mentioning Ukraine alone is insufficient; must concern immigration or
    # protection. PESEL and CUKR are by themselves decisive rights topics.
    if not RIGHTS.search(title) and not re.search(r"\bPESEL\b|\bCUKR\b|status[\s-]?UKR", title, re.I):
        return None
    if ukrainian:
        return "ukrainian"
    if not CHANGES.search(title):
        return None
    if country == "" and not GEO_KEYWORDS.search(title):
        return None
    return "general"

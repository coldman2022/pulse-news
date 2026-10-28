"""Conservative near-duplicate headlines for Pulse's editorial front page.

Only combine near-identical titles in the same category and 48-hour window.
This is not semantic clustering, fact checking, translation, or an AI summary.
Full news.json and original source URLs remain untouched.
"""
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import re
import unicodedata

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "for", "from", "in", "on",
    "with", "about", "after", "by", "as", "at", "is", "are", "was", "will",
    "this", "that", "new", "latest", "now", "says", "said",
    "та", "і", "й", "у", "в", "на", "за", "для", "про", "від", "до", "що",
    "з", "із", "новий", "нова", "нове", "нові",
    "i", "oraz", "w", "we", "z", "ze", "na", "do", "dla", "po", "o",
    "jest", "nowy", "nowa", "nowe", "się", "sie",
}
NEGATION = {"not", "no", "never", "without", "не", "ні", "без", "nie", "bez"}
MAX_WINDOW_SECONDS = 48 * 3600
MAX_RELATED = 12


def _signature(article, title_override=None):
    title = unicodedata.normalize(
        "NFKC", str(title_override if title_override is not None else article.get("title") or "")
    ).casefold()
    publisher = str(article.get("publisher") or "").strip().casefold()
    if publisher:
        # Only strip a verified publisher suffix, not arbitrary meaningful dashes.
        title = re.sub(r"\s+[-–|]\s+" + re.escape(publisher) + r"$", "", title)
    words = re.findall(r"[^\W_]+", title, flags=re.UNICODE)
    significant = [word for word in words if word not in STOP and len(word) > 1]
    numbers = {word for word in words if any(char.isdigit() for char in word)}
    negated = any(word in NEGATION for word in words)
    return set(significant), " ".join(significant), numbers, negated


def _same_story(left, right):
    words_a, phrase_a, numbers_a, negative_a = left
    words_b, phrase_b, numbers_b, negative_b = right
    if not phrase_a or not phrase_b or numbers_a != numbers_b or negative_a != negative_b:
        return False
    if phrase_a == phrase_b:
        return True
    # A four-word title needs an exact match; longer ones require strong evidence.
    if min(len(words_a), len(words_b)) < 5:
        return False
    shared = len(words_a & words_b)
    if shared < 5:
        return False
    if shared / min(len(words_a), len(words_b)) < .85:
        return False
    if shared / len(words_a | words_b) < .72:
        return False
    return SequenceMatcher(None, phrase_a, phrase_b).ratio() >= .88


def group_articles(articles, translations=None):
    """Merge obvious original-language duplicates, then very high-confidence translated ones.

    Translated matching uses only existing offline cache whose source_title is an
    exact match. No online translation, no semantic guesses; original publisher
    links always remain and the unchanged archive is never mutated.
    """
    translations = translations or {}
    groups, original_signatures, localized_signatures, group_langs = [], [], [], []
    token_index = defaultdict(list)
    seen_urls = set()

    def localized(article):
        lang = str(article.get("language") or "en").split("-", 1)[0].lower()
        if lang == "uk":
            return _signature(article)
        entry = translations.get(article.get("id"))
        if (not isinstance(entry, dict)
                or entry.get("source_title") != article.get("title")
                or entry.get("language") != lang
                or not isinstance(entry.get("title"), str)):
            return None
        return _signature(article, entry["title"])

    for article in sorted(articles, key=lambda item: item.get("published") or 0, reverse=True):
        url = article.get("url") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        signature = _signature(article)
        localized_sig = localized(article)
        topic = article.get("category") or ""
        lang = str(article.get("language") or "en").split("-", 1)[0].lower()
        timestamp = article.get("published") or 0
        candidates = Counter(
            index for word in signature[0] for index in token_index[(topic, "original", word)]
        )
        if localized_sig:
            candidates.update(
                index for word in localized_sig[0] for index in token_index[(topic, "uk", word)]
            )
        target = None
        for group_id, shared in candidates.most_common():
            if shared < 4:
                break
            main = groups[group_id]
            if not timestamp or not main.get("published"):
                continue
            if abs(timestamp - main["published"]) > MAX_WINDOW_SECONDS:
                continue
            # Existing same-language matching takes precedence.
            same_original = _same_story(signature, original_signatures[group_id])
            other_lang = lang != group_langs[group_id]
            cross_language = (
                other_lang and localized_sig is not None
                and localized_signatures[group_id] is not None
                and signature[2] == original_signatures[group_id][2]
                and signature[3] == original_signatures[group_id][3]
                and _same_story(localized_sig, localized_signatures[group_id])
            )
            if same_original or cross_language:
                target = main
                break
        if target is not None:
            related = target.setdefault("related_sources", [])
            if len(related) < MAX_RELATED:
                related.append({
                    "title": article.get("title") or "",
                    "url": url,
                    "source": article.get("source") or "",
                    "publisher": article.get("publisher") or article.get("source") or "",
                    "published": timestamp,
                    "origin": article.get("origin") or "",
                })
            continue
        copy = dict(article)
        copy.pop("related_sources", None)
        index = len(groups)
        groups.append(copy)
        original_signatures.append(signature)
        localized_signatures.append(localized_sig)
        group_langs.append(lang)
        for word in signature[0]:
            token_index[(topic, "original", word)].append(index)
        if localized_sig:
            for word in localized_sig[0]:
                token_index[(topic, "uk", word)].append(index)
    return groups

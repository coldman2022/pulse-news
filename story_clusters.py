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


def _signature(article):
    title = unicodedata.normalize("NFKC", str(article.get("title") or "")).casefold()
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


def group_articles(articles):
    """Return independent representative articles with source-linked alternatives."""
    groups = []
    signatures = []
    token_index = defaultdict(list)
    seen_urls = set()
    for article in sorted(articles, key=lambda item: item.get("published") or 0, reverse=True):
        url = article.get("url") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        signature = _signature(article)
        topic = article.get("category") or ""
        timestamp = article.get("published") or 0
        candidates = Counter(
            group_id for word in signature[0]
            for group_id in token_index[(topic, word)]
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
            if _same_story(signature, signatures[group_id]):
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
        group_id = len(groups)
        groups.append(copy)
        signatures.append(signature)
        for word in signature[0]:
            token_index[(topic, word)].append(group_id)
    return groups

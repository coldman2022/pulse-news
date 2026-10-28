#!/usr/bin/env python3
"""Translate up to 200 new RSS headlines + previews per day on a GitHub runner.

Open-source Marian/OPUS models run locally in this scheduled job, not on
GitHub Pages or readers' phones. Existing translations are keyed by article ID
and original text to avoid work on every hourly RSS refresh.

An optional MYMEMORY_CONTACT_EMAIL repository secret enables a bounded
fallback for languages with no installed local model. No email or API URL with
credentials is ever written to the published JSON.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

DAILY_LIMIT = 200
MAX_CACHED = 1800
MAX_AGE_DAYS = 120
SUMMARY_LIMIT = 600
SUPPORTED_OFFLINE = {
    "en": "Helsinki-NLP/opus-mt-en-uk",
    "pl": "Helsinki-NLP/opus-mt-pl-uk",
}
SUPPORTED_FALLBACK = {"de", "fr", "es", "it"}
MYMEMORY_MAX_CHARS = 42_000  # Below the documented 50k email tier.
TRANSLATION_SCHEMA = 1
ARTICLE_ID = re.compile(r"^[a-f0-9]{20}$")


def empty_cache():
    return {
        "schema": TRANSLATION_SCHEMA,
        "updated": 0,
        "articles": {},
        "meta": {"engine": "local_opus_mt", "daily_target": DAILY_LIMIT},
    }


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return default


def load_cache(path):
    cached = load_json(path, empty_cache())
    if not isinstance(cached, dict) or not isinstance(cached.get("articles"), dict):
        return empty_cache()
    return cached


def normalize_language(article):
    return (article.get("language") or "en").lower().split("-", 1)[0]


def original_summary(article):
    return (article.get("summary") or "").strip()[:SUMMARY_LIMIT]


def unchanged(cache_entry, article):
    return (
        isinstance(cache_entry, dict)
        and cache_entry.get("source_title") == (article.get("title") or "").strip()
        and cache_entry.get("source_summary") == original_summary(article)
        and cache_entry.get("language") == normalize_language(article)
        and bool(cache_entry.get("title"))
        and isinstance(cache_entry.get("summary"), str)
    )


def candidates(feed, cache, now, limit=DAILY_LIMIT, contact_email=""):
    """Newest first; no translation for Ukrainian or already-cached articles."""
    rows = feed.get("articles", []) if isinstance(feed, dict) else []
    if not isinstance(rows, list):
        return []
    stored = cache.get("articles", {})
    found, seen = [], set()
    languages = set(SUPPORTED_OFFLINE)
    if contact_email:
        languages |= SUPPORTED_FALLBACK
    for article in sorted(rows, key=lambda a: a.get("published") or 0, reverse=True):
        if not isinstance(article, dict):
            continue
        article_id = article.get("id") or ""
        title = (article.get("title") or "").strip()
        lang = normalize_language(article)
        if (not ARTICLE_ID.fullmatch(article_id) or article_id in seen
                or not title or len(title) > 500 or lang not in languages):
            continue
        published = article.get("published") or 0
        if (not isinstance(published, (int, float)) or published <= 0
                or published > now + 3600
                or now - published > 14 * 86400):
            continue
        seen.add(article_id)
        if unchanged(stored.get(article_id), article):
            continue
        found.append(article)
        if len(found) >= limit:
            break
    return found


class LocalMarian:
    """Lazy-load only necessary open-source models; batch for runner CPU."""
    def __init__(self):
        self.models = {}

    def _model(self, lang):
        if lang not in self.models:
            from transformers import MarianMTModel, MarianTokenizer
            import torch
            torch.set_num_threads(min(4, os.cpu_count() or 2))
            name = SUPPORTED_OFFLINE[lang]
            print(f"Loading local offline model {name}")
            tokenizer = MarianTokenizer.from_pretrained(name)
            model = MarianMTModel.from_pretrained(name)
            model.eval()
            self.models[lang] = (tokenizer, model)
        return self.models[lang]

    def translate_many(self, texts, lang):
        import torch
        tokenizer, model = self._model(lang)
        results = []
        for offset in range(0, len(texts), 8):
            group = texts[offset:offset + 8]
            inputs = tokenizer(
                group, return_tensors="pt", padding=True,
                truncation=True, max_length=384
            )
            with torch.inference_mode():
                tokens = model.generate(
                    **inputs, max_new_tokens=240, num_beams=1
                )
            results.extend(tokenizer.batch_decode(tokens, skip_special_tokens=True))
        return [value.strip() for value in results]


class MyMemoryFallback:
    """Optional email contact stays in Actions Secrets, never in client JS."""
    def __init__(self, email):
        self.email = email
        self.consumed = 0

    @staticmethod
    def _parts(text):
        # Conservative MyMemory limit: <=440 UTF-8 bytes per API query.
        words = re.findall(r"\S+\s*", text)
        chunks, current = [], ""
        for word in words:
            if len((current + word).encode("utf-8")) <= 440:
                current += word
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = ""
                for character in word:
                    if len((current + character).encode("utf-8")) > 440:
                        if current.strip():
                            chunks.append(current.strip())
                        current = ""
                    current += character
        if current.strip():
            chunks.append(current.strip())
        return chunks

    def translate_many(self, texts, lang):
        output = []
        for text in texts:
            pieces = []
            for piece in self._parts(text):
                if self.consumed + len(piece) > MYMEMORY_MAX_CHARS:
                    raise RuntimeError("Configured MyMemory daily safety budget reached")
                self.consumed += len(piece)  # count attempts, including failures
                qs = urllib.parse.urlencode({
                    "q": piece, "langpair": f"{lang}|uk", "de": self.email,
                })
                # Never print the URL: it contains the secret contact email.
                req = urllib.request.Request(
                    "https://api.mymemory.translated.net/get?" + qs,
                    headers={"User-Agent": "PulseTranslation/1.0"}
                )
                with urllib.request.urlopen(req, timeout=16) as reply:
                    data = json.load(reply)
                value = str(data.get("responseData", {}).get("translatedText", "")).strip()
                if (data.get("responseStatus") != 200 or not value
                        or re.search(r"MYMEMORY WARNING|USED ALL AVAILABLE|DAILY LIMIT", value, re.I)):
                    raise RuntimeError("MyMemory quota or translation error")
                pieces.append(value)
            output.append(" ".join(pieces))
        return output


def clean_translation(value, original):
    if not isinstance(value, str):
        return None
    value = " ".join(value.split()).strip()
    if not value or len(value) > 1800:
        return None
    if len(original) > 30 and value.casefold() == original.casefold():
        return None
    return value


def prune(cache, now):
    records = cache.get("articles", {})
    valid = [
        (key, data) for key, data in records.items()
        if ARTICLE_ID.fullmatch(key) and isinstance(data, dict)
        and now - (data.get("translated_at") or 0) < MAX_AGE_DAYS * 86400
        and data.get("translated_at", 0) <= now + 3600
    ]
    valid.sort(key=lambda pair: pair[1].get("translated_at") or 0, reverse=True)
    cache["articles"] = dict(valid[:MAX_CACHED])
    cache["schema"] = TRANSLATION_SCHEMA
    return cache


def process(feed, previous, now, local, mymemory=None, limit=DAILY_LIMIT):
    """Core logic can be tested without downloading models or making requests."""
    cache = dict(previous)
    cache["articles"] = dict(previous.get("articles", {}))
    rows = candidates(feed, cache, now, limit, mymemory.email if mymemory else "")
    done = 0
    for lang in ("en", "pl", "de", "fr", "es", "it"):
        group = [article for article in rows if normalize_language(article) == lang]
        if not group:
            continue
        engine = local if lang in SUPPORTED_OFFLINE else mymemory
        if engine is None:
            continue
        try:
            titles = engine.translate_many(
                [(a.get("title") or "").strip() for a in group], lang
            )
            previews = engine.translate_many(
                [original_summary(a) for a in group if original_summary(a)], lang
            )
            preview_iter = iter(previews)
            for article, translated_title in zip(group, titles):
                original = (article.get("title") or "").strip()
                summary = original_summary(article)
                translated_summary = next(preview_iter, "") if summary else ""
                fixed_title = clean_translation(translated_title, original)
                fixed_summary = clean_translation(translated_summary, summary) if summary else ""
                if not fixed_title or (summary and not fixed_summary):
                    continue
                cache["articles"][article["id"]] = {
                    "source_title": original,
                    "source_summary": summary,
                    "language": lang,
                    "title": fixed_title,
                    "summary": fixed_summary,
                    "engine": "opus_mt" if lang in SUPPORTED_OFFLINE else "mymemory",
                    "translated_at": int(now),
                }
                done += 1
        except Exception as exc:
            # Preserve working translations even if a model/API is unavailable.
            print(f"Translation for {lang} unavailable: {type(exc).__name__}: "
                  f"{str(exc)[:120] if lang in SUPPORTED_OFFLINE else 'remote request failed'}")
    cache["updated"] = int(now)
    cache["meta"] = {
        "engine": "local_opus_mt_with_optional_mymemory_fallback",
        "daily_target": limit,
        "new_translations": done,
        "remaining_candidates": max(0, len(rows) - done),
    }
    prune(cache, now)
    return cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default="_translation_feed.json")
    parser.add_argument("--cache", default="static/translations.json")
    parser.add_argument("--limit", type=int, default=DAILY_LIMIT)
    args = parser.parse_args()
    if not 1 <= args.limit <= DAILY_LIMIT:
        parser.error("The daily limit must be between 1 and 200")
    feed = load_json(args.feed, {})
    if not isinstance(feed, dict) or not isinstance(feed.get("articles"), list):
        raise SystemExit("No valid feed; existing translations were kept unchanged")
    cache = load_cache(args.cache)
    email = os.getenv("MYMEMORY_CONTACT_EMAIL", "").strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise SystemExit("MYMEMORY_CONTACT_EMAIL is not a valid contact email")
    now = time.time()
    result = process(feed, cache, now, LocalMarian(),
                     MyMemoryFallback(email) if email else None, args.limit)
    dest = Path(args.cache)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(dest)
    print(f"Batch complete: {result['meta']['new_translations']} new translations, "
          f"{len(result['articles'])} cached, max {args.limit}/run")


if __name__ == "__main__":
    main()

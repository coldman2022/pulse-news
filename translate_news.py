#!/usr/bin/env python3
"""Bounded, cached, opt-in offline translation of Pulse RSS previews.

Runs AFTER build_site.py on a GitHub-hosted CPU runner.
No tokens, API credentials, external translation requests, or Google services.
Argos packages are downloaded from the upstream Argos model index on first use.

The script never modifies original title/summary and does not invent translations.
"""
import argparse
import json
import os
import tempfile
import time
from pathlib import Path

PREFERRED = {"Імміграція": 0, "AI": 1, "AI-події": 2, "Світ": 3}
SUPPORTED = {"en", "pl"}
MODEL = "argos-v1"


def source_language(article):
    lang = article.get("language", "en")
    return lang if lang in SUPPORTED | {"uk"} else None


def has_current_translation(article):
    if source_language(article) not in SUPPORTED:
        return False
    return (
        article.get("translation_model") == MODEL
        and isinstance(article.get("title_uk"), str)
        and len(article["title_uk"].strip()) > 1
    )


def pending(articles):
    def priority(article):
        return (
            PREFERRED.get(article.get("category"), 5),
            0 if article.get("origin") == "official" else 1,
            -(article.get("published") or 0),
        )
    return sorted(
        (row for row in articles if source_language(row) in SUPPORTED
         and row.get("title") and not has_current_translation(row)),
        key=priority,
    )


def model_route(installed_pairs, source):
    """Prefer a direct pair, else Polish via English."""
    if (source, "uk") in installed_pairs:
        return [(source, "uk")]
    if source == "pl" and ("pl", "en") in installed_pairs and ("en", "uk") in installed_pairs:
        return [("pl", "en"), ("en", "uk")]
    return None


def needed_pairs(languages, available_pairs):
    pairs = []
    if "en" in languages or "pl" in languages:
        if ("en", "uk") in available_pairs:
            pairs.append(("en", "uk"))
    if "pl" in languages:
        if ("pl", "uk") in available_pairs:
            pairs.append(("pl", "uk"))
        elif ("pl", "en") in available_pairs:
            pairs.append(("pl", "en"))
    return pairs


def setup_models(languages):
    import argostranslate.package as package
    import argostranslate.translate as translate
    installed = {(p.from_code, p.to_code) for p in package.get_installed_packages()}
    missing = set(languages) - {lang for lang in languages if model_route(installed, lang)}
    if missing:
        package.update_package_index()
        available = {(p.from_code, p.to_code): p for p in package.get_available_packages()
                     if p.type == "translate"}
        wanted = needed_pairs(missing, set(available))
        for pair in wanted:
            if pair not in installed:
                print("Installing model", pair, flush=True)
                path = available[pair].download()
                package.install_from_path(path)
                installed.add(pair)
    routes = {lang: model_route(installed, lang) for lang in languages}
    print("Available language routes:", routes, flush=True)
    return translate, routes


def translate_text(text, lang, translator, route):
    # Argos itself handles sentence chunks; keep RSS previews short.
    result = text.strip()
    for src, dst in route:
        result = translator.translate(result, src, dst).strip()
        if not result:
            raise ValueError("Model returned empty translation")
    if result == text.strip() and len(text.strip()) > 8:
        raise ValueError("Model returned original unchanged")
    return result


def write_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=str(path.parent), prefix=".news-translated-",
        suffix=".json", encoding="utf-8", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        temp_path = handle.name
    os.replace(temp_path, path)


def record_stats(payload, *, newly=0, note=None):
    articles = payload.get("articles", [])
    eligible = sum(1 for row in articles if source_language(row) in SUPPORTED)
    translated = sum(1 for row in articles if has_current_translation(row))
    payload["translation_stats"] = {
        "engine": MODEL,
        "eligible": eligible,
        "translated": translated,
        "new_this_run": newly,
        "status": note if note else "partial" if translated < eligible else "complete",
    }


def run(snapshot, *, max_new=18, max_seconds=175, summary_limit=320):
    """Bound heavy translation; save each completed article to survive timeouts."""
    start = time.monotonic()
    path = Path(snapshot)
    data = json.loads(path.read_text(encoding="utf-8"))
    articles = data["articles"]
    queue = pending(articles)[:max_new]
    if not queue:
        record_stats(data, note="complete")
        write_atomic(path, data)
        print("Nothing to translate.", flush=True)
        return 0

    languages = {source_language(row) for row in queue}
    try:
        translator, routes = setup_models(languages)
    except Exception as error:
        print("Argos packages unavailable; keeping original: " + str(error), flush=True)
        record_stats(data, note="model_unavailable")
        write_atomic(path, data)
        return 0

    newly = 0
    for row in queue:
        if time.monotonic() - start >= max_seconds:
            print("Reached time budget.", flush=True)
            break
        lang = source_language(row)
        route = routes.get(lang)
        if not route:
            continue
        try:
            title = translate_text(row["title"][:350], lang, translator, route)
            summary = ""
            original_summary = (row.get("summary") or "").strip()
            if original_summary and time.monotonic() - start < max_seconds:
                try:
                    summary = translate_text(original_summary[:summary_limit], lang, translator, route)
                except Exception as error:
                    print("Summary failed for article:", str(error), flush=True)
            row["title_uk"] = title
            if summary:
                row["summary_uk"] = summary
            row["translation_model"] = MODEL
            newly += 1
            record_stats(data, newly=newly)
            write_atomic(path, data)
            print("Translated", newly, "of", len(queue), "articles; elapsed",
                  round(time.monotonic() - start, 1), "seconds", flush=True)
        except Exception as error:
            print("Title translation failed; original preserved:", str(error), flush=True)

    record_stats(data, newly=newly)
    write_atomic(path, data)
    print("Translation summary:", data["translation_stats"], flush=True)
    return 0


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--snapshot", default="_site/news.json")
    cli.add_argument("--max-new", type=int, default=18)
    cli.add_argument("--max-seconds", type=int, default=175)
    cli.add_argument("--summary-limit", type=int, default=320)
    a = cli.parse_args()
    if a.max_new < 0 or a.max_new > 100 or a.max_seconds <= 0:
        cli.error("Invalid resource budget")
    raise SystemExit(run(a.snapshot, max_new=a.max_new, max_seconds=a.max_seconds,
                         summary_limit=a.summary_limit))

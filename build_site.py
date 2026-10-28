#!/usr/bin/env python3
"""Build a Pages artifact using the same RSS parser as the local server."""
import argparse
import json
import shutil
import time
from pathlib import Path

import server
import opportunities
import daily_digest
import personal_feed
import editorial_feed


# The previous snapshot is restored by GitHub Actions cache when available.
# Without it, the current RSS contents still produce a valid fresh build.
RETENTION_DAYS = {'Імміграція': 120, 'AI-події': 120, 'AI': 45, 'Світ': 21}
DEFAULT_RETENTION_DAYS = 30
MAX_ARTICLES = 3500


def retain_recent(current, previous, now):
    # Keep an article until its topic-specific expiry, but never duplicate a URL.
    seen = set()
    retained = []
    for index, article in enumerate(list(current) + list(previous)):
        url = article.get('url')
        if not url or url in seen:
            continue
        date = article.get('published') or 0
        days = RETENTION_DAYS.get(article.get('category'), DEFAULT_RETENTION_DAYS)
        # Accept undated articles only in the freshly fetched snapshot.
        if not date and index >= len(current):
            continue
        if date and now - date > days * 86400:
            continue
        seen.add(url)
        retained.append(article)
    return sorted(retained, key=lambda a: a.get('published', 0), reverse=True)[:MAX_ARTICLES]


def build(output):
    output = Path(output)
    snapshot = output / 'news.json'
    server.CACHE.clear()
    previous_articles = []
    if snapshot.exists():
        previous = json.loads(snapshot.read_text(encoding='utf-8'))
        previous_articles = previous.get('articles', [])
        by_source = {}
        for article in previous_articles:
            if article.get('source'):
                by_source.setdefault(article['source'], []).append(article)
        server.CACHE['by_source'] = by_source
    payload = server.news()
    # Never replace a working deployment with an empty or entirely failed fetch.
    if not payload['articles'] or not any(s['ok'] for s in payload['sources']):
        raise RuntimeError('All RSS sources failed; keep the previous deployment and retry later.')
    payload['articles'] = retain_recent(payload['articles'], previous_articles, time.time())
    # Keep the historical archive, but never carry forward publications from
    # sources removed from our deliberately curated, established-publisher list.
    allowed_sources = {
        source['name'] for source in json.loads((server.ROOT / 'sources.json').read_text(encoding='utf-8'))
    }
    payload['articles'] = [
        article for article in payload['articles'] if article.get('source') in allowed_sources
    ]

    output.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'app.js', 'style.css', 'opportunities.html', 'opportunities.js', 'digest.html', 'digest.js', 'events.json', 'events.js'):
        shutil.copyfile(server.ROOT / 'static' / name, output / name)
    # Make the curated event slider resilient if the browser cannot fetch events.json.
    events_data = json.loads((server.ROOT / 'static' / 'events.json').read_text(encoding='utf-8'))
    events_js = output / 'events.js'
    original_events_js = events_js.read_text(encoding='utf-8')
    fallback_marker = '/* PULSE_BUILD_EVENTS_JSON */ []'
    if fallback_marker not in original_events_js:
        raise RuntimeError('Missing event fallback marker in events.js')
    events_js.write_text(
        original_events_js.replace(fallback_marker, json.dumps(events_data['events'], ensure_ascii=False)),
        encoding='utf-8',
    )
    temporary = output / 'news.json.tmp'
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    temporary.replace(snapshot)
    opportunities_payload = {
        'updated': payload['updated'],
        'cards': opportunities.make_opportunities(payload['articles']),
    }
    opportunity_temp = output / 'opportunities.json.tmp'
    opportunity_temp.write_text(json.dumps(opportunities_payload, ensure_ascii=False), encoding='utf-8')
    opportunity_temp.replace(output / 'opportunities.json')
    # No second RSS fetch or AI API. A rolling 24-hour briefing built from the
    # same publisher-provided headlines and short RSS descriptions.
    digest = daily_digest.build_digest(payload['articles'], payload['updated'])
    digest_temp = output / 'digest.json.tmp'
    digest_temp.write_text(json.dumps(digest, ensure_ascii=False), encoding='utf-8')
    digest_temp.replace(output / 'digest.json')
    editorial = editorial_feed.build_editorial_feed(
        payload['articles'], payload['updated'], payload['sources']
    )
    curated_temp = output / 'feed.json.tmp'
    curated_temp.write_text(json.dumps(editorial, ensure_ascii=False), encoding='utf-8')
    curated_temp.replace(output / 'feed.json')
    # Personal front page is a small ranked view; the complete archive is preserved.
    personal_payload = personal_feed.build_personal_feed(payload['articles'], payload['updated'])
    personal_payload['sources'] = payload['sources']
    personal_temp = output / 'personal.json.tmp'
    personal_temp.write_text(json.dumps(personal_payload, ensure_ascii=False), encoding='utf-8')
    personal_temp.replace(output / 'personal.json')
    (output / '.nojekyll').touch()
    print(f"Built {len(payload['articles'])} articles; sources: {payload['sources']}")
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site')
    build(parser.parse_args().output)

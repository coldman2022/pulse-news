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


# The previous snapshot is restored by GitHub Actions cache when available.
# Without it, the current RSS contents still produce a valid fresh build.
RETENTION_DAYS = {'Імміграція': 60, 'AI-події': 90, 'AI': 21, 'Світ': 7}
DEFAULT_RETENTION_DAYS = 14
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
    output.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'app.js', 'style.css', 'opportunities.html', 'opportunities.js', 'digest.html', 'digest.js'):
        shutil.copyfile(server.ROOT / 'static' / name, output / name)
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
    (output / '.nojekyll').touch()
    print(f"Built {len(payload['articles'])} articles; sources: {payload['sources']}")
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site')
    build(parser.parse_args().output)

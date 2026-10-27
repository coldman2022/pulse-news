#!/usr/bin/env python3
"""Build a Pages artifact using the same RSS parser as the local server."""
import argparse
import json
import shutil
from pathlib import Path

import server


def build(output, translate=False, translation_cache='.cache/translations.json'):
    output = Path(output)
    snapshot = output / 'news.json'
    server.CACHE.clear()
    if snapshot.exists():
        previous = json.loads(snapshot.read_text(encoding='utf-8'))
        by_source = {}
        for article in previous['articles']:
            by_source.setdefault(article['source'], []).append(article)
        server.CACHE['by_source'] = by_source
    payload = server.news()
    # Never replace a working deployment with an empty or entirely failed fetch.
    if not payload['articles'] or not any(s['ok'] for s in payload['sources']):
        raise RuntimeError('All RSS sources failed; keep the previous deployment and retry later.')
    if translate:
        from translate_news import translate_payload
        translate_payload(payload, translation_cache)
    output.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'app.js', 'style.css'):
        shutil.copyfile(server.ROOT / 'static' / name, output / name)
    temporary = output / 'news.json.tmp'
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    temporary.replace(snapshot)
    (output / '.nojekyll').touch()
    print(f"Built {len(payload['articles'])} articles; sources: {payload['sources']}")
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site')
    parser.add_argument('--translate', action='store_true')
    args = parser.parse_args()
    build(args.output, translate=args.translate)

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import build_site
import server


class BuildTests(unittest.TestCase):
    def tearDown(self):
        server.CACHE.clear()

    def article(self, source, url):
        return dict(id=url, title='Test', url=url, source=source, category='Світ',
                    summary='', published=time.time())

    def test_static_artifact_and_persistent_partial_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            old = self.article('The Guardian', 'https://example.org/old')
            (output / 'news.json').write_text(json.dumps({'articles': [old]}))

            def fetch(source):
                if source['name'] == 'The Guardian':
                    raise OSError('offline')
                return [self.article(source['name'], 'https://example.org/' + source['name'])]

            with patch.object(server, 'fetch_source', side_effect=fetch), \
                 patch.object(build_site.reddit_feed, 'build_reddit_preview', return_value={}), \
                 patch.object(build_site.currency_rates, 'build_rates', return_value={}):
                payload = build_site.build(output)
            self.assertIn(old, payload['articles'])
            self.assertEqual(next(s for s in payload['sources'] if s['name'] == 'The Guardian'),
                             dict(name='The Guardian', ok=False, cached=True))
            self.assertEqual(json.loads((output / 'news.json').read_text()), payload)
            html = (output / 'index.html').read_text()
            self.assertIn('href="./style.css?v=26"', html)
            self.assertIn('src="./app.js?v=19"', html)
            self.assertTrue((output / '.nojekyll').exists())
            self.assertTrue((output / 'opportunities.html').exists())
            self.assertTrue((output / 'opportunities.js').exists())
            opportunities = json.loads((output / 'opportunities.json').read_text())
            self.assertIn('cards', opportunities)
            self.assertTrue((output / 'digest.html').exists())
            self.assertTrue((output / 'digest.js').exists())
            self.assertTrue((output / 'reddit.html').exists())
            self.assertTrue((output / 'reddit.js').exists())
            self.assertTrue((output / 'currency.js').exists())
            self.assertTrue((output / 'feed.json').exists())
            editorial = json.loads((output / 'feed.json').read_text())
            self.assertIn('articles', editorial)
            self.assertEqual(editorial['archive_total'], len(payload['articles']))
            self.assertEqual(editorial['selected_total'], len(editorial['articles']))
            self.assertTrue((output / 'personal.json').exists())
            personal = json.loads((output / 'personal.json').read_text())
            self.assertIn('featured', personal)
            self.assertIn('brief', personal)
            self.assertIn('sources', personal)
            self.assertTrue((output / 'events.json').exists())
            self.assertTrue((output / 'motivation.html').exists())
            self.assertTrue((output / 'motivation.js').exists())
            self.assertTrue((output / 'share.js').exists())
            motivation=json.loads((output / 'motivation.json').read_text())
            self.assertIn('articles', motivation)
            self.assertTrue((output / 'events.js').exists())
            for name in ('mobile.js','manifest.webmanifest','pulse-icon.svg',
                         'pulse-icon-180.png','pulse-icon-512.png'):
                self.assertTrue((output / name).exists(), name)
            manifest=json.loads((output/'manifest.webmanifest').read_text())
            self.assertEqual(manifest['display'],'standalone')

            bundled_events = (output / 'events.js').read_text()
            self.assertIn('Product Management Day 2026', bundled_events)
            self.assertNotIn('PULSE_BUILD_EVENTS_JSON', bundled_events)
            digest = json.loads((output / 'digest.json').read_text())
            self.assertEqual(digest['method'], 'publisher_rss_excerpts')
            self.assertEqual(len(digest['sections']), 4)

    def test_history_retains_immigration_but_expires_world_news(self):
        now = 1_800_000_000
        def row(url, category, age):
            return dict(url=url, category=category, published=now-age*86400)
        past = [row('https://example.org/immigration', 'Імміграція', 40),
                row('https://example.org/conference', 'AI-події', 75),
                row('https://example.org/old-world', 'Світ', 40)]
        fresh = [row('https://example.org/today', 'AI', 1)]
        retained = build_site.retain_recent(fresh, past, now)
        urls = {item['url'] for item in retained}
        self.assertIn('https://example.org/immigration', urls)
        self.assertIn('https://example.org/conference', urls)
        self.assertNotIn('https://example.org/old-world', urls)
        self.assertIn('https://example.org/today', urls)

    def test_total_failure_preserves_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'news.json'
            previous = json.dumps({'articles': [self.article('BBC World', 'https://example.org/old')]})
            path.write_text(previous)
            with patch.object(server, 'fetch_source', side_effect=OSError('offline')):
                with self.assertRaises(RuntimeError):
                    build_site.build(folder)
            self.assertEqual(path.read_text(), previous)

    def test_first_build_fails_without_real_news(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(server, 'fetch_source', side_effect=OSError('offline')):
                with self.assertRaises(RuntimeError):
                    build_site.build(folder)
            self.assertFalse((Path(folder) / 'news.json').exists())

"""Regression tests: full feed is the homepage; events cannot disappear on fetch failure."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import build_site
import server

ROOT = Path(__file__).resolve().parent


class RestoreFeedTests(unittest.TestCase):
    def tearDown(self):
        server.CACHE.clear()

    def test_the_full_archive_is_the_default_homepage(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('<button class="active" data-mode="all">', html)
        self.assertIn("mode = 'all'", js)
        self.assertIn("isFull?'./news.json':'./personal.json'", js)
        self.assertIn('data-mode="focus"', html)
        self.assertIn("visibleLimit+=60", js)

    def test_archive_stays_above_a_thousand_when_cache_exists(self):
        now = time.time()
        archive = [dict(
            id=str(i), title="Prior verified news " + str(i),
            url="https://example.org/archive/" + str(i),
            source="BBC World", publisher="BBC", category="Світ",
            published=now - 4 * 86400, summary=""
        ) for i in range(1220)]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / 'news.json').write_text(
                json.dumps({'articles': archive}), encoding='utf-8'
            )
            def fetch(source):
                return [dict(
                    id=source['name'], title="New " + source['name'],
                    url="https://example.org/new/" + str(len(source['name'])) + source['name'],
                    source=source['name'], category=source['category'],
                    published=now, summary=""
                )]
            with patch.object(server, 'fetch_source', side_effect=fetch):
                data = build_site.build(output)
            self.assertGreaterEqual(len(data['articles']), 1220)
            self.assertIn("https://example.org/archive/1000",
                          {a['url'] for a in data['articles']})

    def test_removed_niche_sources_are_not_retained(self):
        names = {s['name'] for s in json.loads(
            (ROOT / 'sources.json').read_text(encoding='utf-8'))}
        self.assertNotIn("Simon Willison — LLM", names)
        self.assertNotIn("Import AI — research", names)
        self.assertNotIn("Hacker News", names)
        for publisher in ["CNBC World", "CNBC Technology", "POLITICO Europe",
                          "The New York Times World", "France 24", "NPR News", "Sky News World"]:
            self.assertIn(publisher, names)


if __name__ == "__main__":
    unittest.main()

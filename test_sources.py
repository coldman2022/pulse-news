import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CATEGORIES = {"Світ", "Україна", "Польща", "Бізнес", "Технології", "AI", "Наука", "Дизайн", "Імміграція", "AI-події"}


class SourceConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))

    def test_broad_coverage(self):
        self.assertGreaterEqual(len(self.sources), 70)
        self.assertTrue(CATEGORIES.issubset({s["category"] for s in self.sources}))
        self.assertGreaterEqual(len([s for s in self.sources if s.get("origin") == "official"]), 2)
        self.assertGreaterEqual(len([s for s in self.sources if s.get("origin") == "discovery"]), 15)

    def test_unique_valid_feeds(self):
        names = [s["name"] for s in self.sources]
        urls = [s["url"] for s in self.sources]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(urls), len(set(urls)))
        for source in self.sources:
            self.assertTrue(source["name"].strip())
            self.assertIn(source["category"], CATEGORIES)
            url = urlsplit(source["url"])
            self.assertEqual(url.scheme, "https", source["name"])
            self.assertTrue(url.hostname, source["name"])

    def test_category_buttons(self):
        page = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        for category in CATEGORIES:
            self.assertIn('data-category="' + category + '"', page)


if __name__ == "__main__":
    unittest.main()

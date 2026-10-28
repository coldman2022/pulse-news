import json
import unittest
from pathlib import Path

import server

ROOT = Path(__file__).resolve().parent


class MobileAndTranslationTests(unittest.TestCase):
    def test_language_is_preserved_from_source(self):
        feed = (b'<rss><channel><item><title>Warszawa</title>'
                b'<link>https://example.org/new</link></item></channel></rss>')
        articles = server.parse_feed(feed, {
            "name": "Polish source", "category": "Польща", "language": "pl"
        })
        self.assertEqual(articles[0]["language"], "pl")

    def test_source_language_metadata(self):
        sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
        self.assertTrue(sources)
        self.assertTrue(all(s.get("language") in {"en", "uk", "pl"} for s in sources))
        self.assertEqual(next(s for s in sources if s["name"] == "Українська правда")["language"], "uk")
        self.assertEqual(next(s for s in sources if s["name"] == "RMF24 Polska")["language"], "pl")

    def test_translation_and_mobile_layout_are_present(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("api.mymemory.translated.net/get", js)
        self.assertIn("translationChunks", js)
        self.assertIn("Перекласти опис українською", js)
        self.assertNotIn("translate.google.com/translate?", js)
        self.assertIn("overflow-x: auto;", css)
        self.assertIn("flex-wrap: nowrap;", css)
        self.assertIn("font-size: 16px;", css)
        self.assertIn('name="viewport" content="width=device-width,initial-scale=1"', html)


if __name__ == "__main__":
    unittest.main()

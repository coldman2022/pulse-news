"""Pulse v22 regression: subtle surfaces, clean headlines, unchanged UI structure."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "static"


class LightSurfaceTests(unittest.TestCase):
    def test_color_adjustments_do_not_change_geometry(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        override = css.split("/* Pulse v22: softer near-white surfaces", 1)[1]
        for token in ("--paper:#fcfbfd", "--card-bg:#f9f8ff",
                      "background:#faf7ff", "background:#fbfbed",
                      "background:#fff9f5"):
            self.assertIn(token, override)
        for token in ("padding:", "margin:", "border-radius:", "font-size:",
                      "grid-template:", "min-height:", "max-height:",
                      "line-height:", "letter-spacing:", "display:"):
            self.assertNotIn(token, override)

    def test_article_titles_are_not_underlined(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        override = css.split("/* Pulse v22: softer near-white surfaces", 1)[1]
        self.assertIn("#news .story-heading a,", override)
        self.assertIn(".reddit-preview-title,", override)
        self.assertIn(".reddit-post-title,", override)
        self.assertIn(".digest-item-title,", override)
        self.assertIn(".brief-title,", override)
        self.assertIn("text-decoration:none!important", override)
        # Interactive links such as 'Програма та участь' retain their existing affordances.
        self.assertNotIn(".event-bottom .event-action", override)

    def test_i_phone_background_and_cache_version(self):
        for name in ("index.html", "digest.html", "opportunities.html", "reddit.html"):
            page = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("style.css?v=23", page)
            self.assertIn('content="#fcfbfd"', page)
        manifest = (ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('"background_color": "#fcfbfd"', manifest)
        self.assertIn('"theme_color": "#fcfbfd"', manifest)


if __name__=="__main__":
    unittest.main()

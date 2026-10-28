"""Pulse v23 only restores v21 backgrounds 10% closer to white."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "static"


class V23BackgroundTests(unittest.TestCase):
    def test_original_card_colors_are_lifted_by_ten_percent(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        section = css.split("/* Pulse v23 —", 1)[1]
        colors = {
            "#f7f3ec": "#f8f4ee",  # Page background
            "#f1eafa": "#f2ecfb",  # AI event
            "#f2eefb": "#f3f0fb",  # Immigration stories
            "#f0e9fa": "#f2ebfb",  # AI stories
            "#eeeffd": "#f0f1fd",  # World stories
            "#f5effb": "#f6f1fb",  # Reddit
            "#f1ecfa": "#f2eefb",  # Personal mode background
        }
        for original, expected in colors.items():
            calculated = "#" + "".join(
                f"{int(int(original[i:i+2], 16)*.9+255*.1+0.5000001):02x}"
                for i in (1,3,5)
            )
            self.assertEqual(calculated, expected)
            self.assertIn(expected, section)

    def test_only_paint_updates_not_typography_or_layout(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        section = css.split("/* Pulse v23 —", 1)[1]
        # Check CSS declarations, not media-query conditions such as max-width.
        properties = re.findall(r"(?<=[{;])\s*([a-z-]+)\s*:", section)
        self.assertTrue(properties)
        self.assertTrue(all(prop == "background" or prop.startswith("--") for prop in properties), properties)
        # Keep the previous request: headline links are never underlined.
        v22 = css.split("/* Pulse v22:", 1)[1].split("/* Pulse v23 —", 1)[0]
        self.assertIn("#news .story-heading a,", v22)
        self.assertIn("text-decoration:none!important", v22)

    def test_theme_assets_match_earlier_more_contrasting_background(self):
        for page in ("index.html", "digest.html", "opportunities.html", "reddit.html"):
            html = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn("style.css?v=24", html)
            self.assertIn('content="#f8f4ee"', html)
        manifest = (ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('"background_color": "#f8f4ee"', manifest)
        self.assertIn('"theme_color": "#f8f4ee"', manifest)


if __name__=="__main__":
    unittest.main()

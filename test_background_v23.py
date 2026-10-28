"""Regression guard: only the shared background changed in v24."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "static"


class BackgroundOnlyV24Tests(unittest.TestCase):
    def test_v24_override_only_paints_global_page(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        section = css.split("/* Pulse v24: ONLY the global background", 1)[1].split("/* Pulse v25:",1)[0]
        self.assertIn(":root{--paper:#f0f0f3}", section)
        self.assertIn("body,header{background:var(--paper)}", section)
        self.assertNotIn(".event-card", section)
        self.assertNotIn(".story--topic-", section)
        self.assertNotIn(".reddit-preview-item", section)
        self.assertNotIn(".focus-hero", section)
        self.assertNotIn('body[data-pulse-mode="focus"]', section)
        self.assertNotIn("text-decoration:", section)

    def test_v22_soft_topic_cards_and_plain_titles_survive(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        v22 = css.split("/* Pulse v22:", 1)[1].split("/* Pulse v24:", 1)[0]
        for token in (
            '.event-card[data-topic="AI"]{background:#faf7ff}',
            '.event-card[data-topic="Product"]{background:#fbfbed}',
            '.event-card[data-topic="Design"]{background:#fff9f5}',
            '.reddit-preview-item{background:#faf8fe}',
            '.story--topic-ai{--card-bg:#faf7ff}',
            '.story--topic-migration{--card-bg:#f9f8ff}',
            'body[data-pulse-mode="focus"]{background:#f9f7fd}',
            'text-decoration:none!important',
        ):
            self.assertIn(token, v22)

    def test_pwa_and_html_match_gray_background(self):
        for page in ("index.html","digest.html","opportunities.html","reddit.html"):
            html = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn("style.css?v=28", html)
            self.assertIn('content="#f0f0f3"', html)
        manifest = (ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('"background_color": "#f0f0f3"', manifest)
        self.assertIn('"theme_color": "#f0f0f3"', manifest)


if __name__ == "__main__":
    unittest.main()

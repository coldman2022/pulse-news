"""Interface contract for Pulse v20 mobile and personal-feed refresh."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "static"


class VisualV20Tests(unittest.TestCase):
    def test_header_date_not_large_news_heading(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('<time id="today" class="header-date"></time>', html)
        self.assertLess(html.index('id="today"'), html.index('id="fx-pln"'))
        self.assertNotIn('<h1>Новини</h1>', html)
        self.assertNotIn('class="intro"', html)
        self.assertIn("format(today) + ' р.'", js)
        self.assertIn('class="visually-hidden">Стрічка Pulse</h1>', html)

    def test_personal_mode_has_own_visual_identity_and_hides_home_modules(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="focus-hero"', html)
        self.assertIn('id="focus-hero-stat"', html)
        self.assertIn("document.body.dataset.pulseMode=mode", js)
        self.assertIn("personalHero.hidden=mode!=='focus'", js)
        self.assertIn('body[data-pulse-mode="focus"] #events-section', css)
        self.assertIn('body[data-pulse-mode="focus"] #reddit-preview', css)
        self.assertIn('.focus-hero{', css)

    def test_search_is_same_page_dock_panel(self):
        mobile = (ROOT / "mobile.js").read_text(encoding="utf-8")
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        self.assertIn("{key:'search',label:'Пошук',mode:'search'}", mobile)
        self.assertNotIn("href:'./?search=1'", mobile)
        self.assertIn("searchButton.addEventListener('click'", mobile)
        self.assertIn("searchPanel.hidden=false", mobile)
        self.assertIn("searchPanel.hidden=true", mobile)
        self.assertIn("searchInput.focus({preventScroll:true})", mobile)
        self.assertIn("fetch('./feed.json',{cache:'no-store'})", mobile)
        self.assertIn("safeArticleLink(item.url)", mobile)
        self.assertIn("aria-modal','true'", mobile)
        self.assertIn(".pulse-dock-search[hidden]", css)
        self.assertIn("bottom:calc(76px + env(safe-area-inset-bottom,0px))", css)
        self.assertIn("window.scrollTo({top:0,behavior:'smooth'})", mobile)

    def test_colored_states_do_not_introduce_card_outlines(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        for token in ("--pulse-accent:#137a70", ".pulse-dock-item.is-active",
                      ".pulse-dock-item.is-active::before",
                      ".event-card[data-topic=\"AI\"]",
                      ".reddit-preview-header h2::before",
                      ".event-bottom .event-action",
                      ".story--topic-migration"):
            self.assertIn(token, css)
        self.assertIn("border:0!important", css)


if __name__ == "__main__":
    unittest.main()

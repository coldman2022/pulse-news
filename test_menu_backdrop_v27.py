"""The bottom menu dims the page without affecting search or share overlays."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "static"


class MobileMenuBackdropTests(unittest.TestCase):
    def test_menu_has_its_own_clickable_backdrop(self):
        js = (ROOT/"mobile.js").read_text(encoding="utf-8")
        for text in (
            "menuBackdrop.className='pulse-dock-menu-backdrop'",
            "menuBackdrop.hidden=true",
            "document.body.append(menuBackdrop,backdrop,searchPanel,sheet,dock)",
            "menuBackdrop.hidden=sheet.hidden",
            "menuBackdrop.addEventListener('click',closeSheet)",
            "function closeSheet()",
            "menuBackdrop.hidden=true;",
            "closeSheet();",
            "closeSearch();",
        ):
            self.assertIn(text, js)

    def test_backdrop_sits_below_menu_and_dock(self):
        css = (ROOT/"style.css").read_text(encoding="utf-8")
        section = css.split("/* Pulse v27",1)[1]
        self.assertIn(".pulse-dock-menu-backdrop[hidden]{display:none!important}", section)
        self.assertIn("background:rgba(28,24,45,.24)", section)
        self.assertIn("z-index:118", section)
        self.assertIn("@media(max-width:760px)", section)
        self.assertIn("@media(min-width:761px)", section)
        self.assertIn(".pulse-dock-sheet{", css)
        self.assertIn("position:fixed;z-index:119;", css)
        self.assertIn("position:fixed;z-index:120;", css)

    def test_cache_refresh_on_every_page(self):
        for page in ("index.html","motivation.html","digest.html",
                     "reddit.html","opportunities.html"):
            html = (ROOT/page).read_text(encoding="utf-8")
            self.assertIn('style.css?v=29', html)
            self.assertIn('mobile.js?v=8', html)


if __name__ == "__main__":
    unittest.main()

"""Prevent iOS keyboard dismissal from leaving a second dock popup."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parent/"static"

class SearchDismissRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=(ROOT/"mobile.js").read_text(encoding="utf-8")

    def test_hide_search_before_keyboard_blur(self):
        start=self.script.index("  function closeSearch() {")
        end=self.script.index("  const normalize=",start)
        body=self.script[start:end]
        self.assertLess(body.index("searchPanel.hidden=true;"),body.index("searchInput.blur();"))
        self.assertLess(body.index("backdrop.hidden=true;"),body.index("searchInput.blur();"))
        self.assertLess(body.index("sheet.hidden=true;"),body.index("searchInput.blur();"))
        self.assertLess(body.index("menuBackdrop.hidden=true;"),body.index("searchInput.blur();"))
        for snippet in (
            "searchPanel.style.animation='none';",
            "menu.setAttribute('aria-expanded','false');",
            "searchButton.setAttribute('aria-expanded','false');",
            "syncSearchViewport();",
            "document.body.classList.remove('pulse-search-open');",
            "document.body.style.overflow=previousOverflow;",
            "selected(primaryMode);",
        ):
            self.assertIn(snippet,body)

    def test_new_search_resets_closed_animation_and_close_event_is_single(self):
        self.assertIn("searchPanel.style.removeProperty('animation');",self.script)
        self.assertIn("const searchWasJustDismissed=()=>Date.now()-lastSearchDismissedAt<400;",self.script)
        self.assertIn("if(searchPanel.hidden && searchWasJustDismissed())",self.script)
        self.assertIn("if(searchWasJustDismissed())",self.script)
        self.assertIn("searchPanel.querySelector('.pulse-dock-search-close').addEventListener('click',closeSearch);",self.script)
        self.assertIn("searchInput.addEventListener('blur',syncSearchViewport);",self.script)
        self.assertIn("if(!searchPanel.hidden)renderSearch();",self.script)

    def test_versions_on_all_mobile_pages(self):
        for page in ("index","digest","motivation","opportunities","reddit",
                     "today","radar","search","collections"):
            page_markup=(ROOT/(page+".html")).read_text(encoding="utf-8")
            self.assertIn("mobile.js?v=8",page_markup,page)
            self.assertNotIn("mobile.js?v=7",page_markup,page)

if __name__=="__main__":
    unittest.main()

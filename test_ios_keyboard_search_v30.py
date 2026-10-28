"""Regression tests: iPhone search stays above the soft keyboard."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent/"static"

class IOSKeyboardSearchTests(unittest.TestCase):
    def test_use_visual_viewport_to_keep_search_input_visible(self):
        js=(ROOT/"mobile.js").read_text(encoding="utf-8")
        for value in (
            "function syncSearchViewport(){",
            "document.activeElement===searchInput",
            "window.visualViewport",
            "viewport?.offsetTop",
            "viewport?.height",
            "pulse-dock-search--editing",
            "--pulse-visible-top",
            "--pulse-visible-height",
            "window.visualViewport.addEventListener('resize',syncSearchViewport",
            "window.visualViewport.addEventListener('scroll',syncSearchViewport",
            "searchInput.addEventListener('focus',syncSearchViewport)",
            "searchInput.addEventListener('blur',syncSearchViewport)",
            "searchInput.blur();",
            "searchInput.focus({preventScroll:true});",
        ):
            self.assertIn(value,js)
        self.assertIn("document.body.style.overflow='hidden';",js)
        self.assertIn("searchPanel.hidden=true;",js)
        self.assertIn("searchPanel.style.removeProperty('--pulse-visible-top');",js)

    def test_focused_sheet_scrolls_within_visible_viewport(self):
        css=(ROOT/"style.css").read_text(encoding="utf-8")
        v30=css.split("/* Pulse v30",1)[1]
        for rule in (
            "@media(max-width:760px)",
            ".pulse-dock-search.pulse-dock-search--editing{",
            "top:calc(var(--pulse-visible-top,0px) + 8px);",
            "bottom:auto;",
            "height:calc(var(--pulse-visible-height,100dvh) - 16px);",
            "max-height:calc(var(--pulse-visible-height,100dvh) - 16px);",
            "min-height:0;",
            "overflow:hidden;",
            ".pulse-dock-search--editing .pulse-dock-search-results{",
            "overflow-y:auto;",
            ".pulse-dock-search--editing ~ .pulse-dock{",
        ):
            self.assertIn(rule,v30)
        self.assertNotIn("touch-action:none",v30)

    def test_refresh_script_and_style_on_every_page(self):
        for page in ("index","search","today","radar","collections","motivation",
                     "digest","opportunities","reddit"):
            html=(ROOT/(page+".html")).read_text(encoding="utf-8")
            self.assertIn("style.css?v=29",html,page)
            self.assertIn("mobile.js?v=8",html,page)

if __name__=="__main__":
    unittest.main()

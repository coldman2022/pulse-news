"""Long-press sharing should not add permanent share buttons or block scrolling."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent/"static"

class PressHoldShareTests(unittest.TestCase):
    def test_native_sheet_and_copy_fallback(self):
        js=(ROOT/"share.js").read_text(encoding="utf-8")
        for token in (
            "LONG_PRESS_MS=550", "MOVE_TOLERANCE_PX=12",
            "document.addEventListener('pointerdown'", "document.addEventListener('pointermove'",
            "document.addEventListener('pointerup'", "document.addEventListener('pointercancel'",
            "document.addEventListener('scroll',clearPress",
            "document.addEventListener('contextmenu'",
            "document.addEventListener('click'", "event.preventDefault()",
            "event.stopImmediatePropagation()",
            "navigator.share({title:", "navigator.clipboard?.writeText",
            "window.prompt('Скопіюй посилання:'",
            "pulse-share-action pulse-share-native", "pulse-share-action pulse-share-copy",
            "aria-modal','true'", "document.addEventListener('keydown'",
            "return {deepLink,share,copy,enableLongPress}",
        ):
            self.assertIn(token,js)
        self.assertNotIn("function button(article",js)

    def test_cards_have_gesture_instead_of_share_icon(self):
        app=(ROOT/"app.js").read_text(encoding="utf-8")
        motivation=(ROOT/"motivation.js").read_text(encoding="utf-8")
        self.assertIn("PulseShare.enableLongPress(card,a)",app)
        self.assertIn("PulseShare.enableLongPress(row,a)",app)
        self.assertIn("PulseShare.enableLongPress(card,article,'story')",motivation)
        self.assertNotIn("PulseShare.button",app)
        self.assertNotIn("PulseShare.button",motivation)

    def test_styles_preserve_flat_cards_and_do_not_obstruct_scroll(self):
        css=(ROOT/"style.css").read_text(encoding="utf-8")
        section=css.split("/* Pulse v26:",1)[1]
        self.assertIn(".pulse-share-sheet",section)
        self.assertIn("border-radius:0",section)
        self.assertIn("pulse-share-backdrop[hidden]",section)
        self.assertIn("-webkit-touch-callout:none",section)
        self.assertNotIn("touch-action:none",section)
        index=(ROOT/"index.html").read_text(encoding="utf-8")
        motivation=(ROOT/"motivation.html").read_text(encoding="utf-8")
        self.assertIn('share.js?v=2',index)
        self.assertIn('app.js?v=20',index)
        self.assertIn('motivation.js?v=2',motivation)
        for file in ("index.html","motivation.html","digest.html","reddit.html","opportunities.html"):
            self.assertIn("style.css?v=28",(ROOT/file).read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()

"""Color-only UI update: protect existing card and navigation geometry."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "static"


class PaletteV21Tests(unittest.TestCase):
    def test_color_tokens_and_theme_are_consistent(self):
        css=(ROOT / "style.css").read_text(encoding="utf-8")
        theme=css.split("/* Pulse v21 — COLORS ONLY.",1)[1]
        for token in (
            "--pulse-accent:#4e2bb8", "--pulse-accent-strong:#25158a",
            "--pulse-lime:#e2e739", "--pulse-purple:#9557d2",
            "--pulse-orange:#ff8b57", "--paper:#f7f3ec",
            ".focus-hero{", ".pulse-dock-item.is-active",
            "body[data-pulse-mode=\"focus\"]", ".event-card[data-topic=\"AI\"]",
            "box-shadow:none!important"
        ):
            self.assertIn(token,theme)
        for page in ("index.html","digest.html","opportunities.html","reddit.html"):
            html=(ROOT / page).read_text(encoding="utf-8")
            self.assertIn('style.css?v=22',html)
            self.assertIn('content="#f7f3ec"',html)
        manifest=(ROOT/"manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('"background_color": "#f7f3ec"',manifest)
        self.assertIn('"theme_color": "#f7f3ec"',manifest)

    def test_only_color_paint_properties_in_override(self):
        css=(ROOT / "style.css").read_text(encoding="utf-8")
        theme=css.split("/* Pulse v21 — COLORS ONLY.",1)[1]
        # v21 must not silently change card shape, spacing, type, layout or navigation.
        forbidden = (
            "padding", "margin", "width", "height", "min-height", "max-height",
            "display", "position", "transform", "font-size", "line-height",
            "letter-spacing", "border-radius", "grid-template", "gap", "flex",
            "overflow", "stroke-width", "text-align", "text-decoration-thickness",
        )
        declarations=re.findall(r"(?<![-\w])([-\w]+)\s*:\s*[^;{}]+[;}]",theme)
        for prop in declarations:
            if prop.startswith("--"):
                continue
            self.assertNotIn(prop,forbidden,prop)
            self.assertTrue(
                prop in ("color","background","background-color",
                         "border-left-color","box-shadow","text-decoration-color"),
                prop
            )


if __name__=="__main__":
    unittest.main()

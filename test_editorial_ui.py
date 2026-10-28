import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parent


class EditorialDesignTests(unittest.TestCase):
    def test_save_icon_above_article_and_metadata_below(self):
        js=(ROOT/"static"/"app.js").read_text(encoding="utf-8")
        self.assertIn("story-bookmark",js)
        self.assertIn("newsIcon('bookmark')",js)
        self.assertIn("saver.setAttribute('aria-pressed'",js)
        self.assertIn("newsIcon('languages')",js)
        self.assertIn("bottom.append(date)",js)
        self.assertIn("if(translateButton)bottom.append(translateButton)",js)
        self.assertNotIn("bottom.append(el('span',a.country",js)
        self.assertNotIn("story--tone-",js)
        self.assertIn("story--topic-migration", (ROOT/"static"/"style.css").read_text(encoding="utf-8"))
        self.assertIn("card.append(top,content,bottom)",js)
        self.assertIn("story--feature",js)
        self.assertIn("story--wide",js)
        self.assertIn("story--compact",js)
        self.assertIn("img.loading='lazy'",js)
        self.assertIn("img.decoding='async'",js)
        self.assertIn("img.referrerPolicy='no-referrer'",js)
        self.assertIn("localStorage.setItem('pulse-show-images'",js)

    def test_borderless_and_mobile_columns(self):
        css=(ROOT/"static"/"style.css").read_text(encoding="utf-8")
        self.assertIn("/* Pulse editorial layout v6",css)
        self.assertIn("grid-template-columns:repeat(12,minmax(0,1fr))",css)
        self.assertIn("grid-column:span 12",css)
        self.assertIn("border:0",css)
        self.assertIn("grid-template-columns:minmax(0,1fr)",css)

    def test_photo_toggle_and_versioning(self):
        html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="show-images"',html)
        self.assertIn('id="filter-toggle"',html)
        self.assertIn('id="filter-panel"',html)
        self.assertIn('href="./digest.html"',html)
        self.assertNotIn('id="sort"',html)
        self.assertIn('style.css?v=8',html)
        self.assertIn('app.js?v=8',html)


if __name__=="__main__":
    unittest.main()

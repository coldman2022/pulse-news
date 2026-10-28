import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parent


class EditorialDesignTests(unittest.TestCase):
    def test_translation_and_bookmark_after_topic_source_and_date(self):
        js=(ROOT/"static"/"app.js").read_text(encoding="utf-8")
        self.assertIn("story-bookmark",js)
        self.assertIn("newsIcon('bookmark')",js)
        self.assertIn("saver.setAttribute('aria-pressed'",js)
        self.assertIn("newsIcon('languages')",js)
        self.assertIn("metadata.append(date)",js)
        self.assertIn("tools.append(tButton)",js)
        self.assertIn("tools.append(saver)",js)
        self.assertIn("bottom.append(metadata,tools)",js)
        self.assertIn("story-publisher-bottom",js)
        self.assertNotIn("PULSE / ",js)
        self.assertNotIn("bottom.append(el('span',a.country",js)
        self.assertNotIn("story--tone-",js)
        self.assertIn("story--topic-migration", (ROOT/"static"/"style.css").read_text(encoding="utf-8"))
        self.assertIn("card.append(content,bottom)",js)
        self.assertIn("story--feature",js)
        self.assertIn("story--wide",js)
        self.assertIn("story--compact",js)
        self.assertIn("img.loading='lazy'",js)
        self.assertIn("img.decoding='async'",js)
        self.assertIn("img.referrerPolicy='no-referrer'",js)
        self.assertIn("const imagesEnabled = true",js)

    def test_borderless_and_mobile_columns(self):
        css=(ROOT/"static"/"style.css").read_text(encoding="utf-8")
        self.assertIn("/* Pulse editorial layout v6",css)
        self.assertIn("grid-template-columns:repeat(12,minmax(0,1fr))",css)
        self.assertIn("grid-column:span 12",css)
        self.assertIn("border:0",css)
        self.assertIn("grid-template-columns:minmax(0,1fr)",css)

    def test_clean_reader_without_settings_clutter(self):
        html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="show-images"',html)
        self.assertNotIn('id="auto-translate"',html)
        self.assertNotIn('id="translation-budget"',html)
        self.assertNotIn('Дати перевірено за сайтами',html)
        self.assertNotIn('Стрічка поєднує першоджерела',html)
        self.assertIn('id="filter-toggle"',html)
        self.assertIn('id="filter-panel"',html)
        self.assertIn('href="./digest.html"',html)
        self.assertNotIn('id="sort"',html)
        self.assertIn('style.css?v=17',html)
        self.assertIn('app.js?v=15',html)


if __name__=="__main__":
    unittest.main()

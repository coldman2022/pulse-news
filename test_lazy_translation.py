import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class LazyTranslationTests(unittest.TestCase):
    def test_site_keeps_budget_internally_without_secondary_controls(self):
        html=(ROOT/'static/index.html').read_text(encoding='utf-8')
        self.assertNotIn('id="auto-translate"', html)
        self.assertNotIn('id="translation-budget"', html)
        self.assertIn('style.css?v=17',html)
        self.assertIn('app.js?v=15',html)

    def test_viewport_only_with_budget_and_per_browser_cache(self):
        js=(ROOT/'static/app.js').read_text(encoding='utf-8')
        for expected in [
            'IntersectionObserver', 'isArticleOnScreen',
            '650', 'AUTO_MAX_CHARS = 2400',
            'pulse-auto-usage', 'pulse-title-translations',
            'autoQueue.length=0', 'translationChunks(title)',
            "const autoEnabled = true",
        ]:
            self.assertIn(expected, js)
        self.assertIn("const title = translatedTitles[article.id]",js)

    def test_no_github_runner_translation_or_paid_key(self):
        workflow=(ROOT/'.github/workflows/pages.yml').read_text(encoding='utf-8')
        self.assertNotIn('translate_news.py',workflow)
        self.assertNotIn('argos-translate',workflow)

if __name__=='__main__': unittest.main()

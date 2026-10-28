"""Motivation feed uses real publisher material rather than synthetic slogans."""
import unittest
from pathlib import Path
import motivation_feed

ROOT=Path(__file__).resolve().parent
NOW=1_800_000_000

def story(title, idx="x", summary="", stamp=NOW, category="Мотивація"):
    return dict(id=idx,title=title,category=category,summary=summary,
                url="https://example.org/"+idx,source="YC",publisher="YC",
                published=stamp,origin="expert",language="en")

class FounderStoryTests(unittest.TestCase):
    def test_candid_founder_journey_and_resilience(self):
        accepted=[
            story("How a founder struggled for years before building a business","a"),
            story("Startup founder: lessons learned after our failed launch","b"),
            story("An entrepreneur started a company after 10 years","c"),
        ]
        data=motivation_feed.build_motivation_feed(accepted,NOW)
        self.assertEqual(len(data["articles"]),3)
        self.assertEqual(data["articles"][1]["story_type"],"Після невдач")
        self.assertEqual(data["articles"][1]["url"],accepted[1]["url"])
        self.assertEqual(data["articles"][1]["summary"],accepted[1]["summary"])

    def test_no_vapid_promo_or_unsourced_quote(self):
        ignored=[
            story("10x your passive income with a founder secret hack","promo"),
            story("Company raises $20 million in a funding round","fund"),
            story("How to buy stocks this month","stocks"),
            story("A founder's story from 8 months ago","old",stamp=NOW-260*86400),
            story("A founder struggled for years","not-ours",category="Світ"),
        ]
        self.assertEqual(motivation_feed.select_journeys(ignored,NOW),[])

    def test_motivation_has_own_section_and_source_links(self):
        html=(ROOT/"static/motivation.html").read_text(encoding="utf-8")
        js=(ROOT/"static/motivation.js").read_text(encoding="utf-8")
        homepage=(ROOT/"static/index.html").read_text(encoding="utf-8")
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        self.assertIn('id="motivation-list"',html)
        self.assertIn('href="https://news.stanford.edu/stories/2005/06/youve-got-find-love-jobs-says"',html)
        self.assertIn("paulgraham.com/ds.html",html)
        self.assertIn("PulseShare.enableLongPress(card,article,'story')",js)
        self.assertIn("safeUrl(article.url)",js)
        self.assertIn('href="./motivation.html"',homepage)
        self.assertIn('data-category="Мотивація"',homepage)
        self.assertIn("motivation_feed.build_motivation_feed",build)

if __name__=="__main__":
    unittest.main()

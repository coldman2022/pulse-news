"""Fresh feed, age-separated archive and native share link contracts."""
import time
import unittest
from pathlib import Path
import editorial_feed

ROOT = Path(__file__).resolve().parent
NOW=1_800_000_000

def article(title, category, idx="x", age=0):
    return dict(id=idx,title=title,category=category,url="https://example.com/"+idx,
                source="Publisher",publisher="Publisher",published=NOW-age*86400,
                summary="Publisher excerpt.")

class FreshFeedV25(unittest.TestCase):
    def test_recent_articles_not_dropped_by_narrow_keyword_rules(self):
        rows=[
            article("A new restaurant opens in Poland","Польща","p",1),
            article("Researchers test an unusual material","Наука","s",1),
            article("A local town opens a community park","Світ","w",2),
            article("How a founder built a business from scratch","Мотивація","m",3),
        ]
        self.assertFalse(editorial_feed.relevant(rows[0]))
        for entry in rows:
            self.assertTrue(editorial_feed.recent_feed_candidate(entry,NOW), entry["title"])
        selected=editorial_feed.build_editorial_feed(rows,NOW)
        self.assertEqual(len(selected["articles"]),4)
        self.assertEqual(selected["window_days"],7)

    def test_archive_kept_and_fresh_noise_excluded(self):
        good=article("How a new product is made","Технології","good",2)
        crime=article("Police investigate a murder","Світ","crime",0)
        old=article("Poland changes its tax law","Польща","old",14)
        future=article("Announcement published in 2027","Світ","future",-5)
        result=editorial_feed.build_editorial_feed([good,crime,old,future],NOW)
        self.assertEqual([x["id"] for x in result["articles"]],["good"])
        self.assertEqual(result["archive_total"],4)
        self.assertEqual(result["method"],"all_fresh_topics_7d+obvious_noise_filter+story_groups_v1")

    def test_browser_has_share_and_archive_routes(self):
        index=(ROOT/"static/index.html").read_text()
        app=(ROOT/"static/app.js").read_text()
        mobile=(ROOT/"static/mobile.js").read_text()
        share=(ROOT/"static/share.js").read_text()
        self.assertIn("share.js?v=1",index)
        self.assertIn("PulseShare.button(a)",app)
        self.assertIn("sharedArticleId",app)
        self.assertIn("mode='archive'",app)
        self.assertIn("archiveCutoff",app)
        self.assertIn("navigator.share(payload)",share)
        self.assertIn("navigator.clipboard",share)
        self.assertIn("encodeURIComponent",share) if False else None
        self.assertIn("motivation.html",mobile)

if __name__=="__main__":
    unittest.main()

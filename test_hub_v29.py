"""Pulse v29 feature regressions without network or a real browser."""
import unittest
from pathlib import Path

import story_clusters
import editorial_feed
import translate_batch

ROOT=Path(__file__).resolve().parent
STATIC=ROOT/"static"
NOW=1800000000


def news(ident,title,lang,category="AI",when=NOW,source="Source"):
    return {
        "id": f"{ident:020x}", "title": title,"language":lang,
        "url":"https://example.com/story/"+str(ident),
        "publisher":source,"source":source,"category":category,
        "origin":"media","summary":"Publisher text","published":when,
    }


class HubUpgradeTests(unittest.TestCase):
    def test_cross_language_merge_with_verified_translation_only(self):
        english=news(1,"OpenAI releases an advanced artificial intelligence model for businesses","en")
        ukrainian=news(2,"OpenAI представила нову модель штучного інтелекту для бізнесу","uk",source="Other")
        cache={english["id"]:{
            "source_title":english["title"],"language":"en",
            "title":ukrainian["title"],"summary":"Український опис"
        }}
        self.assertEqual(len(story_clusters.group_articles([english,ukrainian])),2)
        combined=story_clusters.group_articles([english,ukrainian],translations=cache)
        self.assertEqual(len(combined),1)
        self.assertEqual(combined[0]["related_sources"][0]["url"],ukrainian["url"])
        self.assertNotIn("related_sources",english)

    def test_cross_language_guard_wrong_title_or_topic_or_numbers(self):
        en=news(1,"New regulations for 2026 residency applicants","en","Імміграція")
        uk=news(2,"Нові правила для 2027 року для отримання посвідки","uk","Імміграція")
        cache={en["id"]:{"source_title":en["title"],"language":"en","title":uk["title"]}}
        self.assertEqual(len(story_clusters.group_articles([en,uk],translations=cache)),2)
        bad=dict(cache);bad[en["id"]]=dict(cache[en["id"]],source_title="stale")
        self.assertEqual(len(story_clusters.group_articles([en,uk],translations=bad)),2)
        uk["category"]="AI"
        self.assertEqual(len(story_clusters.group_articles([en,uk],translations=cache)),2)

    def test_editorial_still_retains_archive_and_originals(self):
        a=news(1,"OpenAI launches advanced reasoning models for customer support","en")
        b=news(2,"OpenAI запускає передові моделі міркування для підтримки клієнтів","uk",source="Another")
        cache={a["id"]:{"source_title":a["title"],"language":"en","title":b["title"]}}
        result=editorial_feed.build_editorial_feed([a,b],NOW,translations=cache)
        self.assertEqual(result["archive_total"],2)
        self.assertEqual(result["selected_total"],1)

    def test_translation_quality_guards_important_numbers(self):
        self.assertIsNone(translate_batch.clean_translation(
            "У 2027 році виходить 30 моделей", "In 2026, 30 models launch"))
        self.assertIsNone(translate_batch.clean_translation(
            "New regulations for 2026 residency", "New regulations for 2026 residency"))
        self.assertEqual(translate_batch.clean_translation(
            "Українські правила для 2026 року", "Regulations for 2026 applicants"),
            "Українські правила для 2026 року")
        self.assertIsNone(translate_batch.clean_translation(
            "Wrong English-only output for 2026", "Important update for 2026"))

    def test_personal_page_assets_and_no_calendar_offline_expansion(self):
        home=(STATIC/"index.html").read_text(encoding="utf-8")
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        for name in ("today","radar","search","collections"):
            page=(STATIC/(name+".html")).read_text(encoding="utf-8")
            self.assertIn('data-hub-page="'+name+'"',page)
            self.assertIn('pulse-hub.js?v=1',page)
            self.assertIn(name+".html",build)
            self.assertIn(name+".html",home)
        self.assertIn("pulse-hub.js",build)
        self.assertIn("pulse-extras.css",build)
        self.assertNotIn("serviceWorker.register",home)
        self.assertNotIn("calendar.google.com",home)

    def test_read_radar_search_collections_features_are_connected(self):
        js=(STATIC/"pulse-hub.js").read_text(encoding="utf-8")
        main=(STATIC/"app.js").read_text(encoding="utf-8")
        for expected in (
            "pulse-read-v1","pulse-radar-v1","pulse-collections-v1",
            "markRead(id)", "isRead(id)", "radarPage()",
            "searchPage()", "collectionsPage()", "today()",
            "matchesQuery(article,query", "searchTerms(query)",
            "source.onchange=render", "selectFolder.onchange=render",
            "Експортувати JSON", "pulse-collections.json",
        ):
            self.assertIn(expected,js)
        self.assertIn("unreadOnly",main)
        self.assertIn("hub-unread-filter",main)
        self.assertIn("pulse-is-read",main)

    def test_motivation_preserves_origins_and_can_save(self):
        html=(STATIC/"motivation.html").read_text(encoding="utf-8")
        script=(STATIC/"motivation.js").read_text(encoding="utf-8")
        self.assertIn("news.stanford.edu/stories/2005",html)
        self.assertIn("hub-founder-steps",html)
        self.assertIn("motivation-excerpt",script)
        self.assertIn("pulse-saved",script)
        self.assertIn("collections.html",html)


if __name__=="__main__":
    unittest.main()

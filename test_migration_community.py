"""Ukrainian-rights classification, fee honesty and Reddit RSS sunset safeguards."""
import json
from pathlib import Path
import unittest
import migration_relevance
import editorial_feed

ROOT=Path(__file__).resolve().parent

def article(title,country="Польща"):
    return dict(title=title,country=country,category="Імміграція",url="https://example.com/news",
                published=1800000000,source="BBC World",origin="media")

class MigrationAndCommunityTests(unittest.TestCase):
    def test_direct_ukrainian_rights_outweigh_country(self):
        for row in (
            article("Poland extends temporary protection for Ukrainian refugees"),
            article("PESEL UKR status new rules"),
            article("Australia announces special visa for Ukrainian refugees","Австралія"),
            article("Poland new pobyt rules for Ukrainians")):
            self.assertEqual(migration_relevance.migration_scope(row),"ukrainian")

    def test_general_legal_routes_are_distinct_from_ukrainian_protections(self):
        for row in (
            article("Canada changes citizenship application rules","Канада"),
            article("Poland introduces new residence permits for workers"),
            article("EU reforms Blue Card rules","ЄС"),
        ):
            self.assertEqual(migration_relevance.migration_scope(row),"general")

    def test_irrelevant_stories_not_selected(self):
        rejected=(
            article("Canada announces visa scheme for Nigerian citizens","Канада"),
            article("Immigration agency celebrates annual staff party","Канада"),
            article("New Zealand changes visa rules","Нова Зеландія"),
            article("Bird migration across Poland"),
            article("Ukrainian team wins game in Warsaw"),
            article("A Polish official was arrested in visa card fraud"),
        )
        for row in rejected:
            with self.subTest(title=row["title"]):
                self.assertIsNone(migration_relevance.migration_scope(row))
                self.assertFalse(editorial_feed.relevant(row))

    def test_tags_are_derived_and_archive_input_untouched(self):
        x=article("Poland extends temporary protection for Ukrainian refugees")
        y=article("Canada changes citizenship application rules","Канада")
        x["url"]="https://example.com/x"
        y["url"]="https://example.com/y"
        feed=editorial_feed.build_editorial_feed([x,y],1800000000)
        self.assertEqual({a["migration_scope"] for a in feed["articles"]},{"ukrainian","general"})
        self.assertNotIn("migration_scope",x)
        self.assertNotIn("migration_scope",y)
        self.assertEqual(feed["archive_total"],2)

    def test_ticket_states_and_sources(self):
        data=json.loads((ROOT/"static/events.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["events"]),16)
        self.assertTrue(all(x["fee"] in {"free","paid","unknown","mixed"} for x in data["events"]))
        self.assertTrue(all(x["fee_label"] for x in data["events"]))
        self.assertTrue(any(x["fee"]=="mixed" for x in data["events"]))
        html=(ROOT/"static/index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="event-sources"',html)
        self.assertNotIn('Календарі:',html)
        self.assertIn('id="events-track"',html)
        js=(ROOT/"static/events.js").read_text(encoding="utf-8")
        self.assertIn("event.fee_label",js)

    def test_reddit_is_separate_and_does_not_scrape_sunset_rss(self):
        html=(ROOT/"static/reddit.html").read_text(encoding="utf-8")
        index=(ROOT/"static/index.html").read_text(encoding="utf-8")
        self.assertIn('href="./reddit.html"',index)
        self.assertIn("13 листопада 2026",html)
        self.assertIn("https://www.reddit.com/r/LocalLLaMA/new/",html)
        self.assertIn("https://www.reddit.com/r/ukraine/new/",html)
        self.assertNotIn(".rss",html)
        self.assertIn("reddit.js?v=2",html)
        self.assertIn('id="reddit-feed-list"',html)
        self.assertNotIn("fetch(",html)

if __name__=="__main__":
    unittest.main()

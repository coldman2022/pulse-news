"""Editorial relevance and geographic constraints; never delete unselected news."""
import json
import unittest
from pathlib import Path
import editorial_feed

ROOT = Path(__file__).resolve().parent

def item(title, category, country="", id="1", source="BBC World"):
    return {"id": id, "title": title, "category": category, "country": country,
            "source": source, "publisher": source,
            "url": "https://example.org/news/" + id, "published": 1800000000,
            "summary": "Publisher supplied summary."}


class EditorialRelevanceTests(unittest.TestCase):
    def test_ukraine_is_broad_but_not_crime_or_corruption(self):
        accepted = ["В Україні змінили правила підтримки сімей",
                    "Україна підписала нову міжнародну угоду",
                    "У Києві відкрили новий технологічний центр",
                    "Верховна Рада проголосувала за бюджет"]
        excluded = ["У місті сталося вбивство", "Корупційний скандал у міськраді",
                    "У Львові затримали злочинця"]
        for text in accepted:
            self.assertTrue(editorial_feed.relevant(item(text,"Україна")),text)
        for text in excluded:
            self.assertFalse(editorial_feed.relevant(item(text,"Україна")),text)

    def test_immigration_targets_ukrainians_or_general_accessible_routes(self):
        yes = [
            item("Poland changes rules for temporary protection of Ukrainians", "Імміграція", "Польща"),
            item("Canada updates permanent residence permits", "Імміграція", "Канада"),
            item("Europe expands EU Blue Card for foreign workers", "Імміграція", "ЄС"),
            item("Australia announces special visa for Ukrainian refugees", "Імміграція", "Австралія")
        ]
        no = [
            item("New Zealand visa reform", "Імміграція", "Нова Зеландія"),
            item("Canada opens visa for Nigerian citizens", "Імміграція", "Канада"),
            item("Immigration agency celebrates annual staff party", "Імміграція", "Канада"),
            item("India changes visa rules for Indian nationals", "Імміграція", "Індія"),
        ]
        for x in yes:self.assertTrue(editorial_feed.relevant(x),x["title"])
        for x in no:self.assertFalse(editorial_feed.relevant(x),x["title"])

    def test_world_poland_and_technology_keep_only_material_stories(self):
        valid = [
            item("EU elections reshape parliament", "Світ"),
            item("Global economy faces new trade tariffs", "Світ"),
            item("Polska zmienia zasady pobytu cudzoziemców", "Польща"),
            item("Apple launches new iPhone and chipset", "Технології"),
            item("Researchers announce quantum computing breakthrough", "Наука")
        ]
        ignored = [
            item("Routine police arrest after bar fight", "Світ"),
            item("Corruption investigation in ministry", "Світ"),
            item("Local town opens a new cafe", "Польща"),
            item("A reviewer tests 20 dollar phone case", "Технології"),
        ]
        for x in valid:self.assertTrue(editorial_feed.relevant(x),x["title"])
        for x in ignored:self.assertFalse(editorial_feed.relevant(x),x["title"])

    def test_cinema_includes_releases_trailers_and_movie_collections(self):
        for title in ("New trailer for major sci-fi film",
                      "10 best movies to watch on Netflix",
                      "The 15 best films of 2026",
                      "Movie premiere dates for November",
                      "What to watch this weekend"):
            self.assertTrue(editorial_feed.relevant(item(title,"Кіно")),title)
        self.assertFalse(editorial_feed.relevant(item("Celebrity gossip about a private wedding","Кіно")))

    def test_selected_feed_keeps_full_archive_count_and_sorted_newest_first(self):
        entries=[
            item("OpenAI announces new model","AI",id="a"),
            item("Police investigate a murder","Світ",id="b"),
            item("Ukraine announces new education policy","Україна",id="c"),
            item("The 10 best movies to watch","Кіно",id="d")
        ]
        for index,news in enumerate(entries): news["published"]=1800000000+index
        payload=editorial_feed.build_editorial_feed(entries,1800000010)
        self.assertEqual(payload["archive_total"],4)
        self.assertEqual(payload["selected_total"],3)
        self.assertEqual([x["id"] for x in payload["articles"]],["d","c","a"])
        self.assertEqual(len(entries),4)

    def test_events_only_in_poland_and_seven_named_countries(self):
        data=json.loads((ROOT/"static/events.json").read_text(encoding="utf-8"))
        allowed={"Польща","Німеччина","Чехія","Словаччина",
                 "Румунія","Італія","Угорщина","Австрія"}
        self.assertGreaterEqual(len(data["events"]),5)
        self.assertTrue(all(e["country"] in allowed for e in data["events"]))
        self.assertTrue(any(e["region"]=="PL" for e in data["events"]))
        self.assertTrue(any(e["region"]=="EU" for e in data["events"]))
        js=(ROOT/"static/events.js").read_text(encoding="utf-8")
        self.assertIn("accessibleCountries[event.country] === event.region",js)
        self.assertIn("let eventRegion = 'PL'",js)

    def test_editorial_and_archive_are_separate_frontend_modes(self):
        html=(ROOT/"static/index.html").read_text(encoding="utf-8")
        js=(ROOT/"static/app.js").read_text(encoding="utf-8")
        for needle in ('data-mode="archive"','data-mode="all"','data-mode="focus"',
                       'data-category="Кіно"','data-events-region="EU"'):
            self.assertIn(needle,html)
        self.assertIn("'./feed.json'",js)
        self.assertIn("'./news.json'",js)
        self.assertIn("archiveCount",js)
        self.assertIn("visibleLimit+=60",js)


if __name__=="__main__":
    unittest.main()

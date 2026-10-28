import time
import unittest
import daily_digest


class DailyDigestTests(unittest.TestCase):
    NOW=1793000000

    def article(self, title, category="Світ", ago=1200, publisher="BBC", origin="media", ident=None):
        return {
            "id": ident or title,
            "title": title,
            "url": "https://example.org/story/" + (ident or title).replace(" ", "-"),
            "publisher": publisher,
            "source": publisher,
            "origin": origin,
            "summary": "Short publisher-provided RSS summary about this event.",
            "language": "en",
            "category": category,
            "published": self.NOW - ago,
        }

    def test_four_sections_and_time_window(self):
        rows = [
            self.article("World leaders meet for talks", "Світ", 3600),
            self.article("Canada opens new work permit program", "Імміграція", 7200, "IRCC", "official"),
            self.article("AI model published by lab", "AI", 1800, "DeepMind", "developer"),
            self.article("Conference dates announced", "AI-події", 600, "Tech News"),
            self.article("Very old article about world politics", "Світ", 90000),
            self.article("Future dated world article", "Світ", -600),
        ]
        report = daily_digest.build_digest(rows, self.NOW)
        self.assertEqual([s["category"] for s in report["sections"]],
                         ["Світ", "Імміграція", "AI", "AI-події"])
        self.assertEqual(report["total"], 4)
        self.assertEqual(report["period_hours"], 24)
        self.assertEqual(report["method"], "publisher_rss_excerpts")

    def test_respects_source_diversity_and_limits(self):
        rows = [self.article("Unique world title " + str(i).zfill(2), "Світ", i*600,
                             publisher="Same publisher", ident=str(i)) for i in range(12)]
        report=daily_digest.build_digest(rows,self.NOW)
        self.assertEqual(len(report["sections"][0]["items"]),2)

    def test_no_fabricated_summary(self):
        long_text="Publisher RSS summary " * 50
        row=self.article("World summit discusses climate")
        row["summary"]=long_text
        text=daily_digest.build_digest([row],self.NOW)["sections"][0]["items"][0]["summary"]
        self.assertTrue(text.endswith("…"))
        self.assertLessEqual(len(text),266)
        self.assertTrue(long_text.startswith(text[:-1]))
        row["summary"]=""
        result=daily_digest.build_digest([row],self.NOW)
        self.assertEqual(result["sections"][0]["items"][0]["summary"],"")

    def test_no_random_external_urls(self):
        row=self.article("World update today")
        row["url"]="javascript:alert(1)"
        self.assertEqual(daily_digest.build_digest([row],self.NOW)["total"],0)

    def test_same_story_covered_twice(self):
        a=self.article("World government talks - Reuters", publisher="Reuters",ident="a")
        b=self.article("World government talks - BBC", publisher="BBC",ident="b")
        self.assertEqual(daily_digest.build_digest([a,b],self.NOW)["total"],1)


if __name__ == "__main__":
    unittest.main()

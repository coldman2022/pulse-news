import unittest
import personal_feed

NOW = 1_800_000_000


def article(title, category="Світ", origin="media", publisher="Publisher", stamp=NOW, idx="1"):
    return {
        "id": idx, "title": title, "category": category,
        "origin": origin, "publisher": publisher, "source": publisher,
        "url": "https://example.com/" + idx,
        "published": stamp, "summary": "Unaltered RSS excerpt", "country": ""
    }


class PersonalFeedTests(unittest.TestCase):
    def test_immigration_and_polish_rights_are_first_class(self):
        examples = [
            article("Poland extends temporary protection for Ukrainian refugees", "Імміграція"),
            article("Polska zmienia zasady pobytu Ukraińców", "Польща"),
            article("Canada changes citizenship application rules", "Імміграція")
        ]
        for item in examples:
            with self.subTest(item=item["title"]):
                self.assertEqual(personal_feed.classify(item)[0], "featured")

    def test_not_every_immigration_article_is_urgent(self):
        item=article("IRCC department publishes annual report", "Імміграція", origin="official")
        self.assertEqual(personal_feed.classify(item)[0], "brief")

    def test_ai_release_is_featured_but_ai_opinion_is_not(self):
        feature=article("OpenAI launches new GPT model", "AI", origin="developer")
        minor=article("What researchers think of AI art", "AI")
        self.assertEqual(personal_feed.classify(feature)[0], "featured")
        self.assertEqual(personal_feed.classify(minor)[0], "brief")

    def test_crime_and_gossip_are_omitted_from_personal_feed(self):
        for item in (
            article("Police investigate murder in small village"),
            article("Actor's secret wedding revealed"),
            article("Polska: zabójstwo na ulicy", "Польща"),
            article("Вбивство у квартирі", "Україна")
        ):
            self.assertIsNone(personal_feed.classify(item)[0])

    def test_major_world_and_tech_go_to_short_brief(self):
        cases=[
            article("EU parliament votes on new sanctions", "Світ"),
            article("Apple unveils new processor", "Технології"),
            article("Major government election announced", "Світ"),
        ]
        for item in cases:
            self.assertEqual(personal_feed.classify(item)[0], "brief")
        self.assertIsNone(personal_feed.classify(article("Review of old headphones","Технології"))[0])

    def test_expired_and_http_news_are_not_in_personal_feed(self):
        items=[
            article("OpenAI launches new GPT model", "AI", origin="developer", idx="fresh"),
            article("OpenAI launches a major model", "AI", origin="developer", idx="old", stamp=NOW-200*3600),
            article("New citizenship application rules", "Імміграція", idx="http"),
        ]
        items[-1]["url"]="http://example.com/http"
        feed=personal_feed.build_personal_feed(items,NOW)
        self.assertEqual([a["id"] for a in feed["featured"]],["fresh"])

    def test_similar_syndicated_articles_not_repeated(self):
        data=[
            article("OpenAI launches GPT model with new reasoning features", "AI", "developer", "OpenAI", NOW, "one"),
            article("OpenAI launches GPT model with new reasoning features - Media", "AI", "media", "Media", NOW-5, "two")
        ]
        self.assertEqual(len(personal_feed.build_personal_feed(data,NOW)["featured"]),1)

    def test_featured_and_brief_are_bounded_and_newest_first(self):
        data = [
            article("OpenAI launches new GPT model version " + str(n), "AI", "developer",
                    "Source" + str(n), NOW - n*100, str(n))
            for n in range(40)
        ]
        feed=personal_feed.build_personal_feed(data,NOW)
        self.assertLessEqual(len(feed["featured"]),personal_feed.MAX_FEATURED)
        self.assertEqual(
            [a["published"] for a in feed["featured"]],
            sorted((a["published"] for a in feed["featured"]),reverse=True)
        )

    def test_integration_json_stays_independent_from_complete_feed(self):
        from pathlib import Path
        root=Path(__file__).resolve().parent
        build=(root/"build_site.py").read_text(encoding="utf-8")
        html=(root/"static/index.html").read_text(encoding="utf-8")
        js=(root/"static/app.js").read_text(encoding="utf-8")
        self.assertIn("'personal.json'",build)
        self.assertIn('data-mode="focus"',html)
        self.assertIn('id="brief-list"',html)
        self.assertIn("'./feed.json'",js)
        self.assertIn("'./personal.json'",js)
        self.assertIn("'./news.json'",js)
        self.assertIn("function renderBrief()",js)
        self.assertIn("mode==='focus'?focusArticles:mode==='archive'?archiveArticles:articles",js)


if __name__ == "__main__":
    unittest.main()

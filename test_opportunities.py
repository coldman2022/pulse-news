import unittest
import opportunities


class OpportunityTests(unittest.TestCase):
    def article(self, title, **kwargs):
        data = {
            "id": "a1",
            "title": title,
            "url": "https://www.canada.ca/en/immigration-refugees-citizenship/news.html",
            "category": "Імміграція",
            "country": "Канада",
            "origin": "official",
            "source": "IRCC",
            "publisher": "IRCC",
            "summary": "Official program announcement.",
            "published": 1700000000,
        }
        data.update(kwargs)
        return data

    def test_direct_official_is_source_verified_not_program_open(self):
        row = opportunities.classify_article(
            self.article("Canada launches new immigration pathway for skilled workers")
        )
        self.assertEqual(row["signal"], "Нова програма")
        self.assertEqual(row["evidence"], "офіційне повідомлення")
        self.assertIsNone(row["deadline"])
        self.assertIsNone(row["application_start"])
        self.assertIsNone(row["requirements"])
        self.assertIsNone(row["applications_open"])

    def test_fake_official_subdomain_not_trusted(self):
        row = opportunities.classify_article(self.article(
            "Canada launches new immigration pathway",
            url="https://www.canada.ca.evil.example/path"
        ))
        self.assertEqual(row["evidence"], "потребує перевірки")

    def test_google_news_is_never_official_even_for_gov_headline(self):
        row = opportunities.classify_article(self.article(
            "Canada launches new immigration pathway",
            origin="discovery",
            url="https://news.google.com/rss/articles/123",
        ))
        self.assertEqual(row["evidence"], "потребує перевірки")
        self.assertEqual(row["country"], "Канада")

    def test_speculation_is_marked_for_review(self):
        row = opportunities.classify_article(self.article(
            "Canada could introduce new immigration program",
        ))
        self.assertEqual(row["evidence"], "потребує перевірки")

    def test_unrelated_world_news_is_ignored(self):
        self.assertIsNone(opportunities.classify_article(self.article(
            "Canada launches new migration pathway", category="Світ"
        )))
        self.assertIsNone(opportunities.classify_article(self.article(
            "Canada launches new railway program"
        )))
        self.assertIsNone(opportunities.classify_article(self.article(
            "Canada immigration statistics published"
        )))

    def test_application_and_policy_signal(self):
        a = self.article("Canada visa applications open next week")
        b = self.article("Canada changes work permit rules")
        self.assertEqual(opportunities.classify_article(a)["signal"], "Заявки та реєстрація")
        self.assertEqual(opportunities.classify_article(b)["signal"], "Зміни правил")

    def test_unknown_country_for_generic_discovery(self):
        row = opportunities.classify_article(self.article(
            "New visa pathway launched",
            origin="discovery",
            country="Світ",
            url="https://news.google.com/rss/articles/123"
        ))
        self.assertEqual(row["country"], "Не визначено")

    def test_deduplicate_and_official_first(self):
        media = self.article("Canada launches new immigration pathway",
                             url="https://news.google.com/rss/articles/123",
                             origin="discovery", id="m1")
        gov = self.article("Canada launches new immigration pathway",
                           url="https://www.canada.ca/en/a", id="g1")
        result = opportunities.make_opportunities([media, gov, media])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "g1")


if __name__ == "__main__":
    unittest.main()

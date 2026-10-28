import unittest
import editorial_feed
import story_clusters


def story(title, category="AI", source="First", stamp=1800000000, suffix="1"):
    return {
        "id": suffix, "title": title, "category": category,
        "url": "https://example.org/" + suffix, "source": source,
        "publisher": source, "published": stamp, "origin": "media",
        "summary": "Original summary."
    }


class StoryClusteringTests(unittest.TestCase):
    def test_cross_publisher_near_duplicates_keep_original_links(self):
        a = story("OpenAI launches major new reasoning model for business customers",
                  source="First", suffix="1")
        b = story("OpenAI launches major new reasoning model for business customers today",
                  source="Second", stamp=1800000000-60, suffix="2")
        original = [a, b]
        grouped = story_clusters.group_articles(original)
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["url"], a["url"])
        self.assertEqual(grouped[0]["related_sources"][0]["url"], b["url"])
        self.assertEqual(grouped[0]["related_sources"][0]["publisher"], "Second")
        self.assertNotIn("related_sources", a)  # no mutation of archive objects

    def test_no_merge_for_changed_numbers_dates_or_topic(self):
        data = [
            story("OpenAI announces GPT 6 launch for public users", suffix="6"),
            story("OpenAI announces GPT 7 launch for public users", suffix="7"),
            story("OpenAI announces GPT 6 launch for public users", category="Технології",
                  suffix="different-category"),
            story("OpenAI announces GPT 6 launch for public users", stamp=1800000000-4*86400,
                  suffix="different-day"),
        ]
        self.assertEqual(len(story_clusters.group_articles(data)), 4)

    def test_negation_and_opposite_subjects_never_collapse(self):
        data = [
            story("Poland will extend residence permits for Ukrainian workers",
                  category="Імміграція", suffix="yes"),
            story("Poland will not extend residence permits for Ukrainian workers",
                  category="Імміграція", suffix="no"),
            story("Ukraine imposes restrictions on Russian companies",
                  category="Світ", suffix="a"),
            story("Russian companies impose restrictions on Ukraine",
                  category="Світ", suffix="b"),
        ]
        self.assertEqual(len(story_clusters.group_articles(data)), 4)

    def test_only_url_identical_is_deduplicated_regardless_of_title(self):
        data = [
            story("New verified technology release from OpenAI", suffix="1"),
            story("Different new technology release from OpenAI", suffix="1"),
        ]
        self.assertEqual(len(story_clusters.group_articles(data)), 1)

    def test_editorial_keeps_archive_count_and_related_source(self):
        data = [
            story("OpenAI launches major new reasoning model for business customers", suffix="1"),
            story("OpenAI launches major new reasoning model for business customers today",
                  source="Second", suffix="2"),
        ]
        result = editorial_feed.build_editorial_feed(data, 1800000001)
        self.assertEqual(result["archive_total"], 2)
        self.assertEqual(result["selected_total"], 1)
        self.assertEqual(result["grouped_count"], 1)
        self.assertEqual(len(result["articles"][0]["related_sources"]), 1)
        self.assertNotIn("related_sources", data[0])


if __name__ == "__main__":
    unittest.main()

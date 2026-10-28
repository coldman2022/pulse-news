import unittest
import server


class DiscoveryTests(unittest.TestCase):
    def test_only_known_publishers_in_discovery(self):
        self.assertTrue(server.recognized_publisher('https://www.canada.ca/'))
        self.assertTrue(server.recognized_publisher('https://news.bbc.co.uk/'))
        self.assertFalse(server.recognized_publisher('https://canada.ca.fake.example'))
        self.assertFalse(server.recognized_publisher('https://random-news.example'))
        self.assertFalse(server.recognized_publisher('https://www.reuters.com.fake.example'))

    def test_google_news_source_is_not_official_even_if_state_publisher(self):
        feed = (b'<rss><channel>'
                b'<item><title>Visa update - UKVI</title>'
                b'<link>https://news.google.com/rss/articles/123</link>'
                b'<source url="https://www.gov.uk">UK Visas</source>'
                b'<description>Entry requirements</description></item>'
                b'<item><title>Fake visa headline</title>'
                b'<link>https://news.google.com/rss/articles/456</link>'
                b'<source url="https://unverified-blog.invalid">Unverified</source></item>'
                b'</channel></rss>')
        source = {"name": "Visa discovery", "category": "Імміграція",
                  "origin": "discovery", "country": "UK", "language": "en"}
        rows = server.parse_feed(feed, source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["publisher"], "UK Visas")
        self.assertEqual(rows[0]["origin"], "discovery")
        self.assertEqual(rows[0]["country"], "UK")

    def test_official_atom_and_keyword_filter(self):
        atom = (b'<feed xmlns="http://www.w3.org/2005/Atom">'
                b'<entry><title>New visa route</title>'
                b'<link rel="alternate" href="https://www.gov.uk/a"/>'
                b'<updated>2026-10-27T10:00:00Z</updated></entry>'
                b'<entry><title>Police investigation</title>'
                b'<link href="https://www.gov.uk/b"/>'
                b'</entry></feed>')
        source = {"name": "Government", "category": "Імміграція",
                  "origin": "official", "language": "en", "require_terms": ["visa", "immigration"]}
        rows = server.parse_feed(atom, source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["origin"], "official")
        self.assertEqual(rows[0]["url"], "https://www.gov.uk/a")
        self.assertGreater(rows[0]["published"], 0)


if __name__ == "__main__":
    unittest.main()

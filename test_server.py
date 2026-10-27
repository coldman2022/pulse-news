import unittest
from unittest.mock import patch
import server
S = {'name':'Test','category':'Світ'}
class FeedTests(unittest.TestCase):
    def test_rss_filters_unsafe_links_and_cleans_html(self):
        data = b'<rss><channel><item><title>A &amp; B</title><link>https://example.org/a</link><description>&lt;b&gt;Hello&lt;/b&gt;</description><pubDate>Mon, 26 Oct 2026 12:00:00 GMT</pubDate></item><item><title>Bad</title><link>javascript:alert(1)</link></item></channel></rss>'
        rows = server.parse_feed(data,S)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['summary'],'Hello')
        self.assertEqual(rows[0]['title'],'A & B')
        self.assertGreater(rows[0]['published'],0)
    def test_atom(self):
        data = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title><link href="https://example.org/a"/><updated>2026-10-26T12:00:00Z</updated></entry></feed>'
        self.assertGreater(server.parse_feed(data,S)[0]['published'],0)
    def test_partial_failure_keeps_prior_news(self):
        sources = [{'name':'A','category':'Світ'}, {'name':'B','category':'Світ'}]
        article = dict(id='a',url='https://example.org/a',published=1)
        server.CACHE.clear()
        server.CACHE['by_source'] = {'B':[article]}
        def fetch(s):
            if s['name']=='B': raise OSError('offline')
            return [article]
        with patch.object(server.json,'loads',return_value=sources), patch.object(server,'fetch_source',side_effect=fetch):
            result=server.news()
        self.assertEqual(len(result['articles']),1)
        self.assertTrue(next(s for s in result['sources'] if s['name']=='B')['cached'])
        server.CACHE.clear()
if __name__=='__main__': unittest.main()

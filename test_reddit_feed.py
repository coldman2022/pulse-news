"""Offline tests: temporary first-party RSS trial, safety and graceful retirement."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import reddit_feed

NOW = dt.datetime(2026,10,28,9,0,tzinfo=dt.timezone.utc).timestamp()
RSS = ('''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>New useful AI model</title>
<link rel="alternate" href="https://www.reddit.com/r/LocalLLaMA/comments/abc123/new_model/"/>
<updated>2026-10-28T08:00:00Z</updated></entry>
<entry><title>A malicious outside link</title>
<link href="https://evil.example/r/LocalLLaMA/comments/abc456/name"/>
<updated>2026-10-28T07:00:00Z</updated></entry>
<entry><title>Old reddit post</title>
<link href="https://www.reddit.com/r/LocalLLaMA/comments/abc999/old/"/>
<updated>2026-10-01T07:00:00Z</updated></entry>
<entry><title>Wrong subreddit</title>
<link href="https://www.reddit.com/r/Other/comments/abc555/name/"/>
<updated>2026-10-28T08:00:00Z</updated></entry>
</feed>''').encode()


class RedditTrialTests(unittest.TestCase):
    def test_atom_only_bounded_valid_reddit_community_links(self):
        result = reddit_feed.parse_atom(RSS, 'LocalLLaMA', 'AI', NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'],'New useful AI model')
        self.assertEqual(result[0]['url'],
                         'https://www.reddit.com/r/LocalLLaMA/comments/abc123/new_model/')
        self.assertEqual(result[0]['topic'],'AI')
        self.assertEqual(result[0]['work_topic'],'')
        self.assertEqual(result[0]['work_score'],0)
        self.assertNotIn('author', result[0])
        self.assertNotIn('summary', result[0])

    def test_success_and_cache_respect_six_hour_polling(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'reddit.json'
            with patch.object(reddit_feed, '_fetch_one', return_value=
                              reddit_feed.parse_atom(RSS,'LocalLLaMA','AI',NOW)) as fetch:
                first=reddit_feed.build_reddit_preview(target, NOW)
                self.assertEqual(first['status'],'ok')
                self.assertTrue(first['posts'])
                self.assertEqual(len(first['sources']),len(reddit_feed.COMMUNITIES))
                self.assertEqual(fetch.call_count,len(reddit_feed.COMMUNITIES))
            with patch.object(reddit_feed,'_fetch_one',side_effect=AssertionError('polled too soon')):
                second=reddit_feed.build_reddit_preview(target, NOW+3600)
            self.assertEqual(second['posts'],first['posts'])

    def test_failure_never_invents_posts(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'reddit.json'
            with patch.object(reddit_feed,'_fetch_one',side_effect=OSError('403')):
                result=reddit_feed.build_reddit_preview(target,NOW)
            self.assertEqual(result['status'],'unavailable')
            self.assertEqual(result['posts'],[])
            self.assertEqual(len(result['sources']),len(reddit_feed.COMMUNITIES))
            self.assertTrue(all(not s['ok'] for s in result['sources']))

    def test_after_official_shutdown_no_fetch_or_stale_posts(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'reddit.json'
            target.write_text(json.dumps({'status':'ok','updated':NOW,'last_fetch_at':NOW,
                                          'posts':[{'title':'Old post'}],'sources':[]}))
            with patch.object(reddit_feed,'_fetch_one',side_effect=AssertionError('RSS retired')):
                result=reddit_feed.build_reddit_preview(target,reddit_feed.RETIRES_AT+3600)
            self.assertEqual(result['status'],'ended')
            self.assertFalse(result['posts'])

    def test_live_ui_independent_from_main_news_archive(self):
        frontend=(Path(__file__).parent/'static/reddit.js').read_text(encoding='utf-8')
        self.assertIn("'./reddit.json'",frontend)
        self.assertIn("data-reddit-topic",frontend)
        self.assertNotIn("'./news.json'",frontend)
        self.assertNotIn("'./feed.json'",frontend)
        workflow=(Path(__file__).parent/'.github/workflows/pages.yml').read_text(encoding='utf-8')
        self.assertIn('_site/reddit.json',workflow)


    def test_relevance_matches_practical_work_not_generic_ai_news(self):
        import reddit_feed
        self.assertEqual(reddit_feed.practical_work_signal(
            'How I built an app with Claude Code', 'ClaudeAI')[0], 'Розробка')
        self.assertEqual(reddit_feed.practical_work_signal(
            'My AI workflow using Figma in design', 'FigmaDesign')[0], 'Дизайн')
        self.assertEqual(reddit_feed.practical_work_signal(
            'Using Claude AI to deploy my Docker server', 'selfhosted')[0], 'Адміністрування')
        self.assertEqual(reddit_feed.practical_work_signal(
            'How to build my own server', 'selfhosted'), ('', 0))
        self.assertEqual(reddit_feed.practical_work_signal(
            'New AI model available today', 'ClaudeAI'), ('', 0))
        self.assertIn(('vibecoding', 'Застосунки'), reddit_feed.COMMUNITIES)
        self.assertIn(('selfhosted', 'Автоматизація'), reddit_feed.COMMUNITIES)

    def test_main_page_has_small_related_reddit_window(self):
        home=(Path(__file__).parent/'static/index.html').read_text(encoding='utf-8')
        app=(Path(__file__).parent/'static/app.js').read_text(encoding='utf-8')
        self.assertIn('id="reddit-preview"', home)
        self.assertIn('id="reddit-preview-list"', home)
        self.assertIn('href="./reddit.html"', home)
        self.assertIn("'./reddit.json'",app)
        self.assertIn("work_score",app)
        self.assertIn("chosen.length===4",app)
        self.assertIn("safeRedditUrl",app)

if __name__=='__main__':
    unittest.main()

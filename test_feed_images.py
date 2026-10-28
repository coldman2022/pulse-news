import unittest
import server


class FeedImageTests(unittest.TestCase):
    S = {"name":"BBC","category":"Світ","language":"en"}

    def test_media_thumbnail_and_copyright(self):
        raw = b'''<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><item>
        <title>Title</title><link>https://example.org/article</link>
        <media:content medium="image" type="image/jpeg" url="https://img.example.org/large.jpg">
        <media:thumbnail url="https://img.example.org/small.jpg"/>
        <media:copyright>Publisher copyright</media:copyright>
        </media:content></item></channel></rss>'''
        row=server.parse_feed(raw,self.S)[0]
        self.assertEqual(row["image_url"],"https://img.example.org/small.jpg")
        self.assertEqual(row["image_credit"],"Publisher copyright")

    def test_enclosure_image_ignores_audio(self):
        raw=b'''<rss><channel><item><title>A</title>
        <link>https://example.org/a</link>
        <enclosure url="https://example.org/clip.mp3" type="audio/mpeg"/>
        <enclosure url="https://images.example.org/photo.webp" type="image/webp"/>
        </item></channel></rss>'''
        row=server.parse_feed(raw,self.S)[0]
        self.assertEqual(row["image_url"],"https://images.example.org/photo.webp")

    def test_inline_html_image_and_tracking_pixel(self):
        raw=b'''<rss><channel><item><title>A</title><link>https://example.org/a</link>
        <description>&lt;p&gt;Caption&lt;/p&gt;&lt;img src="https://tracker.example.org/tracking.jpg" width="1"/&gt;&lt;img src="https://images.example.org/picture.jpg" width="480" height="320"/&gt;</description>
        </item></channel></rss>'''
        row=server.parse_feed(raw,self.S)[0]
        self.assertEqual(row["image_url"],"https://images.example.org/picture.jpg")
        self.assertEqual(row["summary"],"Caption")

    def test_images_from_non_https_or_local_are_rejected(self):
        for url in ("data:image/png;base64,AA","javascript:alert(1)",
                    "http://example.org/image.jpg","https://localhost/unsafe.jpg",
                    "https://images.example.org/photo.svg","https://127.0.0.1/hi.png"):
            self.assertEqual(server.safe_image_url(url),"")
        self.assertEqual(server.safe_image_url("https://cdn.example.org/preview.jpg"),"https://cdn.example.org/preview.jpg")

    def test_plain_rss_retains_no_image(self):
        raw=b'''<rss><channel><item><title>Plain</title>
        <link>https://example.org/article</link></item></channel></rss>'''
        row=server.parse_feed(raw,self.S)[0]
        self.assertEqual(row["image_url"],"")
        self.assertEqual(row["image_credit"],"")


if __name__ == "__main__":
    unittest.main()

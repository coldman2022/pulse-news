import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class EventCarouselTests(unittest.TestCase):
    def test_events_are_curated_organizer_links(self):
        payload = json.loads((ROOT / "static" / "events.json").read_text(encoding="utf-8"))
        events = payload["events"]
        self.assertGreaterEqual(len(events), 16)
        self.assertEqual(len(events), len({event["id"] for event in events}))
        self.assertTrue(any(event["region"] == "PL" for event in events))
        self.assertTrue(any(event["region"] == "EU" for event in events))
        self.assertTrue(any(event["topic"] == "Design" for event in events))
        self.assertTrue(any(event["topic"] == "Product" for event in events))
        for event in events:
            with self.subTest(title=event["title"]):
                self.assertRegex(event["start"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertLessEqual(event["start"], event["end"])
                self.assertTrue(event["url"].startswith("https://"))
                self.assertEqual(event["verified_on"], payload["curated"])
                self.assertTrue(event["description"])
                self.assertIn(event['fee'], {'free','paid','mixed','unknown'})
                self.assertTrue(event['fee_label'])

    def test_mobile_slider_and_filters_are_accessible(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "events.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
        for item in ('id="events-section"', 'id="events-track"', 'id="events-prev"',
                     'id="events-next"', 'data-events-region="PL"', 'events.js?v=6'):
            self.assertIn(item, html)
        self.assertIn("event.end >= eventDay()", js)
        self.assertIn("event-fee",js)
        self.assertIn('id="events-calendar"', html)
        self.assertIn('id="events-calendar-grid"', html)
        self.assertIn('id="events-calendar-toggle"', html)
        self.assertIn('function renderCalendar()', js)
        self.assertIn('selectedEventDay', js)
        self.assertIn('margin-left:-29px', css)
        self.assertIn('width:calc(100% + 58px)', css)

        self.assertIn("eventTrack.scrollBy", js)
        self.assertIn("requestAnimationFrame(updateEventArrows)", js)
        self.assertIn("eventSection.hidden = false", js)
        self.assertIn("PULSE_BUILD_EVENTS_JSON", js)
        self.assertIn("embeddedEvents.filter(eventIsValid)", js)
        self.assertIn("accessibleCountries[event.country] === event.region", js)
        self.assertIn("let eventRegion = 'PL'", js)
        self.assertNotIn('data-events-region="all"', html)
        self.assertIn("scroll-snap-type: x mandatory", css)
        self.assertIn("border-radius: 0 !important", css)
        self.assertIn("text-decoration: underline", css)

    def test_all_news_dates_have_time_but_no_year(self):
        feed = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        digest = (ROOT / "static" / "digest.js").read_text(encoding="utf-8")
        opportunities = (ROOT / "static" / "opportunities.js").read_text(encoding="utf-8")
        for code in (feed, digest, opportunities):
            self.assertIn("hour:'2-digit',minute:'2-digit'", code)
        self.assertNotIn("month:'short',year:'numeric'", feed)
        self.assertNotIn("month:'short',year:'numeric'", opportunities)

if __name__ == "__main__":
    unittest.main()

"""Offline rates / soft visual system smoke tests."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import currency_rates

ROOT=Path(__file__).resolve().parent
NOW=dt.datetime(2026,10,28,12,0,tzinfo=dt.timezone.utc).timestamp()


class NbuRatesTests(unittest.TestCase):
    def test_normalize_official_uah_quotes(self):
        records=[
            {"cc":"PLN","rate":10.1234,"exchangedate":"28.10.2026"},
            {"cc":"USD","rate":44.9876,"exchangedate":"28.10.2026"},
            {"cc":"EUR","rate":51.0,"exchangedate":"28.10.2026"}
        ]
        fx=currency_rates.normalize_rates(records,updated=NOW)
        self.assertEqual(fx["source"],"НБУ")
        self.assertEqual(fx["rates"]["PLN"],{"uah":10.1234,"date":"2026-10-28"})
        self.assertEqual(fx["rates"]["USD"],{"uah":44.9876,"date":"2026-10-28"})
        self.assertTrue(currency_rates.valid_snapshot(fx,NOW))

    def test_reject_missing_invalid_and_stale_rates(self):
        for records in (
            [],
            [{"cc":"PLN","rate":10.123,"exchangedate":"28.10.2026"}],
            [{"cc":"PLN","rate":float("nan"),"exchangedate":"28.10.2026"},
             {"cc":"USD","rate":44,"exchangedate":"28.10.2026"}],
            [{"cc":"PLN","rate":10,"exchangedate":"not-a-date"},
             {"cc":"USD","rate":44,"exchangedate":"28.10.2026"}]
        ):
            with self.assertRaises(ValueError):
                currency_rates.normalize_rates(records,NOW)
        stale = currency_rates.normalize_rates([
            {"cc":"PLN","rate":10.1,"exchangedate":"12.09.2026"},
            {"cc":"USD","rate":43.2,"exchangedate":"12.09.2026"}],updated=NOW)
        self.assertFalse(currency_rates.valid_snapshot(stale,NOW))

    def test_provider_outage_uses_valid_cache_not_guessed_values(self):
        entries=[{"cc":"PLN","rate":10.1,"exchangedate":"27.10.2026"},
                 {"cc":"USD","rate":44.2,"exchangedate":"27.10.2026"}]
        snapshot=currency_rates.normalize_rates(entries,updated=NOW-86400)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"currency.json"
            target.write_text(json.dumps(snapshot))
            with patch.object(currency_rates,"fetch_official_rates",side_effect=OSError("503")):
                saved=currency_rates.build_rates(target,NOW)
            self.assertEqual(saved["status"],"cached")
            self.assertEqual(saved["rates"]["PLN"]["uah"],10.1)
            with patch.object(currency_rates,"fetch_official_rates",side_effect=OSError("503")):
                expired=currency_rates.build_rates(target,NOW+15*86400)
            self.assertEqual(expired["status"],"unavailable")
            self.assertEqual(expired["rates"],{})

    def test_new_valid_rates_written(self):
        snapshot=currency_rates.normalize_rates([
            {"cc":"PLN","rate":11.1234,"exchangedate":"28.10.2026"},
            {"cc":"USD","rate":45.1234,"exchangedate":"28.10.2026"}],updated=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"currency.json"
            with patch.object(currency_rates,"fetch_official_rates",return_value=snapshot):
                result=currency_rates.build_rates(path,NOW)
            self.assertEqual(result["status"],"ok")
            self.assertEqual(json.loads(path.read_text())["rates"]["USD"]["uah"],45.1234)

    def test_header_has_two_rates_instead_of_refresh_button(self):
        html=(ROOT/"static/index.html").read_text(encoding="utf-8")
        js=(ROOT/"static/app.js").read_text(encoding="utf-8")
        fx=(ROOT/"static/currency.js").read_text(encoding="utf-8")
        self.assertIn('id="fx-pln"',html)
        self.assertIn('id="fx-usd"',html)
        self.assertIn('id="fx-date"',html)
        self.assertIn('currency.js?v=1',html)
        self.assertIn('style.css?v=15',html)
        self.assertNotIn('id="refresh"',html)
        self.assertNotIn("$('#refresh')",js)
        self.assertIn("setInterval(load,300000)",js)
        self.assertIn("'./currency.json'",fx)
        self.assertIn("'./currency.json'",fx)

    def test_no_card_outlines_and_topic_tints_are_muted(self):
        css=(ROOT/"static/style.css").read_text(encoding="utf-8")
        for token in (".story--topic-migration{--card-bg:#f5faf7",
                      ".story--topic-ai{--card-bg:#f8f7fc",
                      ".story--topic-world{--card-bg:#f7f9fc",
                      ".story--topic-ukraine{--card-bg:#fcfaf5",
                      ".event-card[data-topic=\"AI\"]{background:#f8f7fc",
                      "#news .story,#news .story--feature{",
                      "border:0!important",
                      ".fx-bar{"):
            self.assertIn(token,css)
        for page in ("digest.html","opportunities.html","reddit.html"):
            self.assertIn("style.css?v=15",(ROOT/"static"/page).read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()

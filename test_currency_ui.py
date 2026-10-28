"""Offline Monobank exchange-rate and header smoke tests."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import currency_rates

ROOT=Path(__file__).resolve().parent
NOW=dt.datetime(2026,10,28,12,0,tzinfo=dt.timezone.utc).timestamp()
STAMP=int(NOW-1800)


def mono_rows(stamp=STAMP):
    return [
        {"currencyCodeA":985,"currencyCodeB":980,"date":stamp,"rateCross":11.6566},
        {"currencyCodeA":840,"currencyCodeB":980,"date":stamp,"rateBuy":45.51,"rateSell":45.861},
        {"currencyCodeA":978,"currencyCodeB":980,"date":stamp,"rateBuy":50.6,"rateSell":51.2689},
    ]


class MonobankRatesTests(unittest.TestCase):
    def test_normalize_bank_sell_and_cross_quotes(self):
        result=currency_rates.normalize_rates(mono_rows(),updated=NOW)
        self.assertEqual(result["source"],"Monobank")
        self.assertEqual(result["rates"]["PLN"],{"uah":11.6566,"timestamp":STAMP,"kind":"cross"})
        self.assertEqual(result["rates"]["USD"],{"uah":45.861,"timestamp":STAMP,"kind":"sell"})
        self.assertTrue(currency_rates.valid_snapshot(result,NOW))

    def test_reject_missing_invalid_and_stale_rates(self):
        for rows in (
            [],
            [{"currencyCodeA":985,"currencyCodeB":980,"date":STAMP,"rateCross":11.6}],
            [{"currencyCodeA":985,"currencyCodeB":980,"date":STAMP,"rateCross":float("nan")},
             {"currencyCodeA":840,"currencyCodeB":980,"date":STAMP,"rateSell":45}],
            [{"currencyCodeA":985,"currencyCodeB":980,"date":"bad","rateCross":11.6},
             {"currencyCodeA":840,"currencyCodeB":980,"date":STAMP,"rateSell":45}],
        ):
            with self.assertRaises(ValueError):
                currency_rates.normalize_rates(rows,NOW)
        stale=currency_rates.normalize_rates(mono_rows(int(NOW-10*86400)),updated=NOW)
        self.assertFalse(currency_rates.valid_snapshot(stale,NOW))
        future=currency_rates.normalize_rates(mono_rows(int(NOW+7200)),updated=NOW)
        self.assertFalse(currency_rates.valid_snapshot(future,NOW))

    def test_provider_outage_uses_recent_cache_not_nbu(self):
        snapshot=currency_rates.normalize_rates(mono_rows(),updated=NOW-3600)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"currency.json"
            target.write_text(json.dumps(snapshot))
            with patch.object(currency_rates,"fetch_monobank_rates",side_effect=OSError("429")):
                cached=currency_rates.build_rates(target,NOW)
            self.assertEqual(cached["status"],"cached")
            self.assertEqual(cached["rates"]["PLN"]["uah"],11.6566)
            with patch.object(currency_rates,"fetch_monobank_rates",side_effect=OSError("503")):
                expired=currency_rates.build_rates(target,NOW+10*86400)
            self.assertEqual(expired["status"],"unavailable")
            self.assertEqual(expired["rates"],{})

    def test_new_valid_rates_written(self):
        snapshot=currency_rates.normalize_rates(mono_rows(),updated=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"currency.json"
            with patch.object(currency_rates,"fetch_monobank_rates",return_value=snapshot):
                result=currency_rates.build_rates(path,NOW)
            self.assertEqual(result["status"],"ok")
            self.assertEqual(json.loads(path.read_text())["rates"]["USD"]["uah"],45.861)

    def test_header_has_two_rates_without_date(self):
        html=(ROOT/"static/index.html").read_text(encoding="utf-8")
        js=(ROOT/"static/app.js").read_text(encoding="utf-8")
        fx=(ROOT/"static/currency.js").read_text(encoding="utf-8")
        self.assertIn('id="fx-pln"',html)
        self.assertIn('id="fx-usd"',html)
        self.assertNotIn('id="fx-source"',html)
        self.assertNotIn('id="fx-date"',html)
        self.assertNotIn("НБУ",html)
        self.assertIn('currency.js?v=3',html)
        self.assertIn('style.css?v=26',html)
        self.assertNotIn('id="refresh"',html)
        self.assertNotIn("$('#refresh')",js)
        self.assertIn("setInterval(load,300000)",js)
        self.assertIn("'./currency.json'",fx)
        self.assertNotIn("rate.date",fx)
        self.assertNotIn("НБУ",fx)
        self.assertIn("Monobank",fx)

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
            self.assertIn("style.css?v=26",(ROOT/"static"/page).read_text(encoding="utf-8"))


    def test_v16_visual_system_uses_square_neutral_surfaces(self):
        css=(ROOT/"static/style.css").read_text(encoding="utf-8")
        self.assertIn("Pulse v16 — calm utility design system",css)
        self.assertIn("--paper:#f2f3f3",css)
        self.assertIn("--pulse-white:#ffffff",css)
        self.assertIn("border-radius: 0 !important",css)
        self.assertIn("#news .story--feature",css)
        self.assertIn("aside nav > .opp-nav,aside nav > button",css)
        self.assertIn("#categories button.active::after",css)
        self.assertIn(".event-card[data-topic=\"Design\"]",css)
        self.assertIn(".reddit-post{background:#fff",css)
        self.assertNotIn("#ffcc00",css.split("/* Pulse v16 — calm utility design system")[1])
        for page in ("index.html","digest.html","opportunities.html","reddit.html"):
            html=(ROOT/"static"/page).read_text(encoding="utf-8")
            self.assertIn("style.css?v=26",html)
            self.assertIn('content="#f0f0f3"',html)

if __name__=="__main__":
    unittest.main()

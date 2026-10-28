"""Publish recent Monobank PLN and USD quotes, never substitute NBU reference rates."""
import json
import math
import time
import urllib.request
from pathlib import Path

MONOBANK_URL = "https://api.monobank.ua/bank/currency"
SOURCE_URL = "https://api.monobank.ua/docs/index.html"
CURRENCY_CODES = {"PLN": 985, "USD": 840}
UAH_CODE = 980
MAX_JSON_BYTES = 500_000
MAX_RATE_AGE_SECONDS = 72 * 3600
MAX_FUTURE_SECONDS = 10 * 60


def valid_rate(value):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and 0 < value < 10000
    )


def normalize_rates(rows, updated=None):
    """PLN uses Mono cross-rate, USD uses the bank's sell-rate."""
    if not isinstance(rows, list):
        raise ValueError("Monobank response must be a JSON array")
    selection = {}
    for code, currency in CURRENCY_CODES.items():
        matches = [
            item for item in rows
            if isinstance(item, dict)
            and item.get("currencyCodeA") == currency
            and item.get("currencyCodeB") == UAH_CODE
        ]
        if not matches:
            raise ValueError("Monobank missing " + code + "/UAH")
        entry = matches[0]
        stamp = entry.get("date")
        if not isinstance(stamp, int) or isinstance(stamp, bool) or stamp <= 0:
            raise ValueError("Monobank timestamp invalid: " + code)
        if valid_rate(entry.get("rateSell")):
            rate, kind = entry["rateSell"], "sell"
        elif valid_rate(entry.get("rateCross")):
            rate, kind = entry["rateCross"], "cross"
        else:
            raise ValueError("Monobank quote unavailable: " + code)
        selection[code] = {"uah": round(float(rate), 4),
                           "timestamp": stamp, "kind": kind}
    return {
        "source": "Monobank", "source_url": SOURCE_URL,
        "updated": time.time() if updated is None else updated,
        "rates": selection,
    }


def valid_snapshot(data, now):
    if not isinstance(data, dict) or data.get("source") != "Monobank":
        return False
    if not isinstance(data.get("rates"), dict):
        return False
    for code in CURRENCY_CODES:
        item = data["rates"].get(code)
        if not isinstance(item, dict) or not valid_rate(item.get("uah")):
            return False
        stamp = item.get("timestamp")
        if not isinstance(stamp, int) or isinstance(stamp, bool):
            return False
        age = now - stamp
        if not -MAX_FUTURE_SECONDS <= age <= MAX_RATE_AGE_SECONDS:
            return False
        if item.get("kind") not in ("sell", "cross"):
            return False
    return True


def fetch_monobank_rates():
    request = urllib.request.Request(
        MONOBANK_URL,
        headers={"User-Agent": "PulseNews/1.0 (public Monobank rates)",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("Unexpectedly large Monobank response")
    return normalize_rates(json.loads(raw.decode("utf-8")))


def build_rates(destination, now=None):
    now = time.time() if now is None else now
    dest = Path(destination)
    prior = None
    if dest.exists():
        try:
            prior = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    try:
        result = fetch_monobank_rates()
        if not valid_snapshot(result, now):
            raise ValueError("Monobank rates outdated or inconsistent")
        result["status"] = "ok"
    except (OSError, ValueError) as error:
        print("Monobank rate fetch unavailable:", type(error).__name__)
        if valid_snapshot(prior, now):
            result = dict(prior, status="cached")
        else:
            result = {"source": "Monobank", "status": "unavailable",
                      "rates": {}, "source_url": SOURCE_URL}
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    temp.replace(dest)
    print("Monobank rates:", result["status"])
    return result

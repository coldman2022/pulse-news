"""Publish official NBU exchange rates in UAH. Missing data is never guessed."""
import datetime as dt
import json
import math
import time
import urllib.request
from pathlib import Path

NBU_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
MAX_JSON_BYTES = 500_000
STALE_DAYS = 7

def normalize_rates(rows, updated=None):
    """Return PLN and USD official 1-unit UAH quotes with the rate's own date."""
    if not isinstance(rows, list):
        raise ValueError("NBU rates must be a JSON array")
    selection = {}
    for code in ("PLN", "USD"):
        matches = [item for item in rows if isinstance(item, dict) and item.get("cc") == code]
        if not matches:
            raise ValueError("NBU missing " + code)
        entry = matches[0]
        rate = entry.get("rate")
        date = entry.get("exchangedate")
        if not isinstance(rate, (int, float)) or not math.isfinite(rate) or not 0 < rate < 10000:
            raise ValueError("NBU rate invalid: " + code)
        if not isinstance(date, str):
            raise ValueError("NBU date missing: " + code)
        try:
            parsed = dt.datetime.strptime(date, "%d.%m.%Y").date()
        except ValueError as exc:
            raise ValueError("NBU date invalid") from exc
        selection[code] = {"uah": round(float(rate), 4), "date": parsed.isoformat()}
    return {"source": "НБУ", "source_url": "https://bank.gov.ua/ua/markets/exchangerates",
            "updated": time.time() if updated is None else updated, "rates": selection}


def valid_snapshot(data, now):
    if not isinstance(data, dict) or data.get("source") != "НБУ":
        return False
    if not isinstance(data.get("rates"), dict):
        return False
    for code in ("PLN", "USD"):
        value = data["rates"].get(code, {})
        try:
            rate = value["uah"]
            date = dt.date.fromisoformat(value["date"])
            if not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0:
                return False
            if not (0 <= (dt.datetime.fromtimestamp(now, dt.timezone.utc).date() - date).days <= STALE_DAYS):
                return False
        except (ValueError, KeyError, TypeError):
            return False
    return True


def fetch_official_rates():
    request = urllib.request.Request(
        NBU_URL, headers={"User-Agent": "PulseNews/1.0 (official rates preview)",
                          "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("Unexpectedly large NBU response")
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
        result = fetch_official_rates()
        if not valid_snapshot(result, now):
            raise ValueError("NBU rates outdated or inconsistent")
        result["status"] = "ok"
    except (OSError, ValueError) as error:
        print("NBU rate fetch unavailable:", type(error).__name__)
        if valid_snapshot(prior, now):
            result = dict(prior, status="cached")
        else:
            result = {"source": "НБУ", "status": "unavailable", "rates": {},
                      "source_url": "https://bank.gov.ua/ua/markets/exchangerates"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    temp.replace(dest)
    print("NBU rates:", result["status"])
    return result

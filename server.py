#!/usr/bin/env python3
"""Pulse local RSS reader. Python 3.10+, standard library only."""
import argparse, concurrent.futures, datetime, email.utils, hashlib, html, json, re, threading, time
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT = Path(__file__).resolve().parent
LOCK = threading.Lock()
CACHE = {}

def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', '', value or ''))).strip()

def safe_url(value):
    return value if urllib.parse.urlsplit(value or '').scheme in ('http', 'https') else ''

# A conservative publisher allow-list for results discovered via Google News.
# Being listed here means a known publishing domain, NOT proof an article is true.
DISCOVERY_DOMAINS = (
    'canada.ca', 'gov.uk', 'gov.pl', 'europa.eu', 'gov.au', 'govt.nz',
    'homeaffairs.gov.au', 'immigration.govt.nz', 'uscis.gov', 'gov.pt',
    'reuters.com', 'apnews.com', 'bbc.com', 'bbc.co.uk', 'dw.com',
    'theguardian.com', 'euronews.com', 'ft.com', 'bloomberg.com',
    'cbc.ca', 'ctvnews.ca', 'globalnews.ca', 'cnn.com', 'nytimes.com',
    'washingtonpost.com', 'politico.eu', 'politico.com', 'nbcnews.com',
    'pap.pl', 'rmf24.pl', 'tvn24.pl', 'notesfrompoland.com',
    'pravda.com.ua', 'ukrinform.ua', 'rbc.ua', 'itc.ua',
    'theverge.com', 'techcrunch.com', 'arstechnica.com', 'wired.com',
    'technologyreview.com', 'forbes.com', 'nature.com', 'science.org',
    'openai.com', 'anthropic.com', 'mistral.ai', 'deepmind.google',
    'google.com', 'huggingface.co', 'nvidia.com', 'microsoft.com',
    'github.com', 'linuxfoundation.org', 'iclr.cc', 'neurips.cc',
    'icml.cc', 'acm.org', 'ieee.org',
)


def recognized_publisher(url):
    host = urllib.parse.urlsplit(url or '').hostname or ''
    host = host.lower().rstrip('.')
    return any(host == d or host.endswith('.' + d) for d in DISCOVERY_DOMAINS)


def parse_feed(raw, source):
    root = ET.fromstring(raw)
    atom = '{http://www.w3.org/2005/Atom}'
    entries = root.findall('.//item') or root.findall(atom + 'entry')
    result = []
    for item in entries[:50]:
        def value(*names):
            for name in names:
                found = item.find(name)
                if found is not None:
                    return ''.join(found.itertext())
            return ''
        url = safe_url(value('link'))
        if not url:
            for link in item.findall(atom + 'link'):
                if link.get('rel', 'alternate') == 'alternate':
                    url = safe_url(link.get('href', ''))
                    break
        title = clean(value('title', atom + 'title'))
        if not title or not url:
            continue
        summary = clean(value('description', atom + 'summary', atom + 'content'))[:600]
        required = source.get('require_terms', ())
        if required and not any(term.lower() in (title + ' ' + summary).lower() for term in required):
            continue
        publisher = source['name']
        if source.get('origin') == 'discovery':
            provider = item.find('source')
            provider_url = provider.get('url', '') if provider is not None else ''
            # Google News is a discovery index. Only display results
            # attributed to a known publishing domain.
            if not recognized_publisher(provider_url):
                continue
            publisher = clean(provider.text) or urllib.parse.urlsplit(provider_url).hostname
        date = value('pubDate', atom + 'published', atom + 'updated')
        try:
            stamp = email.utils.parsedate_to_datetime(date).timestamp()
        except (ValueError, TypeError, OverflowError):
            try:
                stamp = datetime.datetime.fromisoformat(date.replace('Z', '+00:00')).timestamp()
            except (ValueError, TypeError):
                stamp = 0
        result.append(dict(id=hashlib.sha256(url.encode()).hexdigest()[:20], title=title, url=url,
                           summary=summary, publisher=publisher, origin=source.get('origin', 'media'),
                           country=source.get('country', ''), source=source['name'],
                           category=source['category'], language=source.get('language', 'en'), published=stamp))
    return result

def fetch_source(source):
    req = urllib.request.Request(source['url'], headers={'User-Agent': 'PulseRSS/1.0 (personal local reader)'})
    with urllib.request.urlopen(req, timeout=12) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('Feed too large')
    articles = parse_feed(raw, source)
    if not articles:
        raise ValueError('No readable articles')
    return articles

def news():
    sources = json.loads((ROOT / 'sources.json').read_text())
    with LOCK:
        if CACHE.get('time', 0) + 300 > time.time():
            return CACHE['payload']
        previous = CACHE.get('by_source', {})
        by_source, statuses = {}, []
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(fetch_source, s): s for s in sources}
            for future in concurrent.futures.as_completed(futures):
                s = futures[future]
                try:
                    by_source[s['name']] = future.result()
                    statuses.append(dict(name=s['name'], ok=True, cached=False))
                except Exception:
                    by_source[s['name']] = previous.get(s['name'], [])
                    statuses.append(dict(name=s['name'], ok=False, cached=bool(by_source[s['name']])))
        unique = {}
        for articles in by_source.values():
            for article in articles:
                unique.setdefault(article['url'], article)
        payload = dict(articles=sorted(unique.values(), key=lambda a: a['published'], reverse=True),
                       sources=sorted(statuses, key=lambda s: s['name']), updated=time.time())
        CACHE.update(time=time.time(), payload=payload, by_source=by_source)
        return payload

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlsplit(self.path).path
        if route in ('/opportunities.json', '/api/opportunities'):
            try:
                from opportunities import make_opportunities
                payload = news()
                data = json.dumps({'updated': payload['updated'],
                                   'cards': make_opportunities(payload['articles'])}, ensure_ascii=False).encode()
                self.send_response(200)
            except Exception:
                data = b'{"error":"Cannot prepare opportunities"}'
                self.send_response(500)
            mime = 'application/json; charset=utf-8'
        elif route in ('/api/news', '/news.json'):
            try:
                data = json.dumps(news(), ensure_ascii=False).encode()
                self.send_response(200)
            except Exception:
                data = b'{"error":"Cannot read sources.json"}'
                self.send_response(500)
            mime = 'application/json; charset=utf-8'
        elif route in ('/', '/app.js', '/style.css', '/opportunities.html', '/opportunities.js'):
            name = 'index.html' if route == '/' else route[1:]
            data = (ROOT / 'static' / name).read_bytes()
            self.send_response(200)
            mime = {'index.html':'text/html', 'app.js':'text/javascript', 'style.css':'text/css', 'opportunities.html':'text/html', 'opportunities.js':'text/javascript'}[name] + '; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    print(f'Pulse: http://127.0.0.1:{args.port}  |  Stop: Ctrl+C', flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as error:
        parser.exit(1, f'Cannot start: {error}. Try --port 8766\n')


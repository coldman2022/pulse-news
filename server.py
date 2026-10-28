#!/usr/bin/env python3
"""Pulse local RSS reader. Python 3.10+, standard library only."""
import argparse, concurrent.futures, datetime, email.utils, hashlib, html, json, re, threading, time
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from html.parser import HTMLParser

# RSS images are hyperlinks only. GitHub Actions never downloads image bytes.
MEDIA_NS = '{http://search.yahoo.com/mrss/}'
CONTENT_NS = '{http://purl.org/rss/1.0/modules/content/}'


def safe_image_url(url):
    """Allow external HTTPS images, not embedded data or local addresses."""
    if not isinstance(url, str) or len(url) > 1800:
        return ''
    try:
        parts = urllib.parse.urlsplit(url.strip())
        host = (parts.hostname or '').lower()
        if parts.scheme != 'https' or not host or parts.username or parts.password:
            return ''
        if host in ('localhost', '127.0.0.1', '0.0.0.0', '::1') or host.endswith(('.local', '.internal')):
            return ''
        if any(parts.path.lower().endswith(ext) for ext in ('.svg', '.pdf', '.mp4', '.webm', '.gif')):
            return ''
        return url.strip()
    except ValueError:
        return ''


class _FirstHtmlImage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.image = ''

    def handle_starttag(self, tag, attrs):
        if tag != 'img' or self.image:
            return
        meta = dict(attrs)
        # Avoid typical 1x1 tracking pixels.
        if any(str(meta.get(k, '')).strip() in ('0', '1') for k in ('width', 'height')):
            return
        self.image = safe_image_url(meta.get('src', ''))


def feed_image(item):
    """Choose a publisher-provided thumbnail, with optional RSS copyright."""
    image = ''
    credit = ''
    for node in item.iter():
        if node.tag == MEDIA_NS + 'thumbnail':
            image = safe_image_url(node.get('url', ''))
            if image:
                break
    if not image:
        for node in item.iter():
            if node.tag == MEDIA_NS + 'content':
                medium = (node.get('medium') or '').lower()
                media_type = (node.get('type') or '').lower()
                if medium == 'image' or media_type.startswith('image/'):
                    image = safe_image_url(node.get('url', ''))
                    if image:
                        break
    if not image:
        for node in item.findall('enclosure'):
            if (node.get('type') or '').lower().startswith('image/'):
                image = safe_image_url(node.get('url', ''))
                if image:
                    break
    if not image:
        for key in ('description', CONTENT_NS + 'encoded', '{http://www.w3.org/2005/Atom}content'):
            element = item.find(key)
            if element is None:
                continue
            raw = ''.join(element.itertext())
            if '<img' not in raw.lower():
                continue
            parser = _FirstHtmlImage()
            parser.feed(raw)
            if parser.image:
                image = parser.image
                break
    if image:
        for node in item.iter():
            if node.tag == MEDIA_NS + 'copyright':
                credit = clean(''.join(node.itertext()))[:120]
                break
    return image, credit

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
    'cnbc.com', 'npr.org', 'france24.com', 'skynews.com',
    'cbc.ca', 'ctvnews.ca', 'globalnews.ca', 'cnn.com', 'nytimes.com',
    'washingtonpost.com', 'politico.eu', 'politico.com', 'nbcnews.com',
    'pap.pl', 'rmf24.pl', 'tvn24.pl', 'notesfrompoland.com',
    'pravda.com.ua', 'ukrinform.ua', 'rbc.ua', 'itc.ua',
    'theverge.com', 'techcrunch.com', 'arstechnica.com', 'wired.com',
    'technologyreview.com', 'forbes.com', 'nature.com', 'science.org',
    'openai.com', 'anthropic.com', 'mistral.ai', 'deepmind.google',
    'google.com', 'huggingface.co', 'nvidia.com', 'microsoft.com',
    'linuxfoundation.org', 'iclr.cc', 'neurips.cc',
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
        image_url, image_credit = feed_image(item)
        result.append(dict(id=hashlib.sha256(url.encode()).hexdigest()[:20], title=title, url=url,
                           summary=summary, image_url=image_url, image_credit=image_credit,
                           publisher=publisher, origin=source.get('origin', 'media'),
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
        if route in ('/digest.json', '/api/digest'):
            try:
                import daily_digest
                payload = news()
                data = json.dumps(daily_digest.build_digest(payload['articles'], payload['updated']),
                                  ensure_ascii=False).encode()
                self.send_response(200)
            except Exception:
                data = b'{"error":"Cannot prepare daily briefing"}'
                self.send_response(500)
            mime = 'application/json; charset=utf-8'
        elif route in ('/opportunities.json', '/api/opportunities'):
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
        elif route in ('/personal.json', '/api/personal'):
            try:
                from personal_feed import build_personal_feed
                payload = news()
                curated = build_personal_feed(payload['articles'], payload['updated'])
                curated['sources'] = payload['sources']
                data = json.dumps(curated, ensure_ascii=False).encode()
                self.send_response(200)
            except Exception:
                data = b'{"error":"Cannot prepare personal feed"}'
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
        elif route in ('/', '/app.js', '/style.css', '/opportunities.html', '/opportunities.js', '/digest.html', '/digest.js', '/events.js', '/events.json'):
            name = 'index.html' if route == '/' else route[1:]
            data = (ROOT / 'static' / name).read_bytes()
            self.send_response(200)
            mime = {'index.html':'text/html', 'app.js':'text/javascript', 'style.css':'text/css', 'opportunities.html':'text/html', 'opportunities.js':'text/javascript', 'digest.html':'text/html', 'digest.js':'text/javascript', 'events.js':'text/javascript', 'events.json':'application/json'}[name] + '; charset=utf-8'
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


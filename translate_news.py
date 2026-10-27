"""Optional offline English -> Ukrainian RSS translation with a persistent cache."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.argos'
MODEL_VERSION = '1.4'
CACHE_VERSION = 'argos-1.11-en-uk-1.4-spacy-v1'
MODEL_URL = 'https://argos-net.com/v1/translate-en_uk-1_4.argosmodel'
MODEL_SHA256 = '037ebc690c0f7287bff01b09006f76707d7089134205a91ef3d823a3c73811e3'


def configure():
    # Keep every model/config file inside this checkout, including on developers' computers.
    for name, value in {
        'XDG_DATA_HOME': STATE / 'data',
        'XDG_CONFIG_HOME': STATE / 'config',
        'XDG_CACHE_HOME': STATE / 'cache',
        'ARGOS_PACKAGES_DIR': STATE / 'packages',
        'ARGOS_CHUNK_TYPE': 'STANZA',
        'ARGOS_DEVICE_TYPE': 'cpu',
        'ARGOS_INTRA_THREADS': '2',
    }.items():
        os.environ[name] = str(value)


def get_translator():
    configure()
    import argostranslate.package
    import argostranslate.translate
    model = next((p for p in argostranslate.package.get_installed_packages()
                  if p.from_code == 'en' and p.to_code == 'uk' and
                  str(p.package_version) == MODEL_VERSION), None)
    if model is None:
        raise RuntimeError('Install the English/Ukrainian model: python translate_news.py --install')
    # The old en/uk package includes a Stanza model whose default loader requests
    # new resources online. Use spaCy's bundled English rules instead: no downloads.
    import spacy
    nlp = spacy.blank('en')
    nlp.add_pipe('sentencizer')

    class EnglishSentences:
        def split_sentences(self, text):
            return [sentence.text for sentence in nlp(text).sents]

    translation = argostranslate.translate.PackageTranslation(
        argostranslate.translate.Language('en', 'English'),
        argostranslate.translate.Language('uk', 'Ukrainian'), model)
    translation.sentencizer = EnglishSentences()
    return translation.translate


def install_model():
    configure()
    import argostranslate.package
    if any(p.from_code == 'en' and p.to_code == 'uk' and
           str(p.package_version) == MODEL_VERSION
           for p in argostranslate.package.get_installed_packages()):
        return
    STATE.mkdir(parents=True, exist_ok=True)
    archive = STATE / 'en-uk.argosmodel'
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=120) as response:
            with archive.open('wb') as target:
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != MODEL_SHA256:
            raise RuntimeError('The downloaded Argos model failed its SHA-256 check')
        argostranslate.package.install_from_path(archive)
    finally:
        archive.unlink(missing_ok=True)


def translate_payload(payload, cache_path, translator=None, max_seconds=360):
    """Add optional *_uk fields; never overwrite originals or cache failures."""
    path = Path(cache_path)
    try:
        cache = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(cache, dict):
            cache = {}
    except (OSError, ValueError):
        cache = {}
    started = time.monotonic()
    translated = cached = failed = 0
    engine_unavailable = False
    for article in payload['articles']:
        for field in ('title', 'summary'):
            article.pop(field + '_uk', None)
            text = article.get(field, '')
            if not text:
                continue
            key = hashlib.sha256((CACHE_VERSION + '\0' + text).encode()).hexdigest()
            entry = cache.get(key)
            if isinstance(entry, dict) and isinstance(entry.get('text'), str) and entry['text']:
                article[field + '_uk'] = entry['text']
                entry['used'] = time.time()
                cached += 1
                continue
            if engine_unavailable or time.monotonic() - started >= max_seconds:
                failed += 1
                continue
            try:
                if translator is None:
                    try:
                        translator = get_translator()
                    except Exception:
                        engine_unavailable = True
                        raise
                result = translator(text).strip()
                # Don't label an unchanged English string or a broken response as Ukrainian.
                if not result or result == text or not re.search('[А-Яа-яІіЇїЄєҐґ]', result):
                    failed += 1
                    continue
                article[field + '_uk'] = result
                cache[key] = dict(text=result, used=time.time())
                translated += 1
            except Exception as error:
                print(f'Translation unavailable ({type(error).__name__}); keeping original {field}.')
                failed += 1
    # Bound the cache; it is an optimization, not the only copy of the original news.
    cache = {k: v for k, v in cache.items()
             if isinstance(v, dict) and isinstance(v.get('used'), (int, float))}
    cache = dict(sorted(cache.items(), key=lambda item: item[1]['used'], reverse=True)[:5000])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)
    payload['translation'] = dict(engine='Argos Translate', language='uk',
                                  translated=translated, cached=cached, untranslated=failed)
    print(f'Translation: {translated} new, {cached} cached, {failed} original fields; '
          f'{time.monotonic() - started:.1f}s')
    return payload


def smoke_test():
    translator = get_translator()
    result = translator('Scientists discover a new species of butterfly.')
    if not re.search('[А-Яа-яІіЇїЄєҐґ]', result):
        raise RuntimeError('Argos did not return Ukrainian text')
    print('Argos smoke test:', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--smoke-test', action='store_true')
    args = parser.parse_args()
    if args.install:
        install_model()
    if args.smoke_test:
        smoke_test()

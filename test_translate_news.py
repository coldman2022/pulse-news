import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import build_site
import server
import translate_news


class TranslationTests(unittest.TestCase):
    def payload(self):
        return {'articles': [dict(title='A new discovery', summary='Scientists report a discovery.',
                                  source='BBC World', id='1', url='https://example.org/1',
                                  category='Світ', published=1)]}

    def test_cache_survives_new_process_and_originals_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'translations.json'
            translator = Mock(side_effect=['Нове відкриття', 'Науковці повідомляють про відкриття.'])
            first = self.payload()
            translate_news.translate_payload(first, path, translator)
            self.assertEqual(first['articles'][0]['title'], 'A new discovery')
            self.assertEqual(first['articles'][0]['title_uk'], 'Нове відкриття')
            self.assertEqual(translator.call_count, 2)
            second = self.payload()
            translator.reset_mock()
            translate_news.translate_payload(second, path, translator)
            translator.assert_not_called()
            self.assertEqual(second['articles'], first['articles'])
            self.assertEqual(second['translation']['cached'], 2)
            # A changed description must be translated again, even for the same article URL.
            second['articles'][0]['summary'] = 'Updated report'
            translator.side_effect = None
            translator.return_value = 'Оновлений звіт'
            translate_news.translate_payload(second, path, translator)
            translator.assert_called_once_with('Updated report')

    def test_failure_is_not_cached_and_can_be_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'translations.json'
            payload = self.payload()
            translate_news.translate_payload(payload, path, Mock(side_effect=RuntimeError('offline')))
            self.assertNotIn('title_uk', payload['articles'][0])
            self.assertEqual(json.loads(path.read_text()), {})
            translate_news.translate_payload(payload, path, lambda text: 'Український переклад')
            self.assertIn('title_uk', payload['articles'][0])

    def test_missing_engine_keeps_cached_translations_and_uncached_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'translations.json'
            translate_news.translate_payload(self.payload(), path, lambda text: 'Переклад')
            payload = self.payload()
            payload['articles'].append(dict(title='New headline', summary=''))
            with patch.object(translate_news, 'get_translator', side_effect=ImportError('Argos absent')):
                translate_news.translate_payload(payload, path)
            self.assertEqual(payload['articles'][0]['title_uk'], 'Переклад')
            self.assertNotIn('title_uk', payload['articles'][1])

    def test_budget_and_invalid_cache_fall_back_to_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'translations.json'
            path.write_text('broken json')
            translator = Mock()
            payload = self.payload()
            translate_news.translate_payload(payload, path, translator, max_seconds=0)
            translator.assert_not_called()
            self.assertEqual(payload['translation']['untranslated'], 2)

    def test_empty_or_unchanged_output_is_not_labeled_as_translation(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = self.payload()
            translate_news.translate_payload(payload, Path(folder) / 'cache.json', lambda text: text)
            self.assertNotIn('title_uk', payload['articles'][0])
            self.assertNotIn('summary_uk', payload['articles'][0])

    def test_translation_is_included_in_built_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'site'
            payload = self.payload()
            payload.update(sources=[dict(name='BBC World', ok=True, cached=False)], updated=1)
            original = translate_news.translate_payload
            with patch.object(server, 'news', return_value=payload):
                with patch.object(translate_news, 'translate_payload',
                                  side_effect=lambda data, path: original(data, path, lambda text: 'Тестовий переклад')):
                    build_site.build(output, translate=True, translation_cache=Path(folder) / 'cache.json')
            data = json.loads((output / 'news.json').read_text())
            self.assertEqual(data['articles'][0]['title_uk'], 'Тестовий переклад')
            self.assertEqual(data['articles'][0]['title'], 'A new discovery')

    def tearDown(self):
        server.CACHE.clear()

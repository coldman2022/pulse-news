"""Offline translation tests run without models, network access or email secrets."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import translate_batch as batch

NOW=1800000000


def article(number, lang="en", stamp=NOW, category="AI", summary="Publisher provided description"):
    return {
        "id": f"{number:020x}",
        "title": f"Technology company announces new model {number}",
        "summary": summary,
        "published": stamp,
        "language": lang,
        "category": category,
        "url": f"https://example.com/a/{number}",
    }


class BatchTranslationTests(unittest.TestCase):
    def test_200_new_articles_budget_and_reuse(self):
        rows = [article(i) for i in range(235)]
        rows.sort(key=lambda x: -int(x["id"], 16))
        feed = {"articles": rows}
        old = batch.empty_cache()
        selected = batch.candidates(feed, old, NOW)
        self.assertEqual(len(selected), 200)
        self.assertEqual(selected[0]["id"], rows[0]["id"])

        translator=Mock()
        translator.translate_many.side_effect=lambda texts, lang: ["Український переклад "+str(t) for t in texts]
        result=batch.process(feed,old,NOW,translator)
        self.assertEqual(result["meta"]["new_translations"],200)
        self.assertEqual(len(result["articles"]),200)
        self.assertEqual(result["articles"][rows[0]["id"]]["language"],"en")
        self.assertEqual(result["articles"][rows[0]["id"]]["summary"],
                         "Український переклад Publisher provided description")
        self.assertEqual(len(batch.candidates(feed,result,NOW)),35)

        second=batch.process(feed,result,NOW,translator)
        self.assertEqual(second["meta"]["new_translations"],35)
        self.assertEqual(len(second["articles"]),235)
        final=batch.process(feed,second,NOW,translator)
        self.assertEqual(final["meta"]["new_translations"],0)

    def test_polish_and_non_english_and_ukrainian(self):
        rows=[article(1,"pl"),article(2,"uk"),article(3,"fr"),article(4,"en")]
        selected=batch.candidates({"articles":rows},batch.empty_cache(),NOW)
        self.assertEqual({x["language"] for x in selected},{"pl","en"})
        selected_email=batch.candidates(
            {"articles":rows},batch.empty_cache(),NOW,contact_email="contact@example.org")
        self.assertEqual({x["language"] for x in selected_email},{"pl","en","fr"})

    def test_protect_against_original_content_changes(self):
        row=article(10)
        saved=batch.empty_cache()
        saved["articles"][row["id"]]={
            "source_title":row["title"],"source_summary":row["summary"],
            "language":"en","title":"Переклад","summary":"Опис","translated_at":NOW,
        }
        self.assertFalse(batch.candidates({"articles":[row]},saved,NOW))
        row["summary"]="Changed source summary"
        self.assertEqual(len(batch.candidates({"articles":[row]},saved,NOW)),1)

    def test_batch_safe_after_model_failure(self):
        current=batch.empty_cache()
        old=article(1)
        current["articles"][old["id"]]={
            "source_title":old["title"],"source_summary":old["summary"],
            "language":"en","title":"Збережений переклад",
            "summary":"Збережений опис","translated_at":NOW,
        }
        broken=Mock()
        broken.translate_many.side_effect=RuntimeError("model failed")
        result=batch.process({"articles":[old,article(2,"pl")]},current,NOW,broken)
        self.assertEqual(result["articles"][old["id"]]["title"],"Збережений переклад")
        self.assertEqual(result["meta"]["new_translations"],0)

    def test_old_and_invalid_rows_never_translate(self):
        too_old=article(1,stamp=NOW-15*86400)
        future=article(2,stamp=NOW+2*3600)
        invalid=article(3)
        invalid["id"]="not-a-hex-id"
        self.assertFalse(batch.candidates(
            {"articles":[too_old,future,invalid,article(4,"uk")]},
            batch.empty_cache(),NOW))

    def test_prune_and_cache_file(self):
        cache=batch.empty_cache()
        cache["articles"]={
            article(1)["id"]:{"translated_at":NOW-125*86400},
            article(2)["id"]:{"translated_at":NOW},
        }
        result=batch.prune(cache,NOW)
        self.assertEqual(list(result["articles"]),[article(2)["id"]])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"translations.json"
            path.write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")
            self.assertEqual(batch.load_cache(path)["schema"],1)

    def test_unicode_request_chunks_within_mymemory_limit(self):
        pieces=batch.MyMemoryFallback._parts("Довгий заголовок " * 110)
        self.assertTrue(pieces)
        self.assertTrue(all(len(p.encode("utf-8"))<=440 for p in pieces))

    def test_local_model_names_are_pinned_to_supported_languages(self):
        self.assertEqual(batch.SUPPORTED_OFFLINE["en"],"Helsinki-NLP/opus-mt-en-uk")
        self.assertEqual(batch.SUPPORTED_OFFLINE["pl"],"Helsinki-NLP/opus-mt-pl-uk")
        self.assertEqual(batch.DAILY_LIMIT,200)

    def test_wiring_without_leaking_email(self):
        root=Path(__file__).resolve().parent
        workflow=(root/".github/workflows/translate.yml").read_text(encoding="utf-8")
        script=(root/"translate_batch.py").read_text(encoding="utf-8")
        build=(root/"build_site.py").read_text(encoding="utf-8")
        app=(root/"static/app.js").read_text(encoding="utf-8")
        for token in ("workflow_dispatch:", "schedule:", "cache@v4",
                      "MYMEMORY_CONTACT_EMAIL:", "python translate_batch.py",
                      "git push origin HEAD:main"):
            self.assertIn(token,workflow)
        self.assertIn('"de": self.email',script)
        self.assertIn("'translations.json'",build)
        self.assertIn("loadSharedTranslations()",app)
        self.assertIn("sharedTranslation(a)",app)
        self.assertIn("translations.json",app)
        self.assertNotIn("MYMEMORY_CONTACT_EMAIL",app)


if __name__=="__main__":
    unittest.main()

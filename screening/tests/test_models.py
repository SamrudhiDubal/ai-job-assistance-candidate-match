"""Tests for the trained ML/DL models, semantic similarity and the optional Claude layer."""
import importlib.util
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
from django.test import SimpleTestCase

from screening import llm, matcher, semantic
from screening.ml import classifier, dataset, train

RESUMES = Path(__file__).resolve().parents[2] / "sample_data" / "resumes"
HAS_TF = importlib.util.find_spec("tensorflow") is not None


class DatasetTests(SimpleTestCase):
    def test_synthetic_corpus_is_balanced_and_reproducible(self):
        a = dataset.synthetic_corpus(per_role=10, seed=1)
        b = dataset.synthetic_corpus(per_role=10, seed=1)
        self.assertEqual(len(a), 10 * len(dataset.ROLE_PROFILES))
        self.assertTrue((a.Category.value_counts() == 10).all())
        self.assertTrue(a.equals(b))


class SavedModelTests(SimpleTestCase):
    def test_metrics_saved_with_realistic_scores(self):
        metrics = json.loads(train.METRICS_PATH.read_text())
        best = metrics["ml"][metrics["best_ml_model"]]
        self.assertGreater(best["accuracy"], 0.75)
        self.assertLess(best["accuracy"], 1.0)  # the corpus is deliberately noisy
        self.assertEqual(len(metrics["labels"]), len(dataset.ROLE_PROFILES))

    def test_ml_classifier_predicts_categories(self):
        p = classifier.predict_ml((RESUMES / "rahul_verma.txt").read_text())
        self.assertEqual(p["category"], "Backend Developer")
        self.assertTrue(0 < p["confidence"] <= 100)

    @unittest.skipUnless(HAS_TF, "TensorFlow not installed")
    def test_dl_classifier_predicts_categories(self):
        p = classifier.predict_dl((RESUMES / "sneha_iyer.txt").read_text())
        self.assertIsNotNone(p, "TensorFlow is installed but the saved BiLSTM could not be loaded or run")
        self.assertEqual(p["category"], "UI/UX Designer")


class SemanticTests(SimpleTestCase):
    def test_scale_clips_to_percent(self):
        self.assertEqual(semantic.to_percent(0.10, "sbert"), 0)
        self.assertEqual(semantic.to_percent(0.80, "sbert"), 100)
        self.assertAlmostEqual(semantic.to_percent(0.425, "sbert"), 50.0)

    def test_sentence_bert_backend_used_when_available(self):
        class FakeSBERT:
            def encode(self, texts, normalize_embeddings=True, batch_size=32):
                return np.array([[1.0, 0.0], [0.6, 0.8]])

        with mock.patch.object(semantic, "_sbert", return_value=FakeSBERT()):
            pct, info = semantic.similarity("resume", "job")
        self.assertEqual(info["backend"], "Sentence-BERT")
        self.assertAlmostEqual(info["raw"], 0.6)
        self.assertAlmostEqual(pct, 81.8)

    @unittest.skipUnless(HAS_TF, "TensorFlow not installed")
    def test_falls_back_to_bilstm(self):
        with mock.patch.object(semantic, "_sbert", return_value=None):
            pct, info = semantic.similarity((RESUMES / "arjun_sharma.txt").read_text(),
                                            "Full stack developer React Node.js Express MongoDB")
        self.assertIsNotNone(info, "TensorFlow is installed but the BiLSTM fallback returned nothing")
        self.assertEqual(info["backend"], "BiLSTM role profile")
        self.assertTrue(0 <= pct <= 100)

    def test_no_backend_means_signal_skipped(self):
        with mock.patch.dict(os.environ, {"JOBMATCH_SEMANTIC_BACKEND": "off"}):
            self.assertEqual(semantic.similarity("a", "b"), (None, None))


class LLMTests(SimpleTestCase):
    JOB = SimpleNamespace(title="Python Developer", description="Build APIs with Django",
                          skill_list=["python", "django"], experience_level="entry")

    def test_disabled_without_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(llm.enabled())
            self.assertIsNone(llm.rate("resume", "job"))

    def _fake_response(self, text, stop_reason="end_turn"):
        return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])

    def test_llm_score_blended_70_30(self):
        fake = mock.MagicMock()
        fake.return_value.beta.messages.create.return_value = self._fake_response(
            '{"score": 90, "summary": "Strong Django background."}')
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test", "JOBMATCH_SEMANTIC_BACKEND": "off"}), \
                mock.patch("anthropic.Anthropic", fake):
            r = matcher.screen("Python developer, 2 years of experience with Django REST APIs", self.JOB)
        self.assertEqual(r["semantic_score"], 90)
        self.assertEqual(r["semantic_summary"], "Strong Django background.")
        self.assertEqual(r["match_score"], int(0.7 * r["local_score"] + 0.3 * 90 + 0.5))

    def test_refusal_or_bad_reply_falls_back(self):
        fake = mock.MagicMock()
        for response in (self._fake_response("", "refusal"), self._fake_response("not json")):
            fake.return_value.beta.messages.create.return_value = response
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}), mock.patch("anthropic.Anthropic", fake):
                self.assertIsNone(llm.rate("resume", "job"))


class MatcherWithModelsTests(SimpleTestCase):
    def test_breakdown_includes_dl_signal_and_categories(self):
        job = SimpleNamespace(title="QA Automation Engineer", description="Automate tests with Selenium and Java",
                              skill_list=["selenium", "java", "jira"], experience_level="mid")
        r = matcher.screen((RESUMES / "rahul_verma.txt").read_text(), job)
        self.assertIn("semantic", r["weights_used"])
        self.assertIn("ml", r["predicted_categories"])

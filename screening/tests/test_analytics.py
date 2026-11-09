import importlib.util
from pathlib import Path

from django.test import SimpleTestCase

GEN = Path(__file__).resolve().parents[2] / "analytics" / "generate_dataset.py"


class RecruitmentDatasetTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        spec = importlib.util.spec_from_file_location("generate_dataset", GEN)
        cls.gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gen)
        cls.df = cls.gen.generate()

    def test_schema_matches_report(self):
        self.assertEqual(self.df.shape, (12_000, 26))
        self.assertEqual(int(self.df.isna().sum().sum()), 0)
        self.assertEqual(int(self.df.duplicated().sum()), 0)

    def test_class_counts_match_report(self):
        self.assertEqual(self.df.Target_Category.value_counts().to_dict(), self.gen.CLASS_COUNTS)

    def test_salaries_strongly_correlated(self):
        r = self.df.Current_Salary_CNY_K.corr(self.df.Expected_Salary_CNY_K)
        self.assertGreater(r, 0.95)

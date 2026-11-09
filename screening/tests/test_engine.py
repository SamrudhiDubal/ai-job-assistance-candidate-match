from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from screening import experience, matcher, skills
from screening.parsers import ResumeParseError, extract_text

RESUMES = Path(__file__).resolve().parents[2] / "sample_data" / "resumes"

MERN_JOB = SimpleNamespace(
    title="Full Stack Developer (MERN)",
    description="Build web applications using React, Node.js, Express and MongoDB. Design REST APIs "
                "and write clean JavaScript. Collaborate using Git.",
    skill_list=["javascript", "react", "node.js", "express", "mongodb", "rest api", "git"],
    experience_level="mid",
)


class SkillTests(SimpleTestCase):
    def test_aliases_resolve_to_canonical_form(self):
        self.assertEqual(skills.canonical("JS"), "javascript")
        self.assertEqual(skills.canonical("k8s"), "kubernetes")
        self.assertEqual(skills.canonical("REST API"), "rest")
        self.assertEqual(skills.canonical("React"), "react.js")

    def test_java_not_found_inside_javascript(self):
        found = skills.extract_skills("Expert in JavaScript and TypeScript")
        self.assertIn("javascript", found)
        self.assertNotIn("java", found)

    def test_symbols_in_skill_names(self):
        found = skills.extract_skills("Worked with C++, C#, Node.js and CI/CD pipelines")
        for s in ("c++", "c#", "node.js", "ci/cd"):
            self.assertIn(s, found)

    def test_alias_detected_in_text(self):
        self.assertTrue(skills.mentions("Deployed services on k8s", "kubernetes"))

    def test_ambiguous_short_alias_ignored(self):
        self.assertNotIn("computer vision", skills.extract_skills("Please find my CV attached"))


class ExperienceTests(SimpleTestCase):
    def test_years_patterns(self):
        self.assertEqual(experience.years_of_experience("6 years of experience in sales"), 6)
        self.assertEqual(experience.years_of_experience("experience of 3 years"), 3)
        self.assertEqual(experience.years_of_experience("4+ years in Python"), 4)
        self.assertEqual(experience.years_of_experience("2 yrs experience, later 5 years of experience"), 5)

    def test_no_years_returns_none(self):
        self.assertIsNone(experience.years_of_experience("Graduated in 2020 and enjoys design"))

    def test_experience_fit_by_level(self):
        self.assertEqual(experience.experience_fit(0, "entry"), 100)
        self.assertEqual(experience.experience_fit(1, "mid"), 50)
        self.assertEqual(experience.experience_fit(5, "senior"), 100)
        self.assertEqual(experience.experience_fit(4, "lead"), 50)
        self.assertIsNone(experience.experience_fit(None, "mid"))

    def test_education_level(self):
        self.assertEqual(experience.education_level("PhD in Physics, B.Tech"), "PhD")
        self.assertEqual(experience.education_level("MBA, B.Com"), "Master's")
        self.assertEqual(experience.education_level("B.Tech in Computer Engineering"), "Bachelor's")
        self.assertIsNone(experience.education_level("self taught"))


class MatcherTests(SimpleTestCase):
    def test_cosine_similarity_bounds(self):
        self.assertAlmostEqual(matcher.cosine_similarity("python django", "python django"), 1.0)
        self.assertEqual(matcher.cosine_similarity("python", "photoshop"), 0.0)
        self.assertEqual(matcher.cosine_similarity("", "python"), 0.0)

    def test_weights_redistributed_when_experience_unknown(self):
        score, weights = matcher.blend({"skill": 90, "text": 30, "experience": None})
        self.assertAlmostEqual(weights["skill"], 2 / 3)
        self.assertAlmostEqual(weights["text"], 1 / 3)
        self.assertEqual(score, 70)

    def test_full_blend(self):
        score, _ = matcher.blend({"skill": 100, "text": 34, "experience": 100})
        self.assertEqual(score, 84)  # 50 + 8.5 + 25 = 83.5, rounded half up

    def test_declared_skills_count(self):
        result = matcher.screen("I build websites", MERN_JOB, declared_skills=["JS", "React"])
        self.assertIn("javascript", result["matched_skills"])
        self.assertIn("react.js", result["matched_skills"])

    def test_sample_candidates_ranked_like_a_recruiter(self):
        names = ["arjun_sharma", "neha_kulkarni", "rahul_verma", "sneha_iyer"]
        scores = [matcher.screen((RESUMES / f"{n}.txt").read_text(), MERN_JOB)["match_score"] for n in names]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertGreaterEqual(scores[0], 75)
        self.assertLessEqual(scores[-1], 5)


class ParserTests(SimpleTestCase):
    def test_txt(self):
        with open(RESUMES / "arjun_sharma.txt", "rb") as f:
            self.assertIn("Arjun Sharma", extract_text(f, "arjun.txt"))

    def test_docx(self):
        import io

        import docx

        d = docx.Document()
        d.add_paragraph("Jane Doe - Python developer with 3 years of experience in Django")
        buf = io.BytesIO()
        d.save(buf)
        buf.seek(0)
        self.assertIn("Django", extract_text(buf, "jane.docx"))

    def test_rejects_unsupported_and_empty(self):
        import io

        with self.assertRaises(ResumeParseError):
            extract_text(io.BytesIO(b"x"), "resume.exe")
        with self.assertRaises(ResumeParseError):
            extract_text(io.BytesIO(b"hi"), "resume.txt")
        with self.assertRaises(ResumeParseError):
            extract_text(io.BytesIO(b"not really a pdf"), "resume.pdf")

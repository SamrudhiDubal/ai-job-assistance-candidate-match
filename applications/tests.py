import shutil
import tempfile
from pathlib import Path

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from jobs.models import Job

from .models import Application

RESUMES = Path(__file__).resolve().parents[1] / "sample_data" / "resumes"
TMP_MEDIA = tempfile.mkdtemp()


def resume(name):
    return SimpleUploadedFile(f"{name}.txt", (RESUMES / f"{name}.txt").read_bytes(), content_type="text/plain")


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PortalFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.employer = User.objects.create_user("hr@acme.com", "pass12345", name="Acme HR", role="employer", company="Acme")
        self.other_employer = User.objects.create_user("hr@other.com", "pass12345", name="Other HR", role="employer", company="Other")
        self.admin = User.objects.create_superuser("admin@jobmatch.local", "pass12345")
        self.job = Job.objects.create(
            title="Full Stack Developer (MERN)", company="Acme", employer=self.employer,
            description="Build React, Node.js, Express and MongoDB apps with REST APIs, JavaScript and Git.",
            skills_required="JavaScript, React, Node.js, Express, MongoDB, REST API, Git", experience_level="mid")
        self.candidates = {}
        for n in ["arjun_sharma", "neha_kulkarni", "rahul_verma", "sneha_iyer"]:
            self.candidates[n] = User.objects.create_user(f"{n}@example.com", "pass12345", name=n.replace("_", " ").title())

    def apply_as(self, name, upload=None):
        self.client.force_login(self.candidates[name])
        return self.client.post(reverse("applications:apply", args=[self.job.pk]),
                                {"resume": upload or resume(name), "cover_letter": "Hello"})

    # --- authentication and roles ---
    def test_register_candidate_and_employer(self):
        r = self.client.post(reverse("accounts:register"), {
            "name": "New Person", "email": "New@Example.com", "role": "candidate",
            "password1": "S3cure-pass!", "password2": "S3cure-pass!"})
        self.assertRedirects(r, reverse("jobs:list"))
        self.assertTrue(User.objects.filter(email="new@example.com", role="candidate").exists())
        self.client.logout()
        r = self.client.post(reverse("accounts:register"), {
            "name": "Boss", "email": "boss@corp.com", "role": "employer",
            "password1": "S3cure-pass!", "password2": "S3cure-pass!"})
        self.assertContains(r, "Please enter your company name")

    def test_cannot_register_as_admin(self):
        self.client.post(reverse("accounts:register"), {
            "name": "Hacker", "email": "h@x.com", "role": "admin",
            "password1": "S3cure-pass!", "password2": "S3cure-pass!"})
        self.assertFalse(User.objects.filter(email="h@x.com").exists())

    def test_login_with_email(self):
        r = self.client.post(reverse("accounts:login"), {"username": "hr@acme.com", "password": "pass12345"})
        self.assertEqual(r.status_code, 302)

    def test_deactivated_user_cannot_log_in(self):
        self.employer.is_active = False
        self.employer.save()
        r = self.client.post(reverse("accounts:login"), {"username": "hr@acme.com", "password": "pass12345"})
        self.assertEqual(r.status_code, 200)

    def test_role_restrictions(self):
        self.client.force_login(self.candidates["arjun_sharma"])
        self.assertEqual(self.client.get(reverse("jobs:create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("adminpanel:dashboard")).status_code, 403)
        self.client.force_login(self.employer)
        self.assertEqual(self.client.get(reverse("applications:mine")).status_code, 403)

    # --- jobs ---
    def test_employer_creates_job_and_skills_are_normalised(self):
        self.client.force_login(self.employer)
        r = self.client.post(reverse("jobs:create"), {
            "title": "Data Analyst", "company": "Acme", "location": "Pune", "job_type": "full-time",
            "experience_level": "entry", "skills_required": "SQL, Python , sql, Excel",
            "description": "Analyse data."})
        self.assertRedirects(r, reverse("jobs:mine"))
        self.assertEqual(Job.objects.get(title="Data Analyst").skills_required, "sql, python, excel")

    def test_only_owner_can_edit_or_delete(self):
        self.client.force_login(self.other_employer)
        self.assertEqual(self.client.get(reverse("jobs:edit", args=[self.job.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("jobs:delete", args=[self.job.pk])).status_code, 404)

    def test_search_and_filters(self):
        Job.objects.create(title="QA Engineer", company="Beta", employer=self.employer, location="Chennai",
                           description="Manual testing", skills_required="selenium", experience_level="entry")
        r = self.client.get(reverse("jobs:list"), {"q": "MERN"})
        self.assertContains(r, "Full Stack Developer")
        self.assertNotContains(r, "QA Engineer")
        r = self.client.get(reverse("jobs:list"), {"location": "chen"})
        self.assertContains(r, "QA Engineer")
        r = self.client.get(reverse("jobs:list"), {"skill": "Selenium"})
        self.assertNotContains(r, "Full Stack Developer")

    def test_closed_jobs_hidden_from_search(self):
        self.job.status = Job.Status.CLOSED
        self.job.save()
        self.assertNotContains(self.client.get(reverse("jobs:list")), "Full Stack Developer")

    # --- applying and AI screening ---
    def test_apply_scores_resume_and_sends_emails(self):
        r = self.apply_as("arjun_sharma")
        self.assertRedirects(r, reverse("applications:mine"))
        app = Application.objects.get()
        self.assertGreaterEqual(app.match_score, 75)
        self.assertEqual(app.match_details["missing_skills"], [])
        self.assertEqual(len(mail.outbox), 2)  # employer + candidate

    def test_duplicate_application_rejected(self):
        self.apply_as("arjun_sharma")
        self.apply_as("arjun_sharma")
        self.assertEqual(Application.objects.count(), 1)

    def test_bad_file_type_rejected(self):
        self.apply_as("arjun_sharma", SimpleUploadedFile("cv.exe", b"MZ" * 50))
        self.assertEqual(Application.objects.count(), 0)

    def test_cannot_apply_to_closed_job(self):
        self.job.status = Job.Status.CLOSED
        self.job.save()
        self.apply_as("arjun_sharma")
        self.assertEqual(Application.objects.count(), 0)

    def test_applicants_ranked_best_first(self):
        for n in ["sneha_iyer", "rahul_verma", "arjun_sharma", "neha_kulkarni"]:
            self.apply_as(n)
        self.client.force_login(self.employer)
        r = self.client.get(reverse("applications:job_applicants", args=[self.job.pk]))
        names = [a.candidate.name for a in r.context["applications"]]
        self.assertEqual(names, ["Arjun Sharma", "Neha Kulkarni", "Rahul Verma", "Sneha Iyer"])

    def test_other_employer_cannot_see_applicants(self):
        self.apply_as("arjun_sharma")
        self.client.force_login(self.other_employer)
        self.assertEqual(self.client.get(reverse("applications:job_applicants", args=[self.job.pk])).status_code, 404)

    def test_status_change_notifies_candidate(self):
        self.apply_as("arjun_sharma")
        app = Application.objects.get()
        mail.outbox.clear()
        self.client.force_login(self.employer)
        self.client.post(reverse("applications:update_status", args=[app.pk]), {"status": "shortlisted"})
        app.refresh_from_db()
        self.assertEqual(app.status, "shortlisted")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Shortlisted", mail.outbox[0].body)

    def test_resume_download_is_private(self):
        self.apply_as("arjun_sharma")
        app = Application.objects.get()
        url = reverse("applications:resume", args=[app.pk])
        self.client.force_login(self.candidates["neha_kulkarni"])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.other_employer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.employer)
        self.assertEqual(self.client.get(url).status_code, 200)

    # --- administration ---
    def test_admin_dashboard_and_moderation(self):
        self.apply_as("arjun_sharma")
        self.client.force_login(self.admin)
        r = self.client.get(reverse("adminpanel:dashboard"))
        self.assertEqual(r.context["stats"]["Applications"], 1)
        for tab in ["users", "jobs", "applications"]:
            self.assertEqual(self.client.get(reverse("adminpanel:dashboard"), {"tab": tab}).status_code, 200)
        self.client.post(reverse("adminpanel:user_toggle", args=[self.employer.pk]))
        self.employer.refresh_from_db()
        self.assertFalse(self.employer.is_active)
        self.client.post(reverse("adminpanel:job_delete", args=[self.job.pk]))
        self.assertFalse(Application.objects.exists())

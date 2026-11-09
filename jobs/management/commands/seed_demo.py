"""Load demo data: an admin, an employer, a few jobs and four screened sample candidates."""
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand

from accounts.models import User
from applications.services import submit_application
from jobs.models import Job

RESUMES = Path(settings.BASE_DIR) / "sample_data" / "resumes"
PASSWORD = "demo12345"

JOBS = [
    dict(title="Full Stack Developer (MERN)", location="Pune", job_type="full-time", experience_level="mid",
         salary_min=600000, salary_max=1200000,
         skills_required="javascript, react, node.js, express, mongodb, rest api, git",
         description="We are hiring a full stack developer to build web applications using React on the "
                     "frontend and Node.js with Express on the backend, storing data in MongoDB. You will "
                     "design REST APIs, write clean JavaScript, and collaborate using Git."),
    dict(title="Python Django Developer", location="Remote", job_type="full-time", experience_level="entry",
         skills_required="python, django, postgresql, rest api, git",
         description="Join our team to build REST APIs with Python and Django on PostgreSQL. Freshers with "
                     "good Python fundamentals and project experience are welcome."),
    dict(title="Data Scientist", location="Bengaluru", job_type="full-time", experience_level="senior",
         salary_min=1800000, salary_max=3000000,
         skills_required="python, machine learning, deep learning, pandas, scikit-learn, tensorflow, sql",
         description="Build and deploy machine learning and deep learning models for candidate matching and "
                     "demand forecasting. Strong Python, pandas, scikit-learn and TensorFlow skills needed."),
    dict(title="QA Automation Engineer", location="Chennai", job_type="contract", experience_level="mid",
         skills_required="selenium, java, automation testing, jira, postman",
         description="Design automated test suites with Selenium and Java, test APIs with Postman and track "
                     "defects in Jira."),
]

CANDIDATES = [
    ("arjun_sharma", "Arjun Sharma", "Software Engineer"),
    ("neha_kulkarni", "Neha Kulkarni", "Frontend Developer"),
    ("rahul_verma", "Rahul Verma", "Java Developer"),
    ("sneha_iyer", "Sneha Iyer", "Graphic Designer"),
]


class Command(BaseCommand):
    help = "Create demo users, jobs and screened applications"

    def handle(self, *args, **opts):
        if User.objects.filter(email="hr@techcorp.local").exists():
            self.stdout.write("Demo data already loaded.")
            return
        User.objects.create_superuser("admin@jobmatch.local", PASSWORD, name="Portal Admin")
        employer = User.objects.create_user("hr@techcorp.local", PASSWORD, name="TechCorp HR",
                                            role=User.Role.EMPLOYER, company="TechCorp Solutions")
        jobs = [Job.objects.create(employer=employer, company=employer.company, **j) for j in JOBS]

        for slug, name, title in CANDIDATES:
            cand = User.objects.create_user(f"{slug.split('_')[0]}@example.com", PASSWORD, name=name, title=title)
            upload = SimpleUploadedFile(f"{slug}.txt", (RESUMES / f"{slug}.txt").read_bytes(), "text/plain")
            app = submit_application(jobs[0], cand, upload, cover_letter="")
            self.stdout.write(f"  {name:15} -> {app.match_score:3}%")

        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded. Log in with password '{PASSWORD}' as:\n"
            "  admin@jobmatch.local (admin), hr@techcorp.local (employer), arjun@example.com (candidate)"))

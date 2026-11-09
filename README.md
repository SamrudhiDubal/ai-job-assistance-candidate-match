# JobMatch AI

**Full-stack job portal with AI-based resume screening and candidate matching**, built in Python with Django.

Employers post jobs, candidates apply with a resume, and every resume is screened the moment it is submitted. Employers see applicants ranked by an explainable match score.

## Features

| # | Module | What it does |
|---|--------|--------------|
| 1 | Authentication and roles | Sign up as candidate or employer, log in with email. Admins are created with a command. |
| 2 | Profiles | Headline, skills and bio for candidates; company for employers. |
| 3 | Job management | Employers post, edit, close, reopen and delete jobs. |
| 4 | Job search | Keyword search with location, type, level and skill filters, paginated. |
| 5 | Resume upload and parsing | PDF, DOCX or TXT up to 5 MB, stored privately with random names. |
| 6 | AI screening | Skill match (50%), text similarity (25%) and experience fit (25%). |
| 8 | Ranked applicants | Best match first, with matched and missing skills; status pipeline. |
| 9 | Email notifications | Printed to the console unless SMTP settings are given. |
| 10 | Admin dashboard | Platform stats, user and job moderation, all applications. |

Coming next: machine-learning resume classifier and Sentence-BERT deep-learning matching (step 2), and the analytics notebook (step 3).

## How the match score works

```
Match Score = 0.50 x Skill Match + 0.25 x Text Similarity + 0.25 x Experience Fit
```

* **Skill match**: share of the job's required skills found in the resume or the candidate's profile. A 150-skill dictionary and an alias table handle short forms (`js` = javascript, `k8s` = kubernetes).
* **Text similarity**: cosine similarity of word-frequency vectors of the resume and the job.
* **Experience fit**: years stated in the resume against the job level (entry 0, mid 2, senior 5, lead 8 years).
* If the resume doesn't state years of experience, that weight is shared between the other two signals, so nobody is penalised for missing information. Education level is shown but not scored.

The code is in [`screening/`](screening/).

## Run it locally

Needs Python 3.10 or later.

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # optional demo data
python manage.py runserver
```

Open http://127.0.0.1:8000. Demo logins (password `demo12345`): `admin@jobmatch.local`, `hr@techcorp.local`, `arjun@example.com`.

To create your own administrator: `python manage.py create_admin --email you@example.com`.

## Tests

```bash
python manage.py test
```

## Project layout

```
jobmatch/        settings and URLs
accounts/        users, roles, login, profiles
jobs/            job postings and search
applications/    applying, ranking, status changes, emails
screening/       AI engine: parsers, skills, experience, matcher
adminpanel/      administrator dashboard
templates/       Bootstrap pages
sample_data/     sample resumes used by the demo and the tests
```

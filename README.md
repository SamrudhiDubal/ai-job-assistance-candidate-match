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

| 7 | Optional Claude rating | With `ANTHROPIC_API_KEY` set, Claude rates fit and writes a summary for the employer. |
| 11 | ML and DL models | Resume category classifiers (TF-IDF + Logistic Regression, BiLSTM) and semantic matching. |

## How the match score works

```
Match Score = 0.40 x Skill Match + 0.15 x Text Similarity + 0.25 x Semantic Similarity + 0.20 x Experience Fit
```

* **Skill match** (rules): share of the job's required skills found in the resume or the candidate's profile. A 150-skill dictionary and an alias table handle short forms (`js` = javascript, `k8s` = kubernetes).
* **Text similarity** (ML baseline): cosine similarity of word-frequency vectors of the resume and the job.
* **Semantic similarity** (deep learning): how close the meaning of the resume is to the job.
  * **Sentence-BERT** (`all-MiniLM-L6-v2`) is used when `sentence-transformers` is installed. It understands that "built REST endpoints in Flask" matches "API development in Python" even without shared words.
  * Otherwise the project's own **BiLSTM** model compares the job-category profiles of the resume and the job.
* **Experience fit**: years stated in the resume against the job level (entry 0, mid 2, senior 5, lead 8 years).
* If a signal can't be measured (no years stated, no DL model installed), its weight is shared over the others, so nobody is penalised for missing information. Education level is shown but not scored.
* **Optional Claude rating**: `Final = 0.7 x Match Score + 0.3 x Claude score`, plus a 40-word summary. Off unless `ANTHROPIC_API_KEY` is set.

Each applicant also gets a predicted job category from both classifiers, shown next to the job's own category.

The code is in [`screening/`](screening/).

## The AI models

Trained models are already saved in `screening/models/`, so the app works straight away. To retrain or re-evaluate:

```bash
python manage.py train_models        # trains 3 ML models + the BiLSTM, saves metrics.json
python manage.py evaluate_matching   # compares how well each signal ranks the right candidates
```

**Training data.** By default a synthetic corpus of 3,600 resumes across 12 job categories is generated from role profiles (with deliberate overlap between roles, so the task is not trivial). To train on a real dataset instead, save it as `data/resume_dataset.csv` with the columns `Category` and `Resume` (for example the public Kaggle "Resume Dataset") and run `train_models` again.

**Resume category classification** (720 held-out resumes, 12 classes):

| Model | Type | Accuracy | Macro F1 |
|---|---|---|---|
| TF-IDF + Logistic Regression | ML | 0.868 | 0.868 |
| TF-IDF + Multinomial Naive Bayes | ML | 0.864 | 0.864 |
| TF-IDF + Linear SVM | ML | 0.863 | 0.863 |
| Embedding + Bidirectional LSTM (Keras) | DL | 0.832 | 0.831 |

**Ranking quality** (`evaluate_matching`: 12 job posts, each ranking 300 unseen resumes; relevant = same job category):

| Method | Precision@10 | MAP | NDCG@10 |
|---|---|---|---|
| Skill match (rules) | 0.683 | 0.558 | 0.712 |
| TF cosine (ML baseline) | 0.925 | 0.814 | 0.941 |
| Semantic similarity (DL, BiLSTM backend) | 0.975 | 0.891 | 0.982 |
| Combined JobMatch score | 0.900 | 0.850 | 0.905 |

The combined score ranks slightly below the semantic signal alone in this benchmark because it also rewards experience fit, which the benchmark doesn't measure. Both results come from synthetic data, so they show the method works; real-world accuracy needs real resumes. Exact numbers can shift a little between machines.

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

For Sentence-BERT matching (recommended, about 1 GB with PyTorch): `pip install sentence-transformers`. The model downloads on first use; without it the BiLSTM backend is used.

For the Claude rating, set `ANTHROPIC_API_KEY` before `runserver`.

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

"""Compare how well each screening signal ranks the right candidates first.

For every one of the 12 job categories we write a job post from its role
profile, then rank a pool of unseen synthetic resumes (different random seed
from the training data). A resume counts as relevant when it belongs to the
job's category. Each method is scored with standard ranking metrics:

  Precision@10 - share of the top 10 that are relevant
  MAP          - mean average precision over the whole ranking
  NDCG@10      - rewards relevant resumes near the top

Run with:  python manage.py evaluate_matching
"""
import json
import time
from types import SimpleNamespace

import numpy as np

from .. import experience, matcher, semantic, skills
from .dataset import ROLE_PROFILES, synthetic_corpus
from .train import MODEL_DIR

RESULTS_PATH = MODEL_DIR / "matching_evaluation.json"
LEVELS = ["entry", "mid", "mid", "senior"]


def job_for(role, i):
    p = ROLE_PROFILES[role]
    return SimpleNamespace(
        title=p["titles"][0],
        description=f"We are hiring a {p['titles'][0]}. You will " + "; ".join(p["duties"][:4]) + ".",
        skill_list=p["skills"][:6],
        experience_level=LEVELS[i % len(LEVELS)],
    )


def average_precision(relevant):
    hits, total = 0, 0.0
    for k, rel in enumerate(relevant, 1):
        if rel:
            hits += 1
            total += hits / k
    return total / max(1, sum(relevant))


def ndcg_at(relevant, k=10):
    dcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(relevant[:k]))
    ideal = sum(1 / np.log2(i + 2) for i in range(min(k, sum(relevant))))
    return dcg / ideal if ideal else 0.0


def evaluate(per_role=25, seed=7, log=print):
    pool = synthetic_corpus(per_role=per_role, seed=seed)
    resumes, cats = list(pool.Resume), list(pool.Category)
    methods = {name: [] for name in ["Skill match (rules)", "TF cosine (ML baseline)",
                                     "Semantic similarity (DL)", "Combined JobMatch score"]}
    start = time.time()
    jobs = [job_for(role, i) for i, role in enumerate(ROLE_PROFILES)]
    sem_matrix, backend = semantic.similarity_matrix(resumes, [matcher.job_text(j) for j in jobs])
    if sem_matrix is None:
        # No semantic backend: do not report a ranking that would only reflect input order.
        log("  no semantic backend available; semantic ranking is skipped")
        methods.pop("Semantic similarity (DL)")
    for i, role in enumerate(ROLE_PROFILES):
        job = jobs[i]
        jtext = matcher.job_text(job)
        rows = []
        for r, text in enumerate(resumes):
            req = [skills.canonical(s) for s in job.skill_list]
            found = set(skills.extract_skills(text))
            skill = sum(1 for s in req if s in found or skills.mentions(text, s)) / len(req) * 100
            tf = matcher.cosine_similarity(text, jtext) * 100
            sem = float(sem_matrix[r, i]) if sem_matrix is not None else None
            exp = experience.experience_fit(experience.years_of_experience(text), job.experience_level)
            combined, _ = matcher.blend({"skill": skill, "text": tf, "semantic": sem, "experience": exp})
            rows.append((skill, tf, sem, combined) if sem is not None else (skill, tf, combined))
        rows = np.array(rows)
        for col, name in enumerate(methods):
            order = np.argsort(-rows[:, col], kind="stable")
            relevant = [cats[j] == role for j in order]
            methods[name].append((sum(relevant[:10]) / 10, average_precision(relevant), ndcg_at(relevant)))
        log(f"  ranked {len(resumes)} resumes for {role}")

    results = {
        "pool_size": len(resumes), "jobs": len(ROLE_PROFILES), "semantic_backend": backend,
        "seconds": round(time.time() - start, 1), "methods": {},
    }
    for name, vals in methods.items():
        v = np.array(vals)
        results["methods"][name] = {"precision_at_10": round(float(v[:, 0].mean()), 3),
                                    "map": round(float(v[:, 1].mean()), 3),
                                    "ndcg_at_10": round(float(v[:, 2].mean()), 3)}
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    return results

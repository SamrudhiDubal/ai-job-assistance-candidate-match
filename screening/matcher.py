"""Blend the screening signals into one explainable match score (Module 6).

    Match Score = 0.50 x Skill Match + 0.25 x Text Similarity + 0.25 x Experience Fit

If a signal cannot be measured (for example the resume does not state years of
experience), its weight is shared out over the other signals so the candidate is
not penalised for missing information.
"""
import math
import re
from collections import Counter

from . import experience, skills

WEIGHTS = {"skill": 0.50, "text": 0.25, "experience": 0.25}

STOP_WORDS = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have
having he her here hers him his how i if in into is it its itself just me more most my no nor not
now of off on once only or other our ours out over own same she should so some such than that the
their them then there these they this those through to too under until up very was we were what
when where which while who whom why will with would you your yours etc also using use used work
worked working experience years year role team strong good knowledge ability skills skill job
""".split())

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.]*")


def tokenize(text):
    tokens = (t.rstrip(".") for t in _TOKEN.findall(text.lower()))
    return [t for t in tokens if t and t not in STOP_WORDS and (len(t) > 1 or t in {"c", "r"})]


def cosine_similarity(text_a, text_b):
    """Cosine similarity of term-frequency vectors, between 0 and 1."""
    a, b = Counter(tokenize(text_a)), Counter(tokenize(text_b))
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in a.keys() & b.keys())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def job_text(job):
    return f"{job.title} {job.description} {' '.join(job.skill_list)}"


def blend(signals):
    """Weighted average of the available signals (None = not measurable)."""
    available = {k: v for k, v in signals.items() if v is not None}
    if not available:
        return 0, {}
    total = sum(WEIGHTS[k] for k in available)
    weights = {k: WEIGHTS[k] / total for k in available}
    score = sum(weights[k] * available[k] for k in available)
    return int(math.floor(score + 0.5)), weights


def screen(resume_text, job, declared_skills=()):
    """Score a resume against a job. Returns a dict with the score and its breakdown."""
    required = [skills.canonical(s) for s in job.skill_list]
    detected = set(skills.extract_skills(resume_text))
    declared = {skills.canonical(s) for s in declared_skills}
    candidate_skills = detected | declared

    matched = [s for s in required if s in candidate_skills or skills.mentions(resume_text, s)]
    missing = [s for s in required if s not in matched]
    skill_pct = round(len(matched) / len(required) * 100, 1) if required else None

    text_pct = round(cosine_similarity(resume_text, job_text(job)) * 100, 1)

    years = experience.years_of_experience(resume_text)
    exp_pct = experience.experience_fit(years, job.experience_level)

    score, weights = blend({"skill": skill_pct, "text": text_pct, "experience": exp_pct})
    return {
        "match_score": score,
        "skill_match_percent": skill_pct,
        "text_similarity_percent": text_pct,
        "experience_fit_percent": exp_pct,
        "candidate_years_of_experience": years,
        "education_level": experience.education_level(resume_text),
        "matched_skills": matched,
        "missing_skills": missing,
        "extracted_skills": sorted(candidate_skills | set(matched)),
        "weights_used": {k: round(v, 3) for k, v in weights.items()},
    }

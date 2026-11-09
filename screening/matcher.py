"""Blend the screening signals into one explainable match score (Module 6).

    Match Score = 0.40 x Skill Match            (dictionary + aliases)
                + 0.15 x Text Similarity        (term-frequency cosine, ML baseline)
                + 0.25 x Semantic Similarity    (deep learning: Sentence-BERT or BiLSTM)
                + 0.20 x Experience Fit         (years stated vs job level)

If a signal cannot be measured (for example the resume does not state years of
experience, or no deep-learning model is installed), its weight is shared out
over the other signals so the candidate is not penalised for missing information.

When Claude scoring is switched on (see llm.py):
    Final Score = 0.7 x Match Score + 0.3 x LLM Score
"""
import math
import re
from collections import Counter

from . import experience, llm, semantic, skills

WEIGHTS = {"skill": 0.40, "text": 0.15, "semantic": 0.25, "experience": 0.20}
LLM_WEIGHT = 0.3

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


def _categories(resume_text, jtext):
    """Job category predicted for the resume and for the job by the ML and DL classifiers."""
    from .ml import classifier

    out = {}
    for key, predict in (("ml", classifier.predict_ml), ("dl", classifier.predict_dl)):
        try:
            resume, job = predict(resume_text), predict(jtext)
        except Exception:
            resume = job = None
        if resume and job:
            out[key] = {"model": resume["model"], "resume_category": resume["category"],
                        "resume_confidence": resume["confidence"], "job_category": job["category"],
                        "same_category": resume["category"] == job["category"]}
    return out


def screen(resume_text, job, declared_skills=(), use_models=True):
    """Score a resume against a job. Returns a dict with the score and its breakdown.

    use_models=False skips the trained ML/DL models and Claude (used by fast unit tests).
    """
    required = [skills.canonical(s) for s in job.skill_list]
    detected = set(skills.extract_skills(resume_text))
    declared = {skills.canonical(s) for s in declared_skills}
    candidate_skills = detected | declared

    matched = [s for s in required if s in candidate_skills or skills.mentions(resume_text, s)]
    missing = [s for s in required if s not in matched]
    skill_pct = round(len(matched) / len(required) * 100, 1) if required else None

    jtext = job_text(job)
    text_pct = round(cosine_similarity(resume_text, jtext) * 100, 1)

    semantic_pct, semantic_info = semantic.similarity(resume_text, jtext) if use_models else (None, None)

    years = experience.years_of_experience(resume_text)
    exp_pct = experience.experience_fit(years, job.experience_level)

    score, weights = blend({"skill": skill_pct, "text": text_pct, "semantic": semantic_pct,
                            "experience": exp_pct})
    local_score = score
    llm_result = llm.rate(resume_text, jtext) if use_models else None
    if llm_result:
        score = int(math.floor((1 - LLM_WEIGHT) * local_score + LLM_WEIGHT * llm_result["score"] + 0.5))

    return {
        "match_score": score,
        "local_score": local_score,
        "skill_match_percent": skill_pct,
        "text_similarity_percent": text_pct,
        "semantic_similarity_percent": semantic_pct,
        "semantic_backend": semantic_info["backend"] if semantic_info else None,
        "experience_fit_percent": exp_pct,
        "candidate_years_of_experience": years,
        "education_level": experience.education_level(resume_text),
        "matched_skills": matched,
        "missing_skills": missing,
        "extracted_skills": sorted(candidate_skills | set(matched)),
        "weights_used": {k: round(v, 3) for k, v in weights.items()},
        "predicted_categories": _categories(resume_text, jtext) if use_models else {},
        "semantic_score": llm_result["score"] if llm_result else None,
        "semantic_summary": llm_result["summary"] if llm_result else None,
    }

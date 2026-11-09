"""Deep-learning semantic similarity between a resume and a job (Module 6, signal 4).

Two backends, tried in this order:

1. Sentence-BERT (`sentence-transformers`, model all-MiniLM-L6-v2): a pretrained
   transformer that maps each text to a 384-number vector so that texts with
   similar meaning are close together, even when they use different words.
   Installed with `pip install sentence-transformers`; the model (about 90 MB)
   downloads on first use.
2. The project's own BiLSTM model (trained by `manage.py train_models`). It turns
   the resume and the job into probability profiles over the 12 job categories,
   and the overlap of the two profiles (Bhattacharyya coefficient, 0 to 1) says
   how alike the two roles are. Used when Sentence-BERT is not installed or its
   model cannot be downloaded.

If neither is available, the signal is skipped and its weight is shared out over
the other signals.

Raw cosine similarities from Sentence-BERT are rarely near 0 even for unrelated
texts, so they are mapped onto 0-100 with a calibrated linear scale
(0.15 -> 0 %, 0.70 -> 100 %).
"""
import logging
import os
import threading

import numpy as np

log = logging.getLogger("jobmatch.screening")

SBERT_MODEL = os.environ.get("JOBMATCH_SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SCALE = {"sbert": (0.15, 0.70), "bilstm": (0.0, 1.0)}

_lock = threading.Lock()
_state = {}


def _sbert():
    with _lock:
        if "sbert" not in _state:
            _state["sbert"] = None
            if os.environ.get("JOBMATCH_SEMANTIC_BACKEND", "auto") in ("auto", "sbert"):
                try:
                    from sentence_transformers import SentenceTransformer

                    _state["sbert"] = SentenceTransformer(SBERT_MODEL)
                except Exception as exc:  # not installed, or no internet for the first download
                    log.info("Sentence-BERT unavailable (%s); falling back to the BiLSTM encoder", exc)
        return _state["sbert"]


def _sbert_cosine(resume_text, job_text):
    model = _sbert()
    if model is None:
        return None
    vectors = np.asarray(model.encode([resume_text, job_text], normalize_embeddings=True))
    return cosine(vectors[0], vectors[1])


def _bilstm_overlap(resume_text, job_text):
    from .ml.classifier import dl_probabilities

    probs = dl_probabilities([resume_text, job_text])
    if probs is None:
        return None
    return float(np.sum(np.sqrt(probs[0] * probs[1])))


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0


def to_percent(value, backend):
    low, high = SCALE[backend]
    return round(float(np.clip((value - low) / (high - low), 0, 1)) * 100, 1)


def similarity(resume_text, job_text):
    """Semantic similarity as a percentage plus details, or (None, None) if no backend is available."""
    choice = os.environ.get("JOBMATCH_SEMANTIC_BACKEND", "auto")
    try:
        if choice in ("auto", "sbert"):
            value = _sbert_cosine(resume_text, job_text)
            if value is not None:
                return to_percent(value, "sbert"), {"backend": "Sentence-BERT", "raw": round(value, 4)}
        if choice in ("auto", "bilstm"):
            value = _bilstm_overlap(resume_text, job_text)
            if value is not None:
                return to_percent(value, "bilstm"), {"backend": "BiLSTM role profile", "raw": round(value, 4)}
    except Exception:
        log.exception("Semantic similarity failed")
    return None, None


def similarity_matrix(resume_texts, job_texts):
    """Batch version for evaluation: (matrix of percentages [resume x job], backend) or (None, None)."""
    choice = os.environ.get("JOBMATCH_SEMANTIC_BACKEND", "auto")
    texts = list(resume_texts) + list(job_texts)
    n = len(resume_texts)
    if choice in ("auto", "sbert") and _sbert() is not None:
        v = np.asarray(_sbert().encode(texts, normalize_embeddings=True, batch_size=64))
        cos = v[:n] @ v[n:].T
        low, high = SCALE["sbert"]
        return np.clip((cos - low) / (high - low), 0, 1) * 100, "Sentence-BERT"
    if choice in ("auto", "bilstm"):
        from .ml.classifier import dl_probabilities

        p = dl_probabilities(texts)
        if p is not None:
            return np.sqrt(p[:n]) @ np.sqrt(p[n:]).T * 100, "BiLSTM role profile"
    return None, None

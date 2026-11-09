"""Predict a resume's job category with the saved ML and DL models.

Models are loaded once, on first use. If a model file or its library is
missing, that prediction is simply skipped (returns None).
"""
import json
import logging
import os
import threading

import numpy as np

from .train import DL_PATH, LABELS_PATH, ML_PATH

log = logging.getLogger("jobmatch.screening")
_lock = threading.Lock()
_cache = {}


def _labels():
    if "labels" not in _cache:
        _cache["labels"] = json.loads(LABELS_PATH.read_text()) if LABELS_PATH.exists() else []
    return _cache["labels"]


def ml_model():
    with _lock:
        if "ml" not in _cache:
            _cache["ml"] = None
            if ML_PATH.exists():
                try:
                    import joblib

                    _cache["ml"] = joblib.load(ML_PATH)
                except Exception:
                    log.exception("Could not load the ML classifier")
        return _cache["ml"]


def dl_model():
    """The Keras BiLSTM classifier, or None when TensorFlow is unavailable or disabled."""
    with _lock:
        if "dl" not in _cache:
            _cache["dl"] = None
            if DL_PATH.exists() and os.environ.get("JOBMATCH_DISABLE_DL") != "1":
                try:
                    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
                    import keras

                    _cache["dl"] = (keras.models.load_model(DL_PATH, compile=False),)
                except Exception:
                    log.warning("Deep-learning model not available; continuing without it", exc_info=True)
        return _cache["dl"]


def predict_ml(text):
    model = ml_model()
    if model is None:
        return None
    probs = model.predict_proba([text])[0]
    i = int(np.argmax(probs))
    return {"category": str(model.classes_[i]), "confidence": round(float(probs[i]) * 100, 1),
            "model": "TF-IDF + " + type(model[-1]).__name__}


def predict_dl(text):
    loaded = dl_model()
    if loaded is None:
        return None
    probs = dl_probabilities([text])[0]
    i = int(np.argmax(probs))
    return {"category": _labels()[i], "confidence": round(float(probs[i]) * 100, 1), "model": "BiLSTM (Keras)"}


def dl_probabilities(texts):
    """Category probability vectors from the BiLSTM model, or None if it isn't available."""
    loaded = dl_model()
    if loaded is None:
        return None
    import tensorflow as tf

    return loaded[0].predict(tf.constant(list(texts)), verbose=0)

"""Train the resume job-category classifiers and save them with their metrics.

ML models : TF-IDF features + Logistic Regression / Linear SVM / Naive Bayes
DL model  : Keras text model (embedding + bidirectional LSTM)

Run with:  python manage.py train_models
"""
import json
import time
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
import joblib

from .dataset import load_corpus

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
ML_PATH = MODEL_DIR / "ml_classifier.joblib"
DL_PATH = MODEL_DIR / "dl_classifier.keras"
LABELS_PATH = MODEL_DIR / "labels.json"
METRICS_PATH = MODEL_DIR / "metrics.json"

SEED = 42


def _tfidf():
    return TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=30000,
                           stop_words="english")


ML_CANDIDATES = {
    "Logistic Regression": lambda: LogisticRegression(max_iter=2000, C=4.0),
    "Linear SVM": lambda: LinearSVC(C=0.5),
    "Multinomial Naive Bayes": lambda: MultinomialNB(alpha=0.1),
}


def _scores(y_true, y_pred, labels):
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_f1": round(f1_score(y_true, y_pred, average="macro"), 4),
        "report": classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def train_ml(X_train, X_test, y_train, y_test, labels, log=print):
    """Pick the best classifier by 5-fold cross-validation on the training set only.

    The held-out test set is used once, after selection, so the reported test scores
    are an unbiased estimate for the chosen model.
    """
    results, best = {}, None
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    for name, make in ML_CANDIDATES.items():
        start = time.time()
        pipe = Pipeline([("tfidf", _tfidf()), ("clf", make())])
        cv_f1 = cross_val_score(pipe, X_train, y_train, cv=folds, scoring="f1_macro").mean()
        pipe.fit(X_train, y_train)
        scores = _scores(y_test, pipe.predict(X_test), labels)
        scores["cv_macro_f1"] = round(float(cv_f1), 4)
        scores["train_seconds"] = round(time.time() - start, 2)
        results[name] = scores
        log(f"  {name:25} cv-F1={cv_f1:.3f}  test accuracy={scores['accuracy']:.3f}  "
            f"test macro-F1={scores['macro_f1']:.3f}")
        if best is None or scores["cv_macro_f1"] > results[best[0]]["cv_macro_f1"]:
            best = (name, pipe)
    # Keep the best model; Linear SVM has no probabilities, so calibrate if it wins.
    name, pipe = best
    if name == "Linear SVM":
        from sklearn.calibration import CalibratedClassifierCV

        pipe = Pipeline([("tfidf", _tfidf()), ("clf", CalibratedClassifierCV(LinearSVC(C=0.5), cv=3))])
        pipe.fit(X_train, y_train)
    return name, pipe, results


def build_dl_model(n_classes, vocab_size=8000, seq_len=200):
    import keras
    from keras import layers

    vectorizer = layers.TextVectorization(max_tokens=vocab_size, output_sequence_length=seq_len,
                                          standardize="lower_and_strip_punctuation", name="vectorizer")
    inputs = keras.Input(shape=(1,), dtype="string", name="resume_text")
    x = vectorizer(inputs)
    x = layers.Embedding(vocab_size, 48, mask_zero=True, name="word_embedding")(x)
    x = layers.Bidirectional(layers.LSTM(48), name="bilstm")(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(64, activation="relu", name="resume_embedding")(x)
    outputs = layers.Dense(n_classes, activation="softmax", name="category")(x)
    model = keras.Model(inputs, outputs, name="resume_bilstm")
    return model, vectorizer


def train_dl(X_train, X_test, y_train, y_test, labels, epochs=12, log=print):
    import keras
    import tensorflow as tf

    keras.utils.set_random_seed(SEED)
    index = {label: i for i, label in enumerate(labels)}
    ytr = np.array([index[y] for y in y_train])
    yte = np.array([index[y] for y in y_test])
    Xtr = tf.constant(list(X_train))
    Xte = tf.constant(list(X_test))

    model, vectorizer = build_dl_model(len(labels))
    vectorizer.adapt(tf.data.Dataset.from_tensor_slices(Xtr).batch(256))
    model.compile(optimizer=keras.optimizers.Adam(2e-3), loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    start = time.time()
    history = model.fit(
        Xtr, ytr, validation_split=0.1, epochs=epochs, batch_size=64, verbose=0,
        callbacks=[keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True)],
    )
    pred = model.predict(Xte, verbose=0).argmax(axis=1)
    scores = _scores([labels[i] for i in yte], [labels[i] for i in pred], labels)
    scores["train_seconds"] = round(time.time() - start, 2)
    scores["epochs_run"] = len(history.history["loss"])
    scores["history"] = {k: [round(float(v), 4) for v in vals] for k, vals in history.history.items()}
    log(f"  {'BiLSTM (Keras)':25} accuracy={scores['accuracy']:.3f}  macro-F1={scores['macro_f1']:.3f}")
    return model, scores


def _supports_no_opt():
    import inspect

    import keras

    return "include_optimizer" in inspect.signature(keras.Model.save).parameters


def train_all(base_dir, with_dl=True, log=print):
    df, source = load_corpus(base_dir)
    log(f"Training data: {source}")
    labels = sorted(df.Category.unique())
    X_train, X_test, y_train, y_test = train_test_split(
        df.Resume, df.Category, test_size=0.2, stratify=df.Category, random_state=SEED)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    log("Machine-learning models (TF-IDF features):")
    best_name, best_pipe, ml_results = train_ml(X_train, X_test, y_train, y_test, labels, log)
    joblib.dump(best_pipe, ML_PATH, compress=3)

    metrics = {"data_source": source, "labels": labels, "train_size": len(X_train), "test_size": len(X_test),
               "ml": ml_results, "best_ml_model": best_name, "dl": None}
    if with_dl:
        log("Deep-learning model:")
        model, dl_scores = train_dl(X_train, X_test, y_train, y_test, labels, log=log)
        model.save(DL_PATH, include_optimizer=False) if _supports_no_opt() else model.save(DL_PATH)
        metrics["dl"] = {"BiLSTM (Keras)": dl_scores}

    LABELS_PATH.write_text(json.dumps(labels, indent=2))
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    log(f"Saved models to {MODEL_DIR}")
    return metrics

# Analytics

| File | What it is |
|------|------------|
| `generate_dataset.py` | Creates `data/talent_recruitment.csv`: 12,000 synthetic candidates x 26 attributes (report Table 3.6). |
| `recruitment_analytics.ipynb` | EDA, then **Random Forest (ML)** vs **neural network (DL, Keras)** predicting candidate suitability. |
| `hiring_funnel.ipynb` | Funnel analysis of a real hiring tracker, anonymised (needs `data/private/Recruitment_Tracker.xlsx`, which is never committed). |
| `dashboard.py` | Streamlit dashboard of all the results. |
| `figures/` | Charts saved by the notebooks, ready for the report. |

## Run

From the project folder, with the virtual environment active:

```bash
python analytics/generate_dataset.py          # only if data/talent_recruitment.csv is missing
cd analytics
jupyter notebook recruitment_analytics.ipynb  # or open it in VS Code / Google Colab
cd ..
streamlit run analytics/dashboard.py
```

Install Jupyter with `pip install notebook` if you don't have it. The notebooks save trained models to `analytics/models/`, which is not committed because the Random Forest file is large.

## Results (test set of 2,400 candidates)

| Model | Accuracy | Macro F1 |
|---|---|---|
| Random Forest, 300 trees (ML) | 0.657 | 0.648 |
| Neural network, 128-64 MLP (DL) | 0.698 | 0.698 |

The three classes overlap by design, so neither model can be perfect. The neural network does better here because suitability is mostly a smooth weighted combination of the scores. The Random Forest is easier to explain through its feature importances.

## Hiring funnel (real tracker, 1,088 candidates)

Of 959 screened candidates, 808 had an L1 interview scheduled but only 271 L1 results were recorded. 67 passed L2, 22 passed L3 and 4 reached an offer or joined, and 85% of candidates were still waiting on a pending step. See `hiring_funnel.ipynb` for the details.

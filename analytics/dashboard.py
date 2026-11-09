"""JobMatch AI analytics dashboard (Streamlit).

Run from the project folder:   streamlit run analytics/dashboard.py

Shows the recruitment dataset, the Random Forest vs neural-network results,
the screening-model metrics and the hiring-funnel charts. Run the two notebooks
in analytics/ (and `python manage.py train_models`) first so the results exist.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIG = HERE / "figures"

st.set_page_config(page_title="JobMatch AI analytics", layout="wide")
st.title("JobMatch AI: recruitment analytics")


def show(name, caption=None):
    path = FIG / name
    if path.exists():
        st.image(str(path), caption=caption, width="stretch")
    else:
        st.info(f"{name} not found yet. Run the notebooks in analytics/ to create it.")


tab_data, tab_models, tab_screening, tab_funnel = st.tabs(
    ["Dataset", "Suitability models", "Resume screening models", "Hiring funnel"])

with tab_data:
    data_path = HERE / "data" / "talent_recruitment.csv"
    if not data_path.exists():
        st.warning("Dataset missing. Run: python analytics/generate_dataset.py")
    else:
        df = pd.read_csv(data_path)
        c1, c2, c3 = st.columns(3)
        c1.metric("Candidates", f"{len(df):,}")
        c2.metric("Attributes", df.shape[1])
        c3.metric("Missing values", int(df.isna().sum().sum()))
        level = st.multiselect("Career level", sorted(df.Career_Level.unique()))
        role = st.multiselect("Preferred job title", sorted(df.Preferred_Job_Title.unique()))
        view = df
        if level:
            view = view[view.Career_Level.isin(level)]
        if role:
            view = view[view.Preferred_Job_Title.isin(role)]
        st.write(f"{len(view):,} candidates match the filters")
        st.bar_chart(view.Target_Category.value_counts())
        metric = st.selectbox("Average score by suitability",
                              ["Resume_Score", "Problem_Solving_Score", "Communication_Score",
                               "Leadership_Score", "Recruiter_Rating", "CGPA"])
        st.bar_chart(view.groupby("Target_Category")[metric].mean())
        st.dataframe(view.head(200), width="stretch")

with tab_models:
    comp = FIG / "model_comparison.csv"
    if comp.exists():
        st.subheader("Random Forest (ML) vs neural network (DL)")
        st.dataframe(pd.read_csv(comp), width="stretch", hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        show("rf_confusion_matrix.png", "Random Forest")
        show("rf_feature_importance.png")
    with c2:
        show("nn_confusion_matrix.png", "Neural network")
        show("nn_training_curves.png")

with tab_screening:
    models = ROOT / "screening" / "models"
    metrics_path = models / "metrics.json"
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text())
        st.caption(f"Training data: {m['data_source']}")
        rows = [{"Model": k, "Type": "ML", "Accuracy": v["accuracy"], "Macro F1": v["macro_f1"]} for k, v in m["ml"].items()]
        rows += [{"Model": k, "Type": "DL", "Accuracy": v["accuracy"], "Macro F1": v["macro_f1"]}
                 for k, v in (m.get("dl") or {}).items()]
        st.subheader("Resume job-category classifiers")
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    eval_path = models / "matching_evaluation.json"
    if eval_path.exists():
        e = json.loads(eval_path.read_text())
        st.subheader("Ranking quality of each screening signal")
        st.caption(f"{e['jobs']} jobs x {e['pool_size']} resumes, semantic backend: {e['semantic_backend']}")
        st.dataframe(pd.DataFrame(e["methods"]).T.rename(columns={
            "precision_at_10": "Precision@10", "map": "MAP", "ndcg_at_10": "NDCG@10"}), width="stretch")
    if not metrics_path.exists():
        st.info("Run: python manage.py train_models")

with tab_funnel:
    st.caption("Aggregated from a real hiring tracker; no personal data is shown.")
    show("funnel_stages.png")
    c1, c2 = st.columns(2)
    with c1:
        show("funnel_roles.png")
    with c2:
        show("funnel_current_status.png")
    show("funnel_sources_monthly.png")

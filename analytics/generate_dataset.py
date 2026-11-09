"""Generate the synthetic talent-recruitment dataset used by the analytics notebook.

12,000 candidates x 26 attributes, matching the schema described in the project
report (Table 3.6). Numerical attributes are drawn from roughly uniform ranges
and are nearly independent, apart from current and expected salary. The target
Target_Category depends on a *combination* of attributes plus noise, which is
the situation the report describes as suited to ensemble tree models.

Usage:  python analytics/generate_dataset.py  (writes analytics/data/talent_recruitment.csv)
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "data" / "talent_recruitment.csv"
N = 12_000
SEED = 42

ROLES = ["Software Engineer", "Data Analyst", "Data Scientist", "DevOps Engineer", "QA Engineer",
         "Product Manager", "Business Analyst", "UI/UX Designer", "HR Executive", "Sales Executive"]
SKILLS = {
    "Software Engineer": "Python;Java;SQL;Git", "Data Analyst": "SQL;Excel;Power BI;Python",
    "Data Scientist": "Python;Machine Learning;Deep Learning;SQL", "DevOps Engineer": "AWS;Docker;Kubernetes;Linux",
    "QA Engineer": "Selenium;Java;Jira;Postman", "Product Manager": "Agile;Jira;Analytics;Roadmapping",
    "Business Analyst": "Excel;SQL;Requirements;Tableau", "UI/UX Designer": "Figma;Prototyping;User Research",
    "HR Executive": "Recruitment;Communication;HRMS", "Sales Executive": "Negotiation;CRM;Communication",
}
INDUSTRY = ["IT Services", "FinTech", "E-commerce", "Healthcare", "Manufacturing", "Education", "Consulting"]
DEGREE = ["High School", "Diploma", "Bachelor's", "Master's", "PhD"]
DEGREE_P = [0.05, 0.10, 0.50, 0.30, 0.05]
SPECIAL = ["Computer Science", "Information Technology", "Electronics", "Mechanical", "Commerce",
           "Management", "Statistics", "Design"]
LOCATIONS = ["Beijing", "Shanghai", "Shenzhen", "Hangzhou", "Guangzhou", "Chengdu", "Wuhan", "Nanjing"]
COMPANIES = [f"Company_{i:02d}" for i in range(1, 41)]
CERTS = ["No Certification", "AWS Certified", "PMP", "Google Data Analytics", "Scrum Master", "ISTQB", "Azure Fundamentals"]
MODES = ["Onsite", "Remote", "Hybrid"]
LEVELS = ["Entry", "Mid", "Senior", "Lead"]
CLASS_COUNTS = {"Highly Suitable": 4114, "Moderately Suitable": 3887, "Less Suitable": 3999}


def z(x):
    return (x - x.mean()) / x.std()


def generate(n=N, seed=SEED):
    rng = np.random.default_rng(seed)
    exp = rng.integers(0, 21, n)
    level = np.select([exp < 3, exp < 7, exp < 12], LEVELS[:3], "Lead")
    # Some candidates claim a level that doesn't match their experience.
    mismatch = rng.random(n) < 0.15
    level = np.where(mismatch, rng.choice(LEVELS, n), level)
    current_role = rng.choice(ROLES, n)
    preferred = np.where(rng.random(n) < 0.7, current_role, rng.choice(ROLES, n))
    salary = np.round(rng.uniform(60, 600, n), 1)
    df = pd.DataFrame({
        "Candidate_ID": [f"C{i:05d}" for i in range(1, n + 1)],
        "Gender": rng.choice(["Male", "Female", "Other"], n, p=[0.52, 0.46, 0.02]),
        "Age": rng.integers(21, 56, n),
        "Location": rng.choice(LOCATIONS, n),
        "Highest_Degree": rng.choice(DEGREE, n, p=DEGREE_P),
        "Specialization": rng.choice(SPECIAL, n),
        "CGPA": np.round(rng.uniform(5.0, 10.0, n), 2),
        "Experience_Years": exp,
        "Current_Role": current_role,
        "Preferred_Job_Title": preferred,
        "Industry": rng.choice(INDUSTRY, n),
        "Company_Name": rng.choice(COMPANIES, n),
        "Current_Salary_CNY_K": salary,
        "Expected_Salary_CNY_K": np.round(salary * rng.uniform(1.05, 1.5, n), 1),
        "Communication_Score": rng.integers(1, 101, n),
        "Leadership_Score": rng.integers(1, 101, n),
        "Problem_Solving_Score": rng.integers(1, 101, n),
        "Resume_Score": rng.integers(1, 101, n),
        "Job_Applications_Count": rng.integers(1, 51, n),
        "Interview_Attempts": rng.integers(0, 16, n),
        "Recruiter_Rating": np.round(rng.uniform(1.0, 5.0, n), 1),
        "Preferred_Work_Mode": rng.choice(MODES, n),
        "Career_Level": level,
        "Technical_Skills": [SKILLS[r] for r in preferred],
        "Certifications": rng.choice(CERTS, n, p=[0.40, 0.12, 0.10, 0.10, 0.10, 0.09, 0.09]),
    })

    # Hidden suitability: a combination of signals plus noise (age, gender, location play no part).
    degree_bonus = df.Highest_Degree.map({"High School": -0.6, "Diploma": -0.3, "Bachelor's": 0.0,
                                          "Master's": 0.3, "PhD": 0.4})
    level_min = df.Career_Level.map({"Entry": 0, "Mid": 3, "Senior": 7, "Lead": 12})
    level_fit = np.where(df.Experience_Years >= level_min, 0.5, -0.8)
    role_fit = np.where(df.Current_Role == df.Preferred_Job_Title, 0.4, -0.2)
    cert = np.where(df.Certifications != "No Certification", 0.3, 0.0)
    salary_gap = -0.4 * z(df.Expected_Salary_CNY_K / df.Current_Salary_CNY_K)
    # Interaction: communication matters more for senior and lead roles.
    senior = df.Career_Level.isin(["Senior", "Lead"]).astype(float)
    latent = (0.9 * z(df.Resume_Score) + 0.8 * z(df.Problem_Solving_Score) + 0.5 * z(df.Communication_Score)
              + 0.6 * senior * z(df.Leadership_Score) + 0.7 * z(df.Recruiter_Rating) + 0.5 * z(df.CGPA)
              + degree_bonus + level_fit + role_fit + cert + salary_gap
              - 0.3 * z(df.Interview_Attempts) + rng.normal(0, 0.9, n))

    order = np.argsort(-latent.to_numpy())
    target = np.empty(n, dtype=object)
    start = 0
    for label in ["Highly Suitable", "Moderately Suitable", "Less Suitable"]:
        count = round(CLASS_COUNTS[label] * n / N)
        target[order[start:start + count]] = label
        start += count
    target[order[start:]] = "Less Suitable"
    df["Target_Category"] = target
    return df


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = generate()
    data.to_csv(OUT, index=False)
    print(f"Wrote {OUT} with shape {data.shape}")
    print(data.Target_Category.value_counts())

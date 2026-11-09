"""Labelled resume corpus for training the job-category classifiers.

By default a synthetic corpus is generated from role profiles, so the project
runs without downloading anything. If `data/resume_dataset.csv` exists with the
columns `Category` and `Resume` (for example the public Kaggle "Resume Dataset"),
it is used instead.
"""
import random
from pathlib import Path

import pandas as pd

ROLE_PROFILES = {
    "Backend Developer": {
        "titles": ["Backend Developer", "Software Engineer (Backend)", "Python Developer", "Java Developer", "API Engineer"],
        "skills": ["python", "java", "django", "flask", "fastapi", "spring boot", "node.js", "rest api", "postgresql",
                   "mysql", "redis", "microservices", "docker", "git", "sql", "graphql", "kafka", "go"],
        "duties": ["designed and built REST APIs serving millions of requests", "optimised SQL queries and database indexes",
                   "implemented authentication and role-based authorisation on the server",
                   "split a monolith into microservices communicating over message queues",
                   "wrote background jobs and caching layers with Redis", "maintained server-side business logic and data models",
                   "integrated third-party payment and notification APIs", "improved API latency through profiling"],
    },
    "Frontend Developer": {
        "titles": ["Frontend Developer", "Web Developer", "UI Engineer", "React Developer"],
        "skills": ["javascript", "typescript", "react", "angular", "vue", "html", "css", "tailwind css", "redux", "next.js",
                   "bootstrap", "sass", "webpack", "jest", "figma", "git"],
        "duties": ["built responsive single-page applications", "converted Figma designs into pixel-perfect pages",
                   "created reusable UI component libraries", "improved page load speed and Lighthouse scores",
                   "managed client-side state with Redux", "ensured accessibility and cross-browser compatibility",
                   "implemented interactive dashboards and forms in the browser"],
    },
    "Full Stack Developer": {
        "titles": ["Full Stack Developer", "MERN Stack Developer", "Software Engineer (Full Stack)"],
        "skills": ["javascript", "react", "node.js", "express", "mongodb", "rest api", "python", "django", "html", "css",
                   "postgresql", "docker", "git", "typescript", "aws"],
        "duties": ["developed features end to end from database to user interface",
                   "built React frontends backed by Node.js and Express APIs",
                   "designed MongoDB schemas and REST endpoints for web applications",
                   "deployed full stack applications to the cloud", "owned both client and server code for a SaaS product"],
    },
    "Data Scientist": {
        "titles": ["Data Scientist", "Machine Learning Engineer", "AI Engineer", "Data Analyst"],
        "skills": ["python", "machine learning", "deep learning", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
                   "keras", "nlp", "statistics", "sql", "matplotlib", "seaborn", "spark", "power bi", "tableau", "transformers"],
        "duties": ["trained classification and regression models to predict customer churn",
                   "built NLP pipelines for text classification and named entity recognition",
                   "performed exploratory data analysis and statistical testing",
                   "deployed deep learning models for image recognition", "created dashboards and reports for business teams",
                   "engineered features and tuned hyperparameters with cross-validation", "analysed large datasets with Spark"],
    },
    "DevOps Engineer": {
        "titles": ["DevOps Engineer", "Site Reliability Engineer", "Cloud Engineer", "Platform Engineer"],
        "skills": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd", "linux", "bash",
                   "prometheus", "grafana", "helm", "nginx", "github actions", "python"],
        "duties": ["automated infrastructure provisioning with infrastructure as code",
                   "built CI/CD pipelines for automated build, test and deployment", "managed Kubernetes clusters in production",
                   "set up monitoring, alerting and on-call runbooks", "reduced cloud costs through right-sizing",
                   "containerised legacy applications", "maintained Linux servers and networking"],
    },
    "Mobile Developer": {
        "titles": ["Android Developer", "iOS Developer", "Mobile Developer", "Flutter Developer"],
        "skills": ["android", "kotlin", "java", "ios", "swift", "swiftui", "flutter", "dart", "react native", "firebase",
                   "jetpack compose", "rest api", "git", "sqlite"],
        "duties": ["published apps on the Google Play Store and Apple App Store", "built offline-first mobile features",
                   "integrated push notifications and in-app payments", "improved app startup time and crash-free rate",
                   "implemented mobile UI screens following material design guidelines"],
    },
    "QA Engineer": {
        "titles": ["QA Engineer", "Software Test Engineer", "Automation Tester", "SDET"],
        "skills": ["manual testing", "automation testing", "selenium", "cypress", "playwright", "postman", "jmeter", "junit",
                   "pytest", "appium", "jira", "java", "python", "sql", "agile"],
        "duties": ["wrote and executed test cases and test plans", "automated regression suites with Selenium",
                   "performed API testing with Postman", "logged and tracked defects in Jira",
                   "ran load and performance tests", "participated in sprint planning to define acceptance criteria",
                   "performed smoke, sanity and regression testing before releases"],
    },
    "UI/UX Designer": {
        "titles": ["UI/UX Designer", "Product Designer", "Visual Designer", "Graphic Designer"],
        "skills": ["figma", "adobe xd", "photoshop", "illustrator", "sketch", "ux design", "ui design", "wireframing",
                   "html", "css", "communication"],
        "duties": ["conducted user research and usability testing", "created wireframes, prototypes and design systems",
                   "designed brand identities, logos and marketing creatives", "collaborated with developers on design handoff",
                   "mapped user journeys and information architecture"],
    },
    "Project Manager": {
        "titles": ["Project Manager", "Scrum Master", "Delivery Manager", "Agile Coach"],
        "skills": ["agile", "scrum", "kanban", "jira", "confluence", "project management", "risk management",
                   "stakeholder management", "communication", "leadership", "excel"],
        "duties": ["facilitated sprint planning, daily stand-ups and retrospectives", "managed project scope, budget and timelines",
                   "tracked risks and dependencies across teams", "reported delivery status to senior stakeholders",
                   "removed blockers for development teams", "coordinated releases across multiple squads"],
    },
    "Product Manager": {
        "titles": ["Product Manager", "Product Owner", "Associate Product Manager"],
        "skills": ["product management", "agile", "jira", "stakeholder management", "data analysis", "sql", "excel",
                   "communication", "leadership", "figma", "power bi"],
        "duties": ["defined the product roadmap and prioritised the backlog", "wrote user stories and product requirement documents",
                   "analysed product metrics to guide decisions", "ran customer interviews and market research",
                   "launched new features and measured adoption", "aligned engineering, design and business teams on goals"],
    },
    "Cyber Security Analyst": {
        "titles": ["Security Analyst", "Cyber Security Engineer", "Penetration Tester", "SOC Analyst"],
        "skills": ["cybersecurity", "network security", "penetration testing", "owasp", "siem", "encryption", "linux",
                   "python", "bash", "oauth", "aws"],
        "duties": ["performed vulnerability assessments and penetration tests", "monitored security alerts in the SIEM",
                   "investigated and responded to security incidents", "hardened servers and network configurations",
                   "reviewed applications against the OWASP top ten"],
    },
    "Support Engineer": {
        "titles": ["Technical Support Engineer", "Application Support Engineer", "Integration Engineer"],
        "skills": ["sql", "linux", "rest api", "postman", "jira", "communication", "problem solving", "bash", "excel",
                   "python"],
        "duties": ["resolved customer tickets within service-level agreements", "diagnosed production issues from application logs",
                   "integrated client systems through APIs and data feeds", "wrote knowledge-base articles and runbooks",
                   "escalated bugs to engineering with clear reproduction steps"],
    },
}

GENERIC = ["worked closely with cross-functional teams", "mentored junior colleagues", "presented work to clients",
           "documented processes and best practices", "followed agile ways of working", "received a spot award for delivery"]
EDUCATION = ["B.Tech in Computer Science", "B.E. in Information Technology", "B.Sc in Computer Science", "BCA", "MCA",
             "M.Tech in Software Engineering", "MBA", "B.Com", "M.Sc in Data Science", "Bachelor of Design"]
COMPANIES = ["Infosys", "TCS", "Wipro", "a fintech startup", "an e-commerce company", "a healthcare SaaS firm",
             "a product company", "a consulting firm", "Accenture", "a logistics startup"]


def _resume(role, rng):
    p = ROLE_PROFILES[role]
    # Real resumes overlap with neighbouring roles, so mix in a secondary role.
    other = rng.choice([r for r in ROLE_PROFILES if r != role])
    o = ROLE_PROFILES[other]
    skills = rng.sample(p["skills"], k=rng.randint(2, min(7, len(p["skills"]))))
    skills += rng.sample(o["skills"], k=rng.randint(1, 5))
    skills = list(dict.fromkeys(skills))
    rng.shuffle(skills)
    duties = rng.sample(p["duties"], k=rng.randint(1, min(3, len(p["duties"]))))
    if rng.random() < 0.6:
        duties += rng.sample(o["duties"], k=rng.randint(1, 2))
    duties.append(rng.choice(GENERIC))
    rng.shuffle(duties)
    years = rng.randint(0, 12)
    # Many resumes don't state a clear job title, so the model must learn from content.
    if rng.random() < 0.45:
        title = rng.choice(p["titles"])
    elif rng.random() < 0.3:
        title = rng.choice(o["titles"])  # e.g. a QA engineer moving into development
    else:
        title = rng.choice(["Software Professional", "Engineer", "Consultant", "Associate", "IT Professional"])
    exp = f"{years} years of experience" if years else "fresher with internship experience"
    lines = [
        f"{title}",
        f"Summary: {title.lower()} with {exp} at {rng.choice(COMPANIES)}.",
        "Skills: " + ", ".join(skills),
        "Experience: " + ". ".join(d.capitalize() for d in duties) + ".",
        f"Education: {rng.choice(EDUCATION)}",
    ]
    return "\n".join(lines)


def synthetic_corpus(per_role=300, seed=42):
    rng = random.Random(seed)
    rows = [{"Category": role, "Resume": _resume(role, rng)} for role in ROLE_PROFILES for _ in range(per_role)]
    rng.shuffle(rows)
    return pd.DataFrame(rows)


def load_corpus(base_dir, per_role=300, seed=42):
    """Return (dataframe, source description)."""
    path = Path(base_dir) / "data" / "resume_dataset.csv"
    if path.exists():
        df = pd.read_csv(path)[["Category", "Resume"]].dropna()
        return df, f"external dataset {path.name} ({len(df)} resumes)"
    df = synthetic_corpus(per_role, seed)
    return df, f"synthetic corpus ({len(df)} resumes, {df.Category.nunique()} job categories)"

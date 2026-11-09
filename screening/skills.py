"""Skill dictionary, alias table and skill detection (Module 6, signal 1)."""
import re

# Canonical skills grouped by area. Every value is the canonical (stored) form.
SKILL_DICTIONARY = {
    "languages": [
        "python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "rust", "kotlin",
        "swift", "php", "ruby", "scala", "r", "matlab", "perl", "dart", "bash", "sql",
    ],
    "frontend": [
        "html", "css", "react.js", "angular", "vue.js", "next.js", "svelte", "redux",
        "tailwind css", "bootstrap", "sass", "jquery", "webpack", "vite",
    ],
    "backend": [
        "node.js", "express.js", "django", "flask", "fastapi", "spring boot", "spring",
        ".net", "asp.net", "laravel", "ruby on rails", "rest", "graphql", "grpc",
        "microservices", "websockets",
    ],
    "databases": [
        "mysql", "postgresql", "mongodb", "sqlite", "oracle", "sql server", "redis",
        "cassandra", "elasticsearch", "dynamodb", "firebase", "neo4j",
    ],
    "cloud_devops": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible", "jenkins",
        "ci/cd", "github actions", "linux", "nginx", "git", "helm", "prometheus", "grafana",
    ],
    "data_ai": [
        "machine learning", "deep learning", "nlp", "computer vision", "tensorflow", "pytorch",
        "keras", "scikit-learn", "pandas", "numpy", "matplotlib", "seaborn", "spark", "hadoop",
        "tableau", "power bi", "excel", "statistics", "data analysis", "llm", "transformers",
        "opencv", "airflow", "etl",
    ],
    "mobile": [
        "android", "ios", "react native", "flutter", "xamarin", "swiftui", "jetpack compose",
    ],
    "testing": [
        "unit testing", "selenium", "cypress", "jest", "pytest", "junit", "playwright",
        "manual testing", "automation testing", "postman", "jmeter", "appium",
    ],
    "project_management": [
        "agile", "scrum", "kanban", "jira", "confluence", "project management",
        "stakeholder management", "product management", "risk management",
    ],
    "design": [
        "figma", "adobe xd", "photoshop", "illustrator", "ui design", "ux design", "sketch",
        "wireframing",
    ],
    "security": [
        "cybersecurity", "penetration testing", "owasp", "oauth", "jwt", "encryption",
        "network security", "siem",
    ],
    "soft_skills": [
        "communication", "leadership", "teamwork", "problem solving",
    ],
}

# Alternative spellings and abbreviations -> canonical form.
SKILL_ALIASES = {
    "js": "javascript", "ecmascript": "javascript", "es6": "javascript",
    "ts": "typescript",
    "py": "python", "python3": "python",
    "golang": "go",
    "cpp": "c++", "csharp": "c#",
    "react": "react.js", "reactjs": "react.js",
    "angularjs": "angular",
    "vue": "vue.js", "vuejs": "vue.js",
    "nextjs": "next.js",
    "tailwind": "tailwind css", "tailwindcss": "tailwind css",
    "node": "node.js", "nodejs": "node.js",
    "express": "express.js", "expressjs": "express.js",
    "springboot": "spring boot",
    "dotnet": ".net",
    "rails": "ruby on rails", "ror": "ruby on rails",
    "rest api": "rest", "restful": "rest", "rest apis": "rest", "restful api": "rest",
    "postgres": "postgresql", "psql": "postgresql",
    "mongo": "mongodb",
    "mssql": "sql server", "ms sql": "sql server",
    "amazon web services": "aws", "google cloud": "gcp", "google cloud platform": "gcp",
    "microsoft azure": "azure",
    "k8s": "kubernetes",
    "ci cd": "ci/cd", "cicd": "ci/cd", "continuous integration": "ci/cd",
    "github": "git", "gitlab": "git",
    "ml": "machine learning", "dl": "deep learning",
    "natural language processing": "nlp",
    "cv": "computer vision",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn",
    "pyspark": "spark", "apache spark": "spark",
    "powerbi": "power bi", "ms excel": "excel",
    "large language models": "llm", "llms": "llm", "generative ai": "llm",
    "huggingface": "transformers", "hugging face": "transformers",
    "rn": "react native",
    "qa automation": "automation testing", "test automation": "automation testing",
    "ui": "ui design", "ux": "ux design", "ui/ux": "ux design",
    "pentesting": "penetration testing",
    "json web token": "jwt",
}

ALL_SKILLS = sorted({s for group in SKILL_DICTIONARY.values() for s in group})

# Very short or common words are detected only through their full spelling,
# never through the alias, so that e.g. "cv" (a resume) is not "computer vision".
_AMBIGUOUS_ALIASES = {"cv", "ui", "ux", "rn", "ts", "py", "ml", "dl"}
# Single letters are detected only when written as a language ("C programming").
_SINGLE_LETTER = {"c": r"\bc\s*(?:programming|language)\b|\bc\s*/\s*c\+\+",
                  "r": r"\br\s*(?:programming|language|studio)\b"}


def canonical(skill):
    """Return the canonical form of a skill name."""
    s = " ".join(skill.strip().lower().split())
    return SKILL_ALIASES.get(s, s)


def _pattern(term):
    # Word-boundary match that also works for terms with symbols (c++, node.js, ci/cd),
    # so that "java" is not found inside "javascript".
    escaped = re.escape(term).replace(r"\ ", r"[\s\-]+")
    return re.compile(r"(?<![a-z0-9+#])" + escaped + r"(?![a-z0-9+#]|\.[a-z0-9])", re.IGNORECASE)


_PATTERNS = {}


def _patterns_for(skill):
    if skill not in _PATTERNS:
        if skill in _SINGLE_LETTER:
            pats = [re.compile(_SINGLE_LETTER[skill], re.IGNORECASE)]
        else:
            terms = {skill} | {a for a, c in SKILL_ALIASES.items() if c == skill and a not in _AMBIGUOUS_ALIASES}
            pats = [_pattern(t) for t in sorted(terms, key=len, reverse=True)]
        _PATTERNS[skill] = pats
    return _PATTERNS[skill]


def mentions(text, skill):
    """True if `text` mentions `skill` (canonical form) or one of its aliases."""
    return any(p.search(text) for p in _patterns_for(canonical(skill)))


def extract_skills(text):
    """Return the sorted list of dictionary skills mentioned in `text`."""
    return sorted(s for s in ALL_SKILLS if mentions(text, s))

"""Years of experience and education level extraction (Module 6, signal 3)."""
import re

_NUM = r"(\d{1,2}(?:\.\d)?)"
_EXPERIENCE_PATTERNS = [
    re.compile(_NUM + r"\s*\+?\s*(?:years?|yrs?)\b(?:\s+of)?(?:\s+\w+){0,3}?\s+(?:experience|exp)\b", re.I),
    re.compile(r"(?:experience|exp)\s*(?:of|:|-)?\s*" + _NUM + r"\s*\+?\s*(?:years?|yrs?)\b", re.I),
    re.compile(_NUM + r"\s*\+\s*(?:years?|yrs?)\b", re.I),
    re.compile(_NUM + r"\s*(?:years?|yrs?)\s+(?:in|as|with|working)\b", re.I),
]

# Minimum years usually expected for each job level.
LEVEL_MIN_YEARS = {"entry": 0, "mid": 2, "senior": 5, "lead": 8}

_EDUCATION = [
    ("PhD", r"\bph\.?\s?d\b|\bdoctorate\b"),
    ("Master's", r"\bmaster'?s?\b|\bm\.?\s?tech\b|\bm\.?\s?sc\b|\bmba\b|\bm\.?\s?e\b(?=\s|\.|,)|\bmca\b|\bm\.?s\.?\b(?=\s+in\b)"),
    ("Bachelor's", r"\bbachelor'?s?\b|\bb\.?\s?tech\b|\bb\.?\s?sc\b|\bb\.?\s?e\b(?=\s|\.|,)|\bbca\b|\bb\.?\s?com\b|\bb\.?a\.?\b(?=\s+in\b)"),
    ("Associate", r"\bassociate'?s? degree\b|\bdiploma\b"),
    ("High School", r"\bhigh school\b|\bhsc\b|\bssc\b|\b12th\b"),
]


def years_of_experience(text):
    """Largest number of years stated in the text, or None if none is stated."""
    found = []
    for pattern in _EXPERIENCE_PATTERNS:
        for match in pattern.finditer(text):
            value = float(match.group(1))
            if 0 <= value <= 50:
                found.append(value)
    return max(found) if found else None


def experience_fit(years, level):
    """Percentage fit of `years` for a job `level`; None when years are unknown."""
    if years is None:
        return None
    minimum = LEVEL_MIN_YEARS.get(level, 0)
    if minimum == 0 or years >= minimum:
        return 100.0
    return round(years / minimum * 100, 1)


def education_level(text):
    """Highest education level mentioned, or None. Shown for information only."""
    for label, pattern in _EDUCATION:
        if re.search(pattern, text, re.I):
            return label
    return None

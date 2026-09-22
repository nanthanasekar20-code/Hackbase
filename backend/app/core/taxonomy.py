"""
Fixed domain/field taxonomy for HackBase, plus lightweight heuristic
mappers used during the cleaning/normalization stage of the ingestion
pipeline (see app/ingestion/clean.py).

These mappers are intentionally rule-based (keyword lookups), not
LLM-based: they run for free, offline, on every ingestion, and give every
problem statement a reasonable first-pass domain/technology tag even
before the Gemini enrichment pass (Phase 2) exists. Phase 2 can later
refine or override these tags — it is not required for them to work.
"""

from __future__ import annotations

import re

# The fixed set of fields/domains users can browse HackBase by. Keep this
# list in sync with anything the frontend hardcodes as filter options.
DOMAINS = [
    "AI/ML",
    "Web Development",
    "Mobile Development",
    "Cybersecurity",
    "IoT",
    "Healthcare",
    "FinTech",
    "Agriculture",
    "EdTech",
    "Sustainability & Climate",
    "Blockchain & Web3",
    "Data Science & Analytics",
]

# Raw "theme"/"category" strings seen in real source data (SIH themes,
# Devpost tracks, campus-hackathon section headers) mapped to one or more
# taxonomy domains. Matching is case-insensitive, word-boundary-aware
# (see _theme_pattern below) — plain substring matching was tried first and
# produced real false positives (e.g. the keyword "hospital" matching inside
# "hospitality services"), so keywords match as whole words/phrases unless
# explicitly listed in PREFIX_KEYWORDS. Tried in order — first match wins
# for the primary domain, but a record can carry more than one tag if
# multiple keys hit.
THEME_KEYWORDS: dict[str, list[str]] = {
    "AI/ML": [
        "artificial intelligence", "machine learning", "ai/ml", "ai-ml", "ai",
        "deep learning", "computer vision", "nlp", "predictive model", "neuro ai",
    ],
    "Healthcare": [
        "medtech", "biotech", "healthtech", "health", "medical", "clinical",
        "hospital", "patient", "therapy", "ayush", "thalassemia",
        # NOTE: intentionally no standalone "disease" keyword — it false-
        # matched non-human contexts like "crop disease" / "plant disease"
        # / "livestock disease", tagging agriculture problems as Healthcare
        # (caught via a real /api/v1/plan run pulling in an HL7 FHIR
        # resource for a crop-disease-detection problem). Human-disease
        # problem statements are still caught by "medical"/"clinical"/
        # "patient"/"hospital"/etc. above.
    ],
    "Agriculture": [
        "agri", "farm", "crop", "rural development", "foodtech", "livestock",
        "fertilizer", "irrigation",
    ],
    "FinTech": [
        "fintech", "financial", "finance", "fraud detection", "payment",
        "banking", "cryptocurrency transaction", "insurance",
    ],
    "Cybersecurity": [
        "cybersecurity", "cyber security", "forensic", "encryption", "firewall",
        "vulnerability", "malware", "ddos", "de-anonymiz", "redaction", "tor network",
        "fuzzing", "data recovery", "pii detection",
    ],
    "IoT": [
        "iot", "internet of things", "sensor", "sensors", "drone", "embedded system",
        "arduino", "raspberry pi", "wearable device", "smart bands",
    ],
    "Blockchain & Web3": [
        "blockchain", "web3", "nft", "distributed ledger", "smart contract",
        "cryptocurrency", "decentralized",
    ],
    "Sustainability & Climate": [
        "clean & green", "clean and green", "sustainab", "renewable", "solar",
        "climate", "carbon", "water", "waste management", "energy", "environment",
        "air quality", "aqi",
    ],
    "EdTech": [
        "smart education", "edtech", "e-learning", "learning app",
        "faculty", "alumni", "academic", "curriculum", "classroom",
        "school education", "higher education",
    ],
    "Data Science & Analytics": [
        "data analytics", "data science", "big data", "dashboard", "analytics",
        "data visualization", "predictive", "forecasting",
    ],
    "Web Development": [
        "web application", "web portal", "website", "web platform",
    ],
    "Mobile Development": [
        "mobile app", "mobile application", "android", "ios app",
    ],
}

# Curated technology/skill keyword list, matched case-insensitively as
# whole words/phrases against a problem's title + description. Kept small
# and high-signal on purpose — this is a heuristic first pass, not an
# exhaustive tech dictionary.
TECH_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "React", "Next.js", "Node.js",
    "Flutter", "Android", "iOS", "Java", "Kotlin", "Swift",
    "TensorFlow", "PyTorch", "scikit-learn", "OpenCV", "NLP", "LLM",
    "Machine Learning", "Deep Learning", "Computer Vision",
    "Blockchain", "Solidity", "Smart Contracts",
    "IoT", "Arduino", "Raspberry Pi", "Sensors",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes",
    "PostgreSQL", "MongoDB", "MySQL", "Firebase",
    "GIS", "Satellite Imagery", "Remote Sensing",
    "Cloud Computing", "APIs", "REST API",
    "Cybersecurity", "Encryption", "Penetration Testing",
    "Data Analytics", "Power BI", "Tableau",
    "AR/VR", "3D Modeling",
]

# A few canonical tech keywords are written very differently in real
# problem statements than the compound label used as their catalog key
# (see app.core.resource_catalog.TECH_RESOURCES) — nobody writes "AR/VR"
# verbatim; they say "AR", "VR", "augmented reality". Real bug found via a
# real saved plan: an AR-based problem statement mentioning "AR" and
# "augmented reality" repeatedly matched zero technologies, because the
# only pattern tried was the literal string "AR/VR". Each alias here is
# tried in addition to (not instead of) the canonical keyword itself.
TECH_KEYWORD_ALIASES: dict[str, list[str]] = {
    "AR/VR": ["AR", "VR", "Augmented Reality", "Virtual Reality", "Mixed Reality", "XR"],
}


def _tech_pattern(surface_form: str) -> re.Pattern:
    escaped = re.escape(surface_form).replace(r"\ ", r"[\s\-]+")
    return re.compile(r"(?<![\w])" + escaped + r"(?![\w])", re.IGNORECASE)


_TECH_PATTERNS = [
    (kw, [_tech_pattern(form) for form in [kw, *TECH_KEYWORD_ALIASES.get(kw, [])]])
    for kw in TECH_KEYWORDS
]

# Keywords that are intentionally truncated word-stems (so they deliberately
# match multiple word-forms, e.g. "agri" -> agriculture/agri-tech/agri-food,
# "sustainab" -> sustainable/sustainability). These keep a left word-boundary
# but skip the right one. Every other keyword requires both boundaries, so a
# complete word like "hospital" cannot match inside an unrelated word like
# "hospitality".
PREFIX_KEYWORDS = {"agri", "sustainab", "de-anonymiz"}


def _theme_pattern(kw: str) -> re.Pattern:
    escaped = re.escape(kw).replace(r"\ ", r"[\s\-]+")
    right_boundary = "" if kw in PREFIX_KEYWORDS else r"(?![\w])"
    return re.compile(r"(?<![\w])" + escaped + right_boundary, re.IGNORECASE)


_THEME_PATTERNS: dict[str, list[tuple[str, re.Pattern]]] = {
    domain: [(kw, _theme_pattern(kw)) for kw in keywords]
    for domain, keywords in THEME_KEYWORDS.items()
}


def map_domains(*texts: str) -> list[str]:
    """
    Heuristically tag one or more free-text fields (theme, description)
    with taxonomy domains. Returns a de-duplicated, order-preserving list;
    empty if nothing matched (callers should treat that as "uncategorized"
    rather than guessing).
    """
    haystack = " ".join(t for t in texts if t)
    matched: list[str] = []
    for domain, patterns in _THEME_PATTERNS.items():
        if any(pattern.search(haystack) for _, pattern in patterns):
            matched.append(domain)
    return matched


def extract_technologies(*texts: str) -> list[str]:
    """Heuristically extract mentioned technologies/skills from free text."""
    haystack = " ".join(t for t in texts if t)
    found = []
    for kw, patterns in _TECH_PATTERNS:
        if any(pattern.search(haystack) for pattern in patterns):
            found.append(kw)
    return found

"""
Curated resource catalog for the Resource Agent.

Per the Phase 1 planning decision, the Resource Agent does NOT call a
search API or an LLM — it's a curated, keyword-based lookup. This module
holds the actual curated data: real, well-known, stable documentation
sites, GitHub orgs/tools, and dataset hubs, keyed by taxonomy domain and by
technology (the same keys app.core.taxonomy already tags problems with).

Every URL here points at an official/canonical resource homepage (docs
site, project homepage, dataset hub) rather than a deep specific article —
homepages for established projects change far less often than individual
pages, which keeps this catalog low-maintenance and reduces the chance of
a link going stale.
"""

from __future__ import annotations

# type must match app.schemas.plan.Resource's Literal["docs", "repo",
# "tutorial", "dataset", "tool", "api"].

DOMAIN_RESOURCES: dict[str, list[dict]] = {
    "AI/ML": [
        {"title": "TensorFlow documentation", "url": "https://www.tensorflow.org/learn", "type": "docs"},
        {"title": "PyTorch tutorials", "url": "https://pytorch.org/tutorials/", "type": "tutorial"},
        {"title": "Kaggle Learn (free ML courses)", "url": "https://www.kaggle.com/learn", "type": "tutorial"},
    ],
    "Web Development": [
        {"title": "MDN Web Docs", "url": "https://developer.mozilla.org/en-US/docs/Web", "type": "docs"},
        {"title": "React documentation", "url": "https://react.dev/learn", "type": "docs"},
    ],
    "Mobile Development": [
        {"title": "Flutter documentation", "url": "https://docs.flutter.dev/", "type": "docs"},
        {"title": "Android developer documentation", "url": "https://developer.android.com/docs", "type": "docs"},
    ],
    "Cybersecurity": [
        {"title": "OWASP Top 10", "url": "https://owasp.org/www-project-top-ten/", "type": "docs"},
        {"title": "NIST Cybersecurity Framework", "url": "https://www.nist.gov/cyberframework", "type": "docs"},
    ],
    "IoT": [
        {"title": "Arduino documentation", "url": "https://docs.arduino.cc/", "type": "docs"},
        {"title": "Raspberry Pi documentation", "url": "https://www.raspberrypi.com/documentation/", "type": "docs"},
    ],
    "Healthcare": [
        {"title": "HL7 FHIR standard (health data interoperability)", "url": "https://hl7.org/fhir/", "type": "docs"},
        {"title": "WHO health data & digital health resources", "url": "https://www.who.int/data", "type": "dataset"},
    ],
    "FinTech": [
        {"title": "Stripe API documentation", "url": "https://stripe.com/docs", "type": "api"},
        {"title": "Plaid API documentation (banking data)", "url": "https://plaid.com/docs/", "type": "api"},
    ],
    "Agriculture": [
        {"title": "FAO open agricultural data", "url": "https://www.fao.org/faostat/", "type": "dataset"},
        {"title": "data.gov.in agriculture datasets", "url": "https://www.data.gov.in/sector/agriculture", "type": "dataset"},
    ],
    "EdTech": [
        {"title": "Open edX (open-source learning platform)", "url": "https://openedx.org/", "type": "tool"},
        {"title": "Google for Education developer resources", "url": "https://edu.google.com/", "type": "docs"},
    ],
    "Sustainability & Climate": [
        {"title": "NASA Earthdata (climate & earth observation data)", "url": "https://www.earthdata.nasa.gov/", "type": "dataset"},
        {"title": "Global Carbon Atlas", "url": "https://globalcarbonatlas.org/", "type": "dataset"},
    ],
    "Blockchain & Web3": [
        {"title": "Ethereum developer documentation", "url": "https://ethereum.org/en/developers/docs/", "type": "docs"},
        {"title": "Solidity documentation", "url": "https://docs.soliditylang.org/", "type": "docs"},
    ],
    "Data Science & Analytics": [
        {"title": "Kaggle datasets & notebooks", "url": "https://www.kaggle.com/", "type": "dataset"},
        {"title": "pandas documentation", "url": "https://pandas.pydata.org/docs/", "type": "docs"},
    ],
}

TECH_RESOURCES: dict[str, dict] = {
    "Python": {"title": "Python documentation", "url": "https://docs.python.org/3/", "type": "docs"},
    "JavaScript": {"title": "JavaScript reference (MDN)", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript", "type": "docs"},
    "TypeScript": {"title": "TypeScript documentation", "url": "https://www.typescriptlang.org/docs/", "type": "docs"},
    "React": {"title": "React documentation", "url": "https://react.dev/learn", "type": "docs"},
    "Next.js": {"title": "Next.js documentation", "url": "https://nextjs.org/docs", "type": "docs"},
    "Node.js": {"title": "Node.js documentation", "url": "https://nodejs.org/en/docs", "type": "docs"},
    "Flutter": {"title": "Flutter documentation", "url": "https://docs.flutter.dev/", "type": "docs"},
    "Android": {"title": "Android developer documentation", "url": "https://developer.android.com/docs", "type": "docs"},
    "iOS": {"title": "Apple developer documentation", "url": "https://developer.apple.com/documentation/", "type": "docs"},
    "Java": {"title": "Java SE documentation", "url": "https://docs.oracle.com/en/java/", "type": "docs"},
    "Kotlin": {"title": "Kotlin documentation", "url": "https://kotlinlang.org/docs/home.html", "type": "docs"},
    "Swift": {"title": "Swift documentation", "url": "https://www.swift.org/documentation/", "type": "docs"},
    "TensorFlow": {"title": "TensorFlow documentation", "url": "https://www.tensorflow.org/learn", "type": "docs"},
    "PyTorch": {"title": "PyTorch documentation", "url": "https://pytorch.org/docs/stable/index.html", "type": "docs"},
    "scikit-learn": {"title": "scikit-learn documentation", "url": "https://scikit-learn.org/stable/", "type": "docs"},
    "OpenCV": {"title": "OpenCV documentation", "url": "https://docs.opencv.org/", "type": "docs"},
    "NLP": {"title": "Hugging Face Transformers documentation", "url": "https://huggingface.co/docs/transformers", "type": "docs"},
    "LLM": {"title": "Google AI (Gemini API) documentation", "url": "https://ai.google.dev/gemini-api/docs", "type": "docs"},
    "Blockchain": {"title": "Ethereum developer documentation", "url": "https://ethereum.org/en/developers/docs/", "type": "docs"},
    "Solidity": {"title": "Solidity documentation", "url": "https://docs.soliditylang.org/", "type": "docs"},
    "Smart Contracts": {"title": "Ethereum smart contracts overview", "url": "https://ethereum.org/en/developers/docs/smart-contracts/", "type": "docs"},
    "IoT": {"title": "Arduino documentation", "url": "https://docs.arduino.cc/", "type": "docs"},
    "Arduino": {"title": "Arduino documentation", "url": "https://docs.arduino.cc/", "type": "docs"},
    "Raspberry Pi": {"title": "Raspberry Pi documentation", "url": "https://www.raspberrypi.com/documentation/", "type": "docs"},
    "AWS": {"title": "AWS documentation", "url": "https://docs.aws.amazon.com/", "type": "docs"},
    "Azure": {"title": "Microsoft Azure documentation", "url": "https://learn.microsoft.com/azure/", "type": "docs"},
    "GCP": {"title": "Google Cloud documentation", "url": "https://cloud.google.com/docs", "type": "docs"},
    "Docker": {"title": "Docker documentation", "url": "https://docs.docker.com/", "type": "docs"},
    "Kubernetes": {"title": "Kubernetes documentation", "url": "https://kubernetes.io/docs/home/", "type": "docs"},
    "PostgreSQL": {"title": "PostgreSQL documentation", "url": "https://www.postgresql.org/docs/", "type": "docs"},
    "MongoDB": {"title": "MongoDB documentation", "url": "https://www.mongodb.com/docs/", "type": "docs"},
    "MySQL": {"title": "MySQL documentation", "url": "https://dev.mysql.com/doc/", "type": "docs"},
    "Firebase": {"title": "Firebase documentation", "url": "https://firebase.google.com/docs", "type": "docs"},
    "Cybersecurity": {"title": "OWASP Top 10", "url": "https://owasp.org/www-project-top-ten/", "type": "docs"},
    "Encryption": {"title": "OWASP Cryptographic Storage Cheat Sheet", "url": "https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html", "type": "docs"},
    "Penetration Testing": {"title": "OWASP Testing Guide", "url": "https://owasp.org/www-project-web-security-testing-guide/", "type": "docs"},
    "Data Analytics": {"title": "pandas documentation", "url": "https://pandas.pydata.org/docs/", "type": "docs"},
    "Power BI": {"title": "Power BI documentation", "url": "https://learn.microsoft.com/power-bi/", "type": "docs"},
    "Tableau": {"title": "Tableau help documentation", "url": "https://help.tableau.com/", "type": "docs"},
    "AR/VR": {"title": "Unity learn (AR/VR development)", "url": "https://learn.unity.com/", "type": "tutorial"},
}

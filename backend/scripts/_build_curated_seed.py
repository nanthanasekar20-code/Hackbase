"""
One-off helper (not part of the runtime pipeline) used to hand-assemble
data/seed/curated_supplementary.json from real, publicly published
hackathon problem statements that this project's automated scrapers
cannot yet reach (Devpost hackathon pages render challenge details
client-side; a campus hackathon's problem-statement PDF isn't something a
generic scraper should target). Every record here reflects an actual,
real, currently-public hackathon listing — titles and descriptions are
faithful summaries of the primary source, not invented. Each keeps its
source URL for verification.

Run once: python scripts/_build_curated_seed.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

FETCHED_AT = datetime.now(timezone.utc).isoformat()

MITS_URL = "https://web.mitsgwalior.in/images/2025/feb/Problem%20Statements-CC-2025.pdf"
MITS_HACKATHON = "Code Coalescence 2025 - MITS-DU Gwalior"

# Source: Code Coalescence 2025 problem-statement PDF, MITS-DU Gwalior
# (institute-level hackathon). Theme = the PDF's own section headings.
MITS_RECORDS = [
    ("CC1", "Agriculture, FoodTech & Rural Development", "Mobile App for Direct Market Access for Farmers",
     "Create a mobile platform connecting farmers directly with consumers and retailers, with product "
     "listing, price negotiation, and transaction management to eliminate intermediaries."),
    ("CC2", "Agriculture, FoodTech & Rural Development", "AI-Driven Crop Disease Prediction and Management System",
     "Develop an AI system that analyzes crop images and environmental data to predict disease outbreaks, "
     "providing actionable insights and treatment recommendations via mobile/web apps."),
    ("CC3", "Agriculture, FoodTech & Rural Development", "Sustainable Fertilizer Usage Optimizer for Higher Yield",
     "Build a data-driven application recommending optimal fertilizer types and quantities based on soil "
     "health, crops, and weather patterns, promoting sustainable farming while enhancing yields."),
    ("CC4", "Agriculture, FoodTech & Rural Development", "Assured Contract Farming System for Stable Market Access",
     "Develop an online marketplace facilitating contract farming agreements between farmers and buyers, "
     "with transparent communication, secure contracts, and timely payment processing."),
    ("CC5", "Agriculture, FoodTech & Rural Development", "AI-ML Models for Predicting Agri-Horticultural Commodity Prices",
     "Create predictive models forecasting prices of pulses and vegetables using AI/ML techniques (e.g. "
     "ARIMA) to aid government decisions on buffer stock releases and market interventions."),
    ("CC6", "Agriculture, FoodTech & Rural Development", "Farmers Disease Diagnostic/Reporting Portal - AI-Based Mobile Portal",
     "Build an AI-powered mobile portal enabling farmers to diagnose and report livestock and crop "
     "diseases, integrating with NDLM to provide diagnoses and alert veterinarians."),
    ("CC8", "Blockchain & Cybersecurity", "DDoS Protection System for Cloud: Architecture and Tool",
     "Design cloud architecture and a tool that detects and protects against distributed denial-of-service "
     "attacks, demonstrating automatic attack detection and recovery."),
    ("CC9", "Blockchain & Cybersecurity", "PII Detection in Documents and Data",
     "Create an application that identifies government-issued personally identifiable information embedded "
     "in documents, with detection, alerting, and optional redaction/masking of sensitive data."),
    ("CC12", "Blockchain & Cybersecurity", "OEM Equipment Vulnerability Web-Scraping Tool",
     "Develop an automated tool that scrapes OEM websites for Critical/High severity vulnerabilities and "
     "emails vulnerability information with mitigation strategies to predefined recipients."),
    ("CC13", "Blockchain & Cybersecurity", "Real-Time Cyber Incident Feed Generator",
     "Build a framework collecting and analyzing cyber incident activity in Indian cyberspace using machine "
     "learning, generating sector- and APT-level insights and visualizations."),
    ("CC14", "Blockchain & Cybersecurity", "RE-DACT: Redaction and Anonymization Tool",
     "Build an NLP-based redaction tool that masks sensitive data while maintaining structural integrity, "
     "with gradational redaction levels and synthetic data generation."),
    ("CC15", "Blockchain & Cybersecurity", "CIS Benchmark Audit Scripts for Windows 11 and Linux",
     "Develop automated audit scripts checking compliance with CIS benchmarks for Windows 11 and Linux, "
     "with GUI-based reporting and customizable organizational policies."),
    ("CC17", "Blockchain & Cybersecurity", "Centralized Application-Context Aware Firewall",
     "Develop an endpoint firewall that identifies and restricts application access to external networks "
     "with granular domain/IP/protocol control, a central management console, and AI/ML anomaly detection."),
    ("CC18", "Blockchain & Cybersecurity", "Cyber Triage Tool for Digital Forensic Investigation",
     "Design a forensics tool that streamlines evidence importing, automated analysis, and reporting, "
     "including RAW image scanning, IOC identification, and AI/ML-based anomaly detection."),
    ("CC22", "Blockchain & Cybersecurity", "Fake Social Media Account Detection",
     "Build tools that identify fake profiles on Facebook, Instagram, Twitter and similar platforms, with "
     "detection, reporting, and coordination workflows for account suspension."),
    ("CC24", "Clean & Green Technology", "Technological Solutions for AQI Value Capturing",
     "Develop mobile/alternative station solutions (potentially drone-mounted sensors) for measuring Air "
     "Quality Index and pollution parameters in real time."),
    ("CC25", "Clean & Green Technology", "Digital Technology for Water Footprint Calculation",
     "Create an app or website that calculates water footprints for agricultural products using AI and Big "
     "Data, including camera-based scanning (similar to Google Lens) and local-language support."),
    ("CC26", "Clean & Green Technology", "Digital Knowledge Sharing Platform for Water Efficiency",
     "Develop a wiki-style platform sharing water-efficient techniques for agriculture and conservation, "
     "with peer-reviewed articles, forums, videos, and mobile accessibility."),
    ("CC28", "Clean & Green Technology", "Downscaling Satellite Air Quality Maps using AI/ML",
     "Develop an AI/ML model that generates fine spatial-resolution air quality maps from coarse satellite "
     "data, validated against independent ground data using Python-based ML libraries."),
    ("CC30", "Clean & Green Technology", "Swachhta and LiFE Dashboard with AI Image Processing",
     "Develop an AI-powered dashboard monitoring cleanliness and environmental practices in post offices, "
     "with camera-based monitoring, alert generation, and centralized surveillance."),
    ("CC33", "MedTech / BioTech / HealthTech", "Virtual Herbal Garden for AYUSH Education",
     "Create an interactive 3D virtual garden showcasing medicinal plants used in AYUSH systems, with "
     "interactive 3D models, plant information, multimedia content, and guided tours."),
    ("CC34", "MedTech / BioTech / HealthTech", "Queuing Models for Hospital OPDs and Bed Management",
     "Develop a hospital solution managing patient queuing, bed availability, and admissions, integrating "
     "medicine dispensation and inventory management modules at city-wide scale."),
    ("CC35", "MedTech / BioTech / HealthTech", "Online Testing and Monitoring of Medicine Quality",
     "Build a module for testing and monitoring medicine/consumable quality in hospitals that ensures "
     "compliance and automatically rejects low-quality supplies without manual intervention."),
    ("CC36", "MedTech / BioTech / HealthTech", "Health Data Information & Management System (HDIMS) Mobile App",
     "Develop a mobile app enabling hospitals to enter and update health data viewable by administrators, "
     "supporting performance tracking for health schemes and policy formulation."),
    ("CC37", "MedTech / BioTech / HealthTech", "Drug Inventory and Supply Chain Tracking System",
     "Create a system ensuring the right quantity of the right product reaches the right place at the "
     "right time and condition, with dashboard monitoring, vendor tracking, and consumption analysis."),
    ("CC39", "MedTech / BioTech / HealthTech", "Software for Speech Language Therapy Clinical Services",
     "Develop software digitizing speech-language therapy services end-to-end, from patient allocation "
     "through progress evaluation, with therapy plan management and supervisor review workflows."),
    ("CC41", "Renewable / Sustainable Energy", "Carbon Footprint Quantification Tool for Indian Coal Mines",
     "Create a web app helping coal mines quantify carbon emissions and explore carbon-neutrality pathways, "
     "with activity-wise emission estimation, carbon sink analysis, and renewable-energy options."),
    ("CC42", "Renewable / Sustainable Energy", "Building Integrated Photovoltaic (BIPV) Potential Assessment",
     "Develop an interactive application assessing BIPV potential using LOD-1 3D city models from satellite "
     "data, simulating shadows and calculating incident solar energy on vertical surfaces."),
    ("CC44", "Smart Education", "Research, IPR, and Start-up Monitoring for Gujarat State",
     "Build a web app unifying research project tracking, IPR management, innovation monitoring, and "
     "startup support, with a centralized data repository and collaboration tools."),
    ("CC45", "Smart Education", "Alumni Association Platform for University/Institute",
     "Develop web and mobile apps facilitating alumni networking, donations, job posting, and success "
     "tracking, with registration, secure donations, an alumni directory, and event management."),
    ("CC46", "Smart Education", "Learning App for Deaf and Mute Students with Sign Language Converter",
     "Create a mobile app teaching deaf and mute students via Indian Sign Language, with alphabet/number "
     "instruction, word/sentence translation, and speech-to-sign conversion."),
    ("CC48", "Smart Education", "Publications Summary Generator for Faculty Profile Building",
     "Develop a solution that crawls academic databases (Google Scholar, DBLP) to generate publication "
     "summaries, with customized year-wise queries and multi-format export."),
    ("CC49", "Smart Education", "Learning Path Dashboard for Skill Enhancement",
     "Create a dashboard enabling instructors to build learning paths with resources and track learner "
     "progress continuously, including reading statistics and mixed-media resources."),
    ("CC50", "Smart Education", "Smart Competency Diagnostic and Candidate Profile Score Calculator",
     "Build an employment platform with AI-powered job matching and skill-gap analysis, including "
     "competency assessments, training recommendations, and resume tooling."),
]

DEVPOST_RECORDS = [
    dict(
        title="Blood Donation and Transfusion Management for Thalassemia Patients",
        hackathon_name="AI for Good Hackathon",
        url="https://ai-for-good.devpost.com/",
        theme="Healthcare",
        description=(
            "Build an AI-driven system supporting Blood Warriors (a Thalassemia patient advocacy non-profit) "
            "with real-time systems connecting patients to regular blood donors, predictive models for donor "
            "availability, tracking for recurring donations, and integration with platforms like e-RaktKosh "
            "and Blood Bridge."
        ),
    ),
    dict(
        title="Access to Care and Support Networks for Thalassemia Patients",
        hackathon_name="AI for Good Hackathon",
        url="https://ai-for-good.devpost.com/",
        theme="Healthcare",
        description=(
            "Design AI-supported solutions improving communication between Thalassemia patients and "
            "healthcare providers, enhancing patient education on disease management, and addressing data "
            "privacy/security for protecting patient and donor information."
        ),
    ),
    dict(
        title="AI Solutions for Real-World Clinical Challenges",
        hackathon_name="Healthcare Hackathon with AI (H2AI)",
        url="https://georgetown-h2ai.devpost.com/",
        theme="Healthcare",
        description=(
            "Develop an AI solution addressing a genuine clinical problem end-to-end — technical "
            "implementation plus a credible go-to-market or adoption path — spanning areas like neuro AI "
            "diagnostics, patient-safety tooling, or health entrepreneurship."
        ),
    ),
    dict(
        title="Fraud Detection Using Device Intelligence",
        hackathon_name="DeveloperWeek 2025 Hackathon",
        url="https://developerweek-2025-hackathon.devpost.com/",
        theme="FinTech / Security",
        description=(
            "Build a fraud detection system using a device-intelligence platform's visitor-ID and smart "
            "signals to track multiple visitor IDs linked to a single data point (and vice versa), exposing "
            "coordinated fraud across e-commerce or social platforms."
        ),
    ),
    dict(
        title="Solve a UN Sustainable Development Goal with a Low-Code Platform",
        hackathon_name="DeveloperWeek 2025 Hackathon",
        url="https://developerweek-2025-hackathon.devpost.com/",
        theme="Sustainability",
        description=(
            "Address one of the UN's 17 Sustainable Development Goals using a low-code application platform "
            "and database, prioritizing innovation, implementation quality, and meaningful social impact."
        ),
    ),
    dict(
        title="Communication-Driven User Experiences with a Programmable API",
        hackathon_name="DeveloperWeek 2025 Hackathon",
        url="https://developerweek-2025-hackathon.devpost.com/",
        theme="Web Development",
        description=(
            "Use a communications API platform's messaging, voice, and interactive tools to build a "
            "personalized, anticipatory user experience — for example smart notifications or interactive "
            "voice features embedded in an app."
        ),
    ),
    dict(
        title="Cold-Chain Monitoring to Protect Live Animal Cargo",
        hackathon_name="DeveloperWeek 2025 Hackathon",
        url="https://developerweek-2025-hackathon.devpost.com/",
        theme="IoT / Logistics",
        description=(
            "Build real-time monitoring on a asset-tracking platform to prevent live animal cargo from being "
            "accidentally placed in cold storage during air transport, using geofence alerts and (as a "
            "stretch goal) text-to-speech notifications."
        ),
    ),
    dict(
        title="Predictive ETA Estimator for Temperature-Sensitive Pharmaceutical Shipments",
        hackathon_name="DeveloperWeek 2025 Hackathon",
        url="https://developerweek-2025-hackathon.devpost.com/",
        theme="IoT / Logistics",
        description=(
            "Develop an ETA predictor for temperature-sensitive medication deliveries using live GPS "
            "tracking data, with automated arrival notifications and (as a stretch goal) map-based route "
            "visualization."
        ),
    ),
    dict(
        title="Medical Technology and Patient Accessibility Innovation",
        hackathon_name="Hacktech by Caltech 2025",
        url="https://hacktech2025.devpost.com/",
        theme="Healthcare",
        description=(
            "Develop solutions advancing medical technology, improving accessibility for patients with "
            "disabilities or limited resources, or advancing biotechnology research with a real-world "
            "application."
        ),
    ),
    dict(
        title="FinTech Tools, Fraud Detection, and Predictive Modeling",
        hackathon_name="Hacktech by Caltech 2025",
        url="https://hacktech2025.devpost.com/",
        theme="FinTech",
        description=(
            "Create financial technology applications — fraud detection systems or predictive models — "
            "that address real-world financial challenges such as risk assessment or transaction monitoring."
        ),
    ),
    dict(
        title="Climate and Renewable Energy Technology",
        hackathon_name="Hacktech by Caltech 2025",
        url="https://hacktech2025.devpost.com/",
        theme="Sustainability",
        description=(
            "Build technology-based approaches to environmental problems — renewable energy innovations or "
            "eco-friendly practices — that demonstrate feasible, measurable real-world impact."
        ),
    ),
    dict(
        title="Wastewater Reuse Tracking Solutions",
        hackathon_name="Global Blockchain Hackathon for Clean Water",
        url="https://wrc-hackathon.devpost.com/updates/9921-hackathon-problem-statements",
        theme="Sustainability / Water",
        description=(
            "Design and build innovative technology solutions — using Blockchain, AI and/or IoT — that help "
            "track and verify wastewater reuse, addressing gaps identified by water-reuse utilities in "
            "monitoring and reporting reused water volumes and quality."
        ),
    ),
]


def build():
    records = []

    for ps_num, theme, title, desc in MITS_RECORDS:
        records.append(
            {
                "title": title,
                "description": desc,
                "organization": "MITS-DU Gwalior",
                "source": "campus",
                "hackathon_name": MITS_HACKATHON,
                "external_id": ps_num,
                "category": None,
                "theme": theme,
                "url": MITS_URL,
                "fetched_at": FETCHED_AT,
            }
        )

    for rec in DEVPOST_RECORDS:
        records.append(
            {
                "title": rec["title"],
                "description": rec["description"],
                "organization": None,
                "source": "devpost",
                "hackathon_name": rec["hackathon_name"],
                "external_id": None,
                "category": None,
                "theme": rec["theme"],
                "url": rec["url"],
                "fetched_at": FETCHED_AT,
            }
        )

    out_path = Path(__file__).resolve().parents[1] / "data_dev" / "curated_supplementary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    print(f"wrote {len(records)} curated records -> {out_path}")


if __name__ == "__main__":
    build()

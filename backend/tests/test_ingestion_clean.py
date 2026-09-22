"""
Tests for app.ingestion.clean — normalization, id generation, and the
dedup logic in particular. The dedup test cases are drawn directly from a
real bug found while building the seed corpus: SIH 2025 has 34 rows all
titled exactly "Student Innovation" (one generic open-call slot per
theme, from different organizations) — 17 of those are genuine duplicates
(byte-identical description too) and 17 are genuinely distinct problems
that happen to share the placeholder title. Title-only similarity
matching collapsed all 34 into 1; this must not regress.
"""

from app.core.taxonomy import extract_technologies
from app.ingestion.clean import clean_pipeline, stable_id


def _raw(title, description, source="sih", external_id=None, **kw):
    rec = {
        "title": title,
        "description": description,
        "source": source,
        "external_id": external_id,
    }
    rec.update(kw)
    return rec


def test_identical_generic_titles_with_different_descriptions_are_kept_distinct():
    records = [
        _raw("Student Innovation", "Ideas to enhance agriculture and manage produce.", external_id="SIH1"),
        _raw("Student Innovation", "Ideas for blockchain and distributed ledger technology.", external_id="SIH2"),
        _raw("Student Innovation", "Ideas for disaster risk mitigation and planning.", external_id="SIH3"),
    ]
    processed = clean_pipeline(records)
    assert len(processed) == 3


def test_identical_title_and_description_collapse_to_one():
    records = [
        _raw("Student Innovation", "Ideas to enhance agriculture and manage produce.", external_id="SIH1"),
        _raw("Student Innovation", "Ideas to enhance agriculture and manage produce.", external_id="SIH4"),
    ]
    processed = clean_pipeline(records)
    assert len(processed) == 1


def test_similar_but_meaningfully_different_titles_within_source_collapse():
    records = [
        _raw(
            "Smart Attendance System Using Facial Recognition",
            "Build a facial-recognition based attendance system for colleges with liveness detection and "
            "a dashboard for administrators to track attendance trends.",
            external_id="A1",
        ),
        _raw(
            "Smart Attendance System using Facial Recognition",  # only casing differs
            "Build a facial recognition based attendance system for colleges with liveness detection and "
            "a dashboard for administrators to track attendance trends.",
            external_id="A2",
        ),
    ]
    processed = clean_pipeline(records)
    assert len(processed) == 1


def test_cross_source_similar_titles_are_not_merged():
    records = [
        _raw("Smart Traffic Management System", "AI based traffic light control for congestion.", source="sih", external_id="S1"),
        _raw("Smart Traffic Management System", "AI based traffic light control for congestion.", source="campus", external_id="C1"),
    ]
    processed = clean_pipeline(records)
    # Same title+description but different sources -> both kept, they're
    # different hackathons' listings even if the ask is similar.
    assert len(processed) == 2


def test_similar_titles_across_different_hackathon_editions_of_same_source_are_not_merged():
    # Regression: dedup used to group near-duplicate detection by `source`
    # alone. SIH 2025 and SIH 2026 both have source="sih" — grouping by
    # source only would wrongly drop a real 2026 problem statement just
    # because a 2025 one happened to use similar wording. Grouping by
    # (source, hackathon_name) instead keeps genuinely distinct editions
    # separate, same as the existing cross-source behavior above.
    records = [
        _raw(
            "Smart Traffic Management System",
            "AI based traffic light control for congestion.",
            source="sih",
            external_id="SIH25999",
            hackathon_name="Smart India Hackathon 2025",
        ),
        _raw(
            "Smart Traffic Management System",
            "AI based traffic light control for congestion.",
            source="sih",
            external_id="SIH26999",
            hackathon_name="Smart India Hackathon 2026",
        ),
    ]
    processed = clean_pipeline(records)
    assert len(processed) == 2


def test_invalid_records_are_skipped_not_fatal():
    records = [
        {"title": "", "description": "blank title should be skipped", "source": "sih"},
        _raw("Valid title", "a valid description", external_id="V1"),
        {"title": "Bad source", "description": "x", "source": "not-a-real-source"},
    ]
    processed = clean_pipeline(records)
    assert len(processed) == 1
    assert processed[0].title == "Valid title"


def test_stable_id_prefers_external_id_and_is_deterministic():
    assert stable_id("sih", "SIH25001", "Some Title") == "sih:sih25001"
    a = stable_id("campus", None, "A Title With No External Id")
    b = stable_id("campus", None, "A Title With No External Id")
    assert a == b
    c = stable_id("campus", None, "A Different Title")
    assert a != c


def test_summary_falls_back_to_title_when_no_description():
    processed = clean_pipeline([_raw("Only A Title", "", external_id="NO_DESC")])
    assert processed[0].summary == "Only A Title"
    assert processed[0].problem_statement == "Only A Title"


def test_category_hardware_does_not_imply_iot_domain():
    """
    Regression test for a real bug found while building the seed corpus:
    SIH's `category` field (Software/Hardware) is a build-type signal, not
    a domain signal — a "Hardware" category problem could be robotics, a
    medical device, hardware security, etc., not necessarily IoT. It must
    not be fed into domain tagging at all, and "hardware" must not be an
    IoT keyword.
    """
    records = [
        _raw(
            "Low-Cost Prosthetic Hand Controller",
            "A wearable robotic prosthetic hand controlled via EMG signals for accessibility.",
            external_id="HW1",
            category="Hardware",
            theme="Robotics & Accessibility",
        ),
    ]
    processed = clean_pipeline(records)
    assert "IoT" not in processed[0].domain


def test_hospitality_does_not_match_hospital_keyword():
    """
    Regression test for a real bug found while building the seed corpus:
    plain substring matching let the Healthcare keyword "hospital" match
    inside the unrelated word "hospitality" (a tourism-platform problem
    mentioning "hospitality services" was wrongly tagged Healthcare).
    Domain keywords must match on word boundaries.
    """
    records = [
        _raw(
            "Smart Digital Platform to Promote Eco & Cultural Tourism",
            "Tourists struggle to find reliable information about travel and hospitality services in the region.",
            external_id="TOUR1",
        ),
    ]
    processed = clean_pipeline(records)
    assert "Healthcare" not in processed[0].domain


def test_generic_student_word_does_not_imply_edtech_domain():
    """
    Regression test for a real bug found while building the seed corpus:
    SIH has 34 rows literally titled "Student Innovation" (a generic
    open-call slot, not an EdTech signal) spanning every domain from
    agriculture to blockchain. The bare word "student" is too generic to
    use as an EdTech keyword — it must not be in THEME_KEYWORDS["EdTech"].
    """
    records = [
        _raw(
            "Student Innovation",
            "Ideas to enhance agriculture and manage produce.",
            external_id="SIH_AGRI",
        ),
    ]
    processed = clean_pipeline(records)
    assert "EdTech" not in processed[0].domain
    assert "Agriculture" in processed[0].domain


def test_ar_mentions_match_the_ar_vr_technology():
    """
    Regression test for a real bug found via a real user's saved
    roadmap: the "AR/VR" tech keyword only matched the literal compound
    string "AR/VR", which essentially never appears in real text — a
    genuine AR problem statement (title "AR-Based Cultural Heritage
    Preservation Platform", repeatedly mentioning "AR" and "augmented
    reality") matched zero technologies, so the Resource Agent had
    nothing to look up and the Resources page showed nothing for it.
    """
    assert "AR/VR" in extract_technologies("Build an AR app for museum tours.")
    assert "AR/VR" in extract_technologies("An augmented reality platform for heritage sites.")
    assert "AR/VR" in extract_technologies("A VR training simulator for surgeons.")
    assert "AR/VR" in extract_technologies("Explore a virtual reality campus tour.")
    assert "AR/VR" not in extract_technologies("A standard web app with no immersive tech.")


def test_crop_disease_does_not_imply_healthcare_domain():
    """
    Regression test for a real bug found via a live /api/v1/plan run: the
    bare word "disease" in THEME_KEYWORDS["Healthcare"] matched non-human
    contexts like "crop disease" (also "plant disease", "livestock
    disease"), tagging agriculture problems as Healthcare and pulling in
    irrelevant resources (e.g. an HL7 FHIR link) via the Resource Agent.
    "disease" must not be a standalone Healthcare keyword.
    """
    records = [
        _raw(
            "AI-Driven Crop Disease Prediction and Management System",
            "Detect crop disease from leaf images using computer vision and recommend treatment.",
            external_id="AGRI_DISEASE",
        ),
    ]
    processed = clean_pipeline(records)
    assert "Healthcare" not in processed[0].domain
    assert "Agriculture" in processed[0].domain

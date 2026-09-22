"""
Tests for app.services.pptx_builder — pure formatting of an already-built
plan into a .pptx, no Gemini calls involved. Verified by re-opening the
generated buffer with python-pptx and reading its slides/text back.
"""

from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE

from app.services.pptx_builder import (
    BODY_SIZE,
    COVER_TITLE_SIZE,
    HEADING_SIZE,
    PAPER,
    SKY_DEEP,
    TITLE_SIZE,
    build_pptx,
)

FULL_PLAN = {
    "problem_understanding": "Farmers need a way to detect crop disease early from photos.",
    "tech_stack": ["Python", "TensorFlow", "React Native"],
    "architecture": "A mobile app uploads leaf photos to a Flask API running a CNN classifier.",
    "roadmap": [],
    "deliverables": [],
    "existing_solutions": ["Plantix"],
    "differentiation_ideas": ["Offline-first inference for low-connectivity farms"],
    "feasibility": "Buildable in a hackathon with a pretrained CNN and a small labeled dataset.",
    "advantages": ["Works offline", "Low-cost to run on free-tier hosting"],
    "scalability": "Could extend to more crop types with more training data.",
    "cost_effectiveness": "Free-tier hosting covers a demo; production needs paid inference compute.",
}


def _all_text(slide) -> str:
    chunks = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            chunks.append(shape.text_frame.text)
    return "\n".join(chunks)


def test_build_pptx_produces_exactly_eight_slides():
    buffer = build_pptx(
        problem_title="Crop Disease Detector",
        problem_statement="Detect crop disease from leaf images.",
        plan=FULL_PLAN,
    )
    prs = Presentation(buffer)
    assert len(prs.slides) == 8


def test_build_pptx_slide_order_and_real_content():
    buffer = build_pptx(
        problem_title="Crop Disease Detector",
        problem_statement="Detect crop disease from leaf images.",
        plan=FULL_PLAN,
        source="sih",
        hackathon_name="Smart India Hackathon 2025",
    )
    prs = Presentation(buffer)
    slides = list(prs.slides)

    assert slides[0].shapes.title.text == "Crop Disease Detector"
    assert "Smart India Hackathon 2025" in _all_text(slides[0])

    assert slides[1].shapes.title.text == "Problem Statement"
    assert FULL_PLAN["problem_understanding"] in _all_text(slides[1])

    assert slides[2].shapes.title.text == "Proposed Solution"
    assert FULL_PLAN["architecture"] in _all_text(slides[2])

    assert "Existing" in slides[3].shapes.title.text
    assert "Plantix" in _all_text(slides[3])
    assert "Offline-first inference for low-connectivity farms" in _all_text(slides[3])

    assert slides[4].shapes.title.text == "Proposed Tech Stack"
    for tech in FULL_PLAN["tech_stack"]:
        assert tech in _all_text(slides[4])

    assert slides[5].shapes.title.text == "Literature Review"
    # Explicitly left blank — no body content beyond the title placeholder.
    assert _all_text(slides[5]).strip() == "Literature Review"

    assert "Feasibility" in slides[6].shapes.title.text
    body6 = _all_text(slides[6])
    assert FULL_PLAN["feasibility"] in body6
    assert "Works offline" in body6
    assert FULL_PLAN["scalability"] in body6
    assert FULL_PLAN["cost_effectiveness"] in body6

    assert slides[7].shapes.title.text == "Thank You"


def test_build_pptx_never_fabricates_missing_content():
    sparse_plan = {
        "problem_understanding": None,
        "tech_stack": [],
        "architecture": None,
        "existing_solutions": [],
        "differentiation_ideas": [],
        "feasibility": None,
        "advantages": [],
        "scalability": None,
        "cost_effectiveness": None,
    }
    buffer = build_pptx(
        problem_title="Untitled Project",
        problem_statement="Fallback problem statement text.",
        plan=sparse_plan,
    )
    prs = Presentation(buffer)
    slides = list(prs.slides)

    # Falls back to the raw problem statement when Gemini's own
    # restatement is missing — never invents new text.
    assert "Fallback problem statement text." in _all_text(slides[1])
    # Missing fields are labeled as not identified, not silently blank or
    # filled with plausible-sounding placeholder content.
    assert "Not identified" in _all_text(slides[2])
    assert "Not identified" in _all_text(slides[3])


def test_build_pptx_uses_one_consistent_font_size_per_role_everywhere():
    # Every title uses TITLE_SIZE except the cover/closing slides, which use
    # the larger COVER_TITLE_SIZE — but that size is identical on both of
    # them, and every body paragraph across every slide uses BODY_SIZE
    # (headings inside a slide use HEADING_SIZE). Nothing slide-specific.
    buffer = build_pptx(problem_title="Crop Disease Detector", problem_statement="Detect crop disease.", plan=FULL_PLAN)
    prs = Presentation(buffer)
    slides = list(prs.slides)

    assert slides[0].shapes.title.text_frame.paragraphs[0].font.size == COVER_TITLE_SIZE
    assert slides[7].shapes.title.text_frame.paragraphs[0].font.size == COVER_TITLE_SIZE
    for i in (1, 2, 3, 4, 5, 6):
        assert slides[i].shapes.title.text_frame.paragraphs[0].font.size == TITLE_SIZE

    for slide in slides:
        for shape in slide.shapes:
            if not shape.has_text_frame or shape == slide.shapes.title:
                continue
            for paragraph in shape.text_frame.paragraphs:
                size = paragraph.font.size
                assert size in (BODY_SIZE, HEADING_SIZE), f"unexpected font size {size} in a body text frame"


def test_build_pptx_shrinks_text_to_fit_instead_of_overflowing():
    long_plan = {
        **FULL_PLAN,
        "architecture": "A very long architecture description. " * 40,
        "tech_stack": [f"Technology {i}" for i in range(20)],
    }
    buffer = build_pptx(problem_title="Crop Disease Detector", problem_statement="x", plan=long_plan)
    prs = Presentation(buffer)

    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                assert shape.text_frame.word_wrap is True
                assert shape.text_frame.auto_size == MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE


def test_build_pptx_applies_the_hackbase_brand_color_theme():
    buffer = build_pptx(problem_title="Crop Disease Detector", problem_statement="x", plan=FULL_PLAN)
    prs = Presentation(buffer)
    slides = list(prs.slides)

    # Cover and closing slides get the strong brand-accent background;
    # every content slide shares the same paper background — one
    # consistent template, not an ad hoc color per slide.
    assert slides[0].background.fill.fore_color.rgb == SKY_DEEP
    assert slides[7].background.fill.fore_color.rgb == SKY_DEEP
    for i in (1, 2, 3, 4, 5, 6):
        assert slides[i].background.fill.fore_color.rgb == PAPER

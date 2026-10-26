"""
Formats an already-generated plan into a .pdf — this is what "View PPT"
opens in the browser's own PDF viewer, since browsers can't render .pptx
natively and this environment has no LibreOffice/PowerPoint installed for
a real pptx -> pdf conversion. Renders the exact same real plan content as
app.services.pptx_builder's .pptx (same 8-section structure, same "not
identified" honesty when a field is empty), through reportlab instead —
a parallel pure-Python path, no external binary, no invented text.

Plan text comes from Gemini's free-form output, which can genuinely
contain '&', '<', '>' — reportlab's Paragraph parses its text as a small
XML-like markup, so every dynamic string is escaped before being wrapped
in one (see _esc()); only the hardcoded section headings below are passed
unescaped, since those are trusted literals this module wrote itself.
"""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer

# --- HackBase brand palette (frontend/src/styles/tokens.css) ---
SKY_DEEP = colors.HexColor("#3F6483")
INK = colors.HexColor("#232733")

_NOT_IDENTIFIED = "Not identified by the Planning Agent."

_base_styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("HBTitle", parent=_base_styles["Title"], textColor=SKY_DEEP, fontSize=22, spaceAfter=16)
COVER_TITLE_STYLE = ParagraphStyle("HBCoverTitle", parent=TITLE_STYLE, fontSize=30, alignment=1)
COVER_SUBTITLE_STYLE = ParagraphStyle(
    "HBCoverSubtitle", parent=_base_styles["BodyText"], textColor=SKY_DEEP, fontSize=13, alignment=1
)
HEADING_STYLE = ParagraphStyle(
    "HBHeading", parent=_base_styles["Heading2"], textColor=SKY_DEEP, fontSize=13, spaceBefore=14, spaceAfter=6
)
BODY_STYLE = ParagraphStyle("HBBody", parent=_base_styles["BodyText"], textColor=INK, fontSize=11, leading=15)


def _esc(text: str | None) -> str:
    return escape(text) if text else ""


def _bullets(items: list[str]) -> ListFlowable:
    items = items or [_NOT_IDENTIFIED]
    return ListFlowable(
        [ListItem(Paragraph(_esc(item), BODY_STYLE)) for item in items],
        bulletType="bullet",
        leftIndent=18,
    )


def _paragraph_section(story: list, title: str, text: str | None) -> None:
    story.append(Paragraph(title, TITLE_STYLE))
    story.append(Paragraph(_esc(text) or _NOT_IDENTIFIED, BODY_STYLE))
    story.append(PageBreak())


def _bullet_section(story: list, title: str, items: list[str]) -> None:
    story.append(Paragraph(title, TITLE_STYLE))
    story.append(_bullets(items))
    story.append(PageBreak())


def _two_column_section(
    story: list,
    title: str,
    left_heading: str,
    left_items: list[str],
    right_heading: str,
    right_items: list[str],
) -> None:
    story.append(Paragraph(title, TITLE_STYLE))
    story.append(Paragraph(left_heading, HEADING_STYLE))
    story.append(_bullets(left_items))
    story.append(Paragraph(right_heading, HEADING_STYLE))
    story.append(_bullets(right_items))
    story.append(PageBreak())


def build_pdf(
    *,
    problem_title: str,
    problem_statement: str,
    plan: dict,
    source: str | None = None,
    hackathon_name: str | None = None,
) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        title=problem_title,
    )
    story: list = []

    # 1. Cover
    story.append(Spacer(1, 2.2 * inch))
    story.append(Paragraph(_esc(problem_title) or "Roadmap", COVER_TITLE_STYLE))
    subtitle = hackathon_name or source
    if subtitle:
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph(_esc(subtitle), COVER_SUBTITLE_STYLE))
    story.append(PageBreak())

    # 2. Problem statement
    _paragraph_section(story, "Problem Statement", plan.get("problem_understanding") or problem_statement)

    # 3. Proposed solution
    _paragraph_section(story, "Proposed Solution", plan.get("architecture"))

    # 4. Proposed solution vs. existing solutions
    _two_column_section(
        story,
        "Proposed Solution vs. Existing Solutions",
        "Existing solutions",
        plan.get("existing_solutions") or [],
        "How this project differs",
        plan.get("differentiation_ideas") or [],
    )

    # 5. Proposed tech stack
    _bullet_section(story, "Proposed Tech Stack", plan.get("tech_stack") or [])

    # 6. Literature review (title only, same as the .pptx — filled in by the team later)
    story.append(Paragraph("Literature Review", TITLE_STYLE))
    story.append(Paragraph("Filled in by the team later.", BODY_STYLE))
    story.append(PageBreak())

    # 7. Feasibility, advantages, scalability & cost
    story.append(Paragraph("Feasibility, Advantages, Scalability & Cost", TITLE_STYLE))
    story.append(Paragraph("Feasibility", HEADING_STYLE))
    story.append(Paragraph(_esc(plan.get("feasibility")) or _NOT_IDENTIFIED, BODY_STYLE))
    story.append(Paragraph("Advantages", HEADING_STYLE))
    story.append(_bullets(plan.get("advantages") or []))
    story.append(Paragraph("Scalability", HEADING_STYLE))
    story.append(Paragraph(_esc(plan.get("scalability")) or _NOT_IDENTIFIED, BODY_STYLE))
    story.append(Paragraph("Cost-effectiveness", HEADING_STYLE))
    story.append(Paragraph(_esc(plan.get("cost_effectiveness")) or _NOT_IDENTIFIED, BODY_STYLE))
    story.append(PageBreak())

    # 8. Thank you
    story.append(Spacer(1, 2.8 * inch))
    story.append(Paragraph("Thank You", COVER_TITLE_STYLE))

    doc.build(story)
    buffer.seek(0)
    return buffer

"""
Formats an already-generated plan (see app.schemas.plan.PptxExportRequest)
into a .pptx file. Pure formatting — makes no Gemini calls and invents no
content: every slide either uses text the Planning Agent already produced,
or (for the literature review slide, and any list Gemini left empty) is
left honestly blank/labeled as such rather than filled with placeholder
text.

Every slide uses the same fixed set of font sizes and the same HackBase
brand colors (frontend/src/styles/tokens.css — --sky, --sky-deep, --sand,
--ink, --paper), and every text box auto-shrinks to fit its box
(MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE) so long Gemini output never overflows a
slide instead of just being drawn smaller.

Fixed 8-slide template, per product spec:
  1. Title
  2. Problem statement explained
  3. Proposed solution
  4. Proposed solution vs existing solutions
  5. Proposed tech stack
  6. Literature review (title only — filled in by the team later)
  7. Feasibility, advantages, scalability, cost-effectiveness
  8. Thank you
"""

from __future__ import annotations

import io

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

TITLE_ONLY_LAYOUT = 5  # "Title Only" — just a title placeholder, empty body

# python-pptx's built-in default template is a 10in x 7.5in (4:3) canvas —
# every position below is sized against that, since resizing prs.slide_*
# without also moving the template's own layout placeholders would just
# leave them mispositioned relative to a bigger canvas.
MARGIN_X = Inches(0.5)
CONTENT_TOP = Inches(1.6)
CONTENT_HEIGHT = Inches(5.3)
CONTENT_WIDTH = Inches(9.0)
COLUMN_GAP = Inches(0.4)

# --- HackBase brand palette (frontend/src/styles/tokens.css) ---
SKY_DEEP = RGBColor(0x3F, 0x64, 0x83)
SAND = RGBColor(0xF3, 0xE3, 0xD0)
INK = RGBColor(0x23, 0x27, 0x33)
PAPER = RGBColor(0xFD, 0xFB, 0xF8)

# One consistent size per role, used identically on every slide — the
# thing that was previously inconsistent slide-to-slide.
COVER_TITLE_SIZE = Pt(40)
TITLE_SIZE = Pt(32)
HEADING_SIZE = Pt(18)
BODY_SIZE = Pt(16)

_NOT_IDENTIFIED = "Not identified by the Planning Agent."


def _set_background(slide, color: RGBColor):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _style_title(slide, *, color: RGBColor, size, align=None):
    title = slide.shapes.title
    title.text_frame.word_wrap = True
    title.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    p = title.text_frame.paragraphs[0]
    p.font.size = size
    p.font.bold = True
    p.font.color.rgb = color
    if align is not None:
        p.alignment = align


def _new_slide(prs: Presentation, title: str, *, bg=PAPER, title_color=SKY_DEEP, title_size=TITLE_SIZE, align=None):
    slide = prs.slides.add_slide(prs.slide_layouts[TITLE_ONLY_LAYOUT])
    _set_background(slide, bg)
    slide.shapes.title.text = title
    _style_title(slide, color=title_color, size=title_size, align=align)
    return slide


def _add_textbox(slide, *, top=CONTENT_TOP, height=CONTENT_HEIGHT, left=MARGIN_X, width=CONTENT_WIDTH):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    return tf


def _set_paragraph(paragraph, text: str, *, size=BODY_SIZE, bold=False, color=INK, align=None):
    paragraph.text = text
    paragraph.font.size = size
    paragraph.font.bold = bold
    paragraph.font.color.rgb = color
    if align is not None:
        paragraph.alignment = align
    return paragraph


def _add_cover_slide(prs: Presentation, title: str, subtitle: str | None):
    slide = _new_slide(prs, title, bg=SKY_DEEP, title_color=PAPER, title_size=COVER_TITLE_SIZE, align=PP_ALIGN.CENTER)
    if subtitle:
        tf = _add_textbox(slide)
        _set_paragraph(tf.paragraphs[0], subtitle, size=HEADING_SIZE, color=SAND, align=PP_ALIGN.CENTER)
    return slide


def _add_paragraph_slide(prs: Presentation, title: str, text: str | None, empty_note: str = _NOT_IDENTIFIED):
    slide = _new_slide(prs, title)
    tf = _add_textbox(slide)
    _set_paragraph(tf.paragraphs[0], text or empty_note)
    return slide


def _add_bullet_slide(prs: Presentation, title: str, bullets: list[str], empty_note: str = _NOT_IDENTIFIED):
    slide = _new_slide(prs, title)
    tf = _add_textbox(slide)
    items = bullets or [empty_note]
    _set_paragraph(tf.paragraphs[0], f"• {items[0]}" if bullets else items[0])
    for item in items[1:]:
        _set_paragraph(tf.add_paragraph(), f"• {item}")
    return slide


def _add_two_column_slide(
    prs: Presentation,
    title: str,
    left_heading: str,
    left_items: list[str],
    right_heading: str,
    right_items: list[str],
):
    slide = _new_slide(prs, title)
    col_width = int((CONTENT_WIDTH - COLUMN_GAP) / 2)
    right_x = MARGIN_X + col_width + COLUMN_GAP

    for x, heading, items in ((MARGIN_X, left_heading, left_items), (right_x, right_heading, right_items)):
        tf = _add_textbox(slide, left=x, width=col_width)
        _set_paragraph(tf.paragraphs[0], heading, size=HEADING_SIZE, bold=True, color=SKY_DEEP)
        for item in items or [_NOT_IDENTIFIED]:
            _set_paragraph(tf.add_paragraph(), f"• {item}")
    return slide


def _add_feasibility_slide(
    prs: Presentation,
    feasibility: str | None,
    advantages: list[str],
    scalability: str | None,
    cost_effectiveness: str | None,
):
    slide = _new_slide(prs, "Feasibility, Advantages, Scalability & Cost")
    tf = _add_textbox(slide)

    sections = [
        ("Feasibility", feasibility or _NOT_IDENTIFIED, False),
        ("Advantages", advantages, True),
        ("Scalability", scalability or _NOT_IDENTIFIED, False),
        ("Cost-effectiveness", cost_effectiveness or _NOT_IDENTIFIED, False),
    ]

    first = True
    for heading, value, is_list in sections:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        _set_paragraph(p, heading, size=HEADING_SIZE, bold=True, color=SKY_DEEP)

        if is_list:
            for item in value or [_NOT_IDENTIFIED]:
                _set_paragraph(tf.add_paragraph(), f"• {item}")
        else:
            _set_paragraph(tf.add_paragraph(), value)
    return slide


def build_pptx(
    *,
    problem_title: str,
    problem_statement: str,
    plan: dict,
    source: str | None = None,
    hackathon_name: str | None = None,
) -> io.BytesIO:
    prs = Presentation()

    _add_cover_slide(prs, problem_title, hackathon_name or source)

    _add_paragraph_slide(
        prs,
        "Problem Statement",
        plan.get("problem_understanding") or problem_statement,
    )

    _add_paragraph_slide(prs, "Proposed Solution", plan.get("architecture"))

    _add_two_column_slide(
        prs,
        "Proposed Solution vs. Existing Solutions",
        "Existing solutions",
        plan.get("existing_solutions") or [],
        "How this project differs",
        plan.get("differentiation_ideas") or [],
    )

    _add_bullet_slide(prs, "Proposed Tech Stack", plan.get("tech_stack") or [])

    _new_slide(prs, "Literature Review")

    _add_feasibility_slide(
        prs,
        plan.get("feasibility"),
        plan.get("advantages") or [],
        plan.get("scalability"),
        plan.get("cost_effectiveness"),
    )

    _new_slide(prs, "Thank You", bg=SKY_DEEP, title_color=PAPER, title_size=COVER_TITLE_SIZE, align=PP_ALIGN.CENTER)

    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer

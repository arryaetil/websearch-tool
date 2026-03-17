"""
pdf_export.py - Professioneel PDF rapport generator voor Identity Research Tool
Gebruikt reportlab
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Etil kleurenpalet ──────────────────────────────────────────────────────────
ETIL_BLUE      = colors.HexColor("#1a3a5c")
ETIL_ACCENT    = colors.HexColor("#2e7dc9")
ETIL_LIGHT     = colors.HexColor("#e8f0fa")
RISK_HIGH      = colors.HexColor("#dc2626")
RISK_HIGH_BG   = colors.HexColor("#fee2e2")
RISK_MED       = colors.HexColor("#d97706")
RISK_MED_BG    = colors.HexColor("#fef3c7")
RISK_LOW       = colors.HexColor("#16a34a")
RISK_LOW_BG    = colors.HexColor("#dcfce7")
GRAY_TEXT      = colors.HexColor("#6b7280")
GRAY_BORDER    = colors.HexColor("#e5e7eb")
WHITE          = colors.white
BLACK          = colors.HexColor("#111827")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


def build_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "title", fontSize=22, textColor=ETIL_BLUE,
            fontName="Helvetica-Bold", spaceAfter=4,
            leading=26
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontSize=11, textColor=GRAY_TEXT,
            fontName="Helvetica", spaceAfter=2
        ),
        "section": ParagraphStyle(
            "section", fontSize=11, textColor=ETIL_BLUE,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
            leading=14
        ),
        "body": ParagraphStyle(
            "body", fontSize=9, textColor=BLACK,
            fontName="Helvetica", spaceAfter=4, leading=13
        ),
        "small": ParagraphStyle(
            "small", fontSize=8, textColor=GRAY_TEXT,
            fontName="Helvetica", spaceAfter=2, leading=11
        ),
        "bold": ParagraphStyle(
            "bold", fontSize=9, textColor=BLACK,
            fontName="Helvetica-Bold", spaceAfter=2
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer", fontSize=7.5, textColor=GRAY_TEXT,
            fontName="Helvetica-Oblique", leading=11,
            borderColor=GRAY_BORDER, borderWidth=0.5,
            borderPadding=6, spaceAfter=4
        ),
        "center": ParagraphStyle(
            "center", fontSize=9, textColor=BLACK,
            fontName="Helvetica", alignment=TA_CENTER
        ),
    }
    return styles


def score_color(score):
    s = int(score)
    if s >= 75:
        return RISK_LOW, RISK_LOW_BG
    elif s >= 45:
        return RISK_MED, RISK_MED_BG
    else:
        return RISK_HIGH, RISK_HIGH_BG


def severity_color(severity):
    s = severity.lower()
    if s == "high":
        return RISK_HIGH, RISK_HIGH_BG
    elif s == "medium":
        return RISK_MED, RISK_MED_BG
    return RISK_LOW, RISK_LOW_BG


def header_table(styles, subject_name, subject_city, analyst, generated_at):
    """Top header with branding and meta info."""
    left = [
        Paragraph("ETIL", ParagraphStyle("brand", fontSize=20,
            textColor=WHITE, fontName="Helvetica-Bold")),
        Paragraph("Identity Research Report", ParagraphStyle("brandSub",
            fontSize=9, textColor=colors.HexColor("#a8c4e0"),
            fontName="Helvetica")),
    ]
    right = [
        Paragraph(f"<b>Subject:</b> {subject_name}", ParagraphStyle(
            "meta", fontSize=9, textColor=WHITE, fontName="Helvetica",
            alignment=TA_RIGHT)),
        Paragraph(f"<b>Region:</b> {subject_city}", ParagraphStyle(
            "meta2", fontSize=9, textColor=WHITE, fontName="Helvetica",
            alignment=TA_RIGHT)),
        Paragraph(f"<b>Analyst:</b> {analyst or '—'}", ParagraphStyle(
            "meta3", fontSize=9, textColor=WHITE, fontName="Helvetica",
            alignment=TA_RIGHT)),
        Paragraph(f"<b>Date:</b> {generated_at}", ParagraphStyle(
            "meta4", fontSize=9, textColor=WHITE, fontName="Helvetica",
            alignment=TA_RIGHT)),
    ]

    t = Table([[left, right]], colWidths=[90*mm, 80*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ETIL_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 8*mm),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 6*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5*mm),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def confidence_block(styles, score, verdict, reasoning):
    """Confidence score visual block."""
    score_int = int(score)
    fg, bg = score_color(score_int)

    score_cell = Paragraph(
        f'<font size="28"><b>{score_int}</b></font><br/>'
        f'<font size="8">/ 100</font>',
        ParagraphStyle("sc", alignment=TA_CENTER, textColor=fg,
                       fontName="Helvetica-Bold", leading=30)
    )
    info_cell = [
        Paragraph(f"<b>{verdict} Confidence</b>",
                  ParagraphStyle("cv", fontSize=11, textColor=fg,
                                 fontName="Helvetica-Bold", spaceAfter=3)),
        Paragraph(reasoning or "—", styles["body"]),
    ]

    t = Table([[score_cell, info_cell]], colWidths=[30*mm, 140*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 5*mm),
        ("LEFTPADDING", (1, 0), (1, 0), 4*mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
        ("BOX", (0, 0), (-1, -1), 0.5, fg),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def section_table(styles, rows, col_headers, col_widths):
    """Generic data table."""
    if not rows:
        return Paragraph("No data found.", styles["small"])

    data = [col_headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ETIL_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ETIL_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, GRAY_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(style))
    return t


def risk_flags_block(styles, flags):
    """Risk flags with colored severity badges."""
    if not flags:
        return Paragraph("✓ No risk flags identified.", ParagraphStyle(
            "ok", fontSize=9, textColor=RISK_LOW, fontName="Helvetica-Bold"))

    elements = []
    for f in flags:
        fg, bg = severity_color(f.get("severity", "low"))
        sev = f.get("severity", "low").upper()
        cat = f.get("category", "")
        desc = f.get("description", "")

        row = Table(
            [[Paragraph(f"<b>[{sev}]</b>", ParagraphStyle(
                "sev", fontSize=8, textColor=fg, fontName="Helvetica-Bold")),
              Paragraph(f"<b>{cat}</b> — {desc}", ParagraphStyle(
                "desc", fontSize=8.5, textColor=BLACK, fontName="Helvetica",
                leading=12))]],
            colWidths=[18*mm, 152*mm]
        )
        row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, 0), 4),
            ("LEFTPADDING", (1, 0), (1, 0), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("BOX", (0, 0), (-1, -1), 0.4, fg),
            ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ]))
        elements.append(row)
        elements.append(Spacer(1, 3))
    return elements


def wrap(text, maxlen=80):
    """Wrap long text for table cells."""
    if not text:
        return "—"
    return text[:maxlen] + ("…" if len(text) > maxlen else "")


def generate_pdf(report: dict, subject_name: str, subject_city: str,
                 analyst: str = "") -> bytes:
    """
    Generate a professional PDF report from the research JSON.
    Returns PDF as bytes (for Streamlit download).
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"Identity Report — {subject_name}",
        author="Etil Identity Research Tool"
    )

    styles = build_styles()
    generated_at = datetime.now().strftime("%d %b %Y, %H:%M")
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(header_table(styles, subject_name, subject_city,
                               analyst, generated_at))
    story.append(Spacer(1, 6*mm))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "⚠ CONFIDENTIAL — For internal compliance use only. This report was generated by AI "
        "from publicly available sources. All findings require human analyst review before "
        "any decision is made. Do not distribute externally.",
        styles["disclaimer"]
    ))
    story.append(Spacer(1, 4*mm))

    # ── Confidence Score ───────────────────────────────────────────────────────
    story.append(Paragraph("Identity Confidence", styles["section"]))
    story.append(confidence_block(
        styles,
        report.get("confidence_score", "0"),
        report.get("confidence_verdict", "Low"),
        report.get("confidence_reasoning", "")
    ))
    story.append(Spacer(1, 5*mm))

    # ── Name Variations Searched ──────────────────────────────────────────────
    variations = report.get("name_variations_searched", [])
    if variations:
        story.append(Paragraph("Name Variations Searched", styles["section"]))
        story.append(Paragraph(
            " · ".join(variations),
            ParagraphStyle("vars", fontSize=8.5, textColor=ETIL_ACCENT,
                           fontName="Helvetica-Oblique")
        ))
        story.append(Spacer(1, 5*mm))

    # ── Identity Matches ─────────────────────────────────────────────────────
    story.append(Paragraph("Identity Matches", styles["section"]))
    matches = report.get("identity_matches", [])
    rows = [[wrap(m.get("name",""), 40),
             wrap(m.get("description",""), 80),
             m.get("confidence","").upper()]
            for m in matches]
    story.append(section_table(
        styles, rows,
        ["Name", "Description", "Confidence"],
        [45*mm, 105*mm, 20*mm]
    ))
    story.append(Spacer(1, 5*mm))

    # ── Professional Profiles ─────────────────────────────────────────────────
    story.append(Paragraph("Professional Profiles", styles["section"]))
    profiles = report.get("professional_profiles", [])
    rows = [[p.get("platform",""), wrap(p.get("role",""), 35),
             wrap(p.get("company",""), 35), wrap(p.get("url_hint",""), 40)]
            for p in profiles]
    story.append(section_table(
        styles, rows,
        ["Platform", "Role", "Company", "Source"],
        [25*mm, 45*mm, 45*mm, 55*mm]
    ))
    story.append(Spacer(1, 5*mm))

    # ── Business Records ─────────────────────────────────────────────────────
    story.append(Paragraph("Business Records", styles["section"]))
    records = report.get("business_records", [])
    rows = [[wrap(b.get("entity",""), 40), b.get("role",""),
             b.get("status",""), b.get("source","")]
            for b in records]
    story.append(section_table(
        styles, rows,
        ["Entity", "Role", "Status", "Source"],
        [55*mm, 40*mm, 30*mm, 45*mm]
    ))
    story.append(Spacer(1, 5*mm))

    # ── Media Mentions ────────────────────────────────────────────────────────
    story.append(Paragraph("Media Mentions", styles["section"]))
    mentions = report.get("media_mentions", [])
    rows = [[wrap(m.get("title",""), 50), m.get("source",""),
             m.get("date",""), m.get("sentiment","").capitalize(),
             wrap(m.get("summary",""), 60)]
            for m in mentions]
    story.append(section_table(
        styles, rows,
        ["Title", "Source", "Date", "Sentiment", "Summary"],
        [50*mm, 28*mm, 20*mm, 18*mm, 54*mm]
    ))
    story.append(Spacer(1, 5*mm))

    # ── Social Media ──────────────────────────────────────────────────────────
    story.append(Paragraph("Social Media Presence", styles["section"]))
    social = report.get("social_media_presence", [])
    rows = [[s.get("platform",""), wrap(s.get("description",""), 120)]
            for s in social]
    story.append(section_table(
        styles, rows,
        ["Platform", "Description"],
        [35*mm, 135*mm]
    ))
    story.append(Spacer(1, 5*mm))

    # ── Risk Flags ────────────────────────────────────────────────────────────
    story.append(Paragraph("Risk Flags", styles["section"]))
    rf = risk_flags_block(styles, report.get("risk_flags", []))
    if isinstance(rf, list):
        story.extend(rf)
    else:
        story.append(rf)
    story.append(Spacer(1, 5*mm))

    # ── Sources ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Sources Consulted", styles["section"]))
    sources = report.get("sources", [])
    rows = [[wrap(s.get("name",""), 50), wrap(s.get("url",""), 90),
             s.get("type","")]
            for s in sources]
    story.append(section_table(
        styles, rows,
        ["Source", "URL", "Type"],
        [45*mm, 100*mm, 25*mm]
    ))
    story.append(Spacer(1, 8*mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"Generated by Etil Identity Research Tool · {generated_at} · "
        f"Analyst: {analyst or '—'} · CONFIDENTIAL",
        ParagraphStyle("footer", fontSize=7, textColor=GRAY_TEXT,
                       fontName="Helvetica", alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()

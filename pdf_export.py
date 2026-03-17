"""
pdf_export.py - Functioneel PDF rapport, clean en leesbaar
"""
 
from datetime import datetime
from io import BytesIO
 
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
 
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
 
BLUE      = colors.HexColor("#1a3a5c")
ACCENT    = colors.HexColor("#2e7dc9")
LIGHT_BG  = colors.HexColor("#f0f4f8")
RED       = colors.HexColor("#dc2626")
RED_BG    = colors.HexColor("#fee2e2")
ORANGE    = colors.HexColor("#d97706")
ORANGE_BG = colors.HexColor("#fef3c7")
GREEN     = colors.HexColor("#16a34a")
GREEN_BG  = colors.HexColor("#dcfce7")
GRAY      = colors.HexColor("#6b7280")
BORDER    = colors.HexColor("#d1d5db")
WHITE     = colors.white
BLACK     = colors.HexColor("#1f2937")
 
CONTENT_W = PAGE_W - 2 * MARGIN  # ~174mm
 
 
def style(name, **kwargs):
    defaults = dict(fontName="Helvetica", fontSize=9, textColor=BLACK,
                    leading=13, spaceAfter=2)
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)
 
 
STYLES = {
    "h1":   style("h1", fontSize=14, textColor=BLUE, fontName="Helvetica-Bold",
                  spaceBefore=0, spaceAfter=4),
    "h2":   style("h2", fontSize=10, textColor=BLUE, fontName="Helvetica-Bold",
                  spaceBefore=10, spaceAfter=4),
    "body": style("body"),
    "small":style("small", fontSize=8, textColor=GRAY),
    "disc": style("disc", fontSize=7.5, textColor=GRAY,
                  fontName="Helvetica-Oblique", leading=11),
    "foot": style("foot", fontSize=7, textColor=GRAY,
                  alignment=TA_CENTER),
    "score_num": style("score_num", fontSize=26, fontName="Helvetica-Bold",
                       alignment=TA_CENTER, leading=30),
    "score_lbl": style("score_lbl", fontSize=8, textColor=GRAY,
                       alignment=TA_CENTER),
    "vars": style("vars", fontSize=8.5, textColor=ACCENT,
                  fontName="Helvetica-Oblique"),
}
 
 
def wrap(text, maxlen):
    """Hard-wrap text to fit column, no overflow."""
    if not text:
        return "—"
    text = str(text).replace("\n", " ").strip()
    if len(text) <= maxlen:
        return text
    # Break into multiple lines
    words = text.split()
    lines, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 <= maxlen:
            current = (current + " " + w).strip()
        else:
            if current:
                lines.append(current)
            current = w[:maxlen]
    if current:
        lines.append(current)
    return "\n".join(lines)
 
 
def p(text, st="body"):
    """Shortcut: make a Paragraph."""
    return Paragraph(str(text) if text else "—", STYLES[st])
 
 
def score_color(score):
    s = int(score)
    if s >= 75:
        return GREEN, GREEN_BG
    elif s >= 45:
        return ORANGE, ORANGE_BG
    return RED, RED_BG
 
 
def sev_color(sev):
    s = str(sev).lower()
    if s == "high":   return RED, RED_BG
    if s == "medium": return ORANGE, ORANGE_BG
    return GREEN, GREEN_BG
 
 
def make_table(headers, rows, col_widths):
    """Build a clean table that fits within content width."""
    # Verify widths sum correctly
    total = sum(col_widths)
    if abs(total - CONTENT_W) > 2:
        # Scale to fit
        scale = CONTENT_W / total
        col_widths = [w * scale for w in col_widths]
 
    # Convert rows: each cell becomes a Paragraph so text wraps
    char_widths = [int(w / mm * 2.2) for w in col_widths]  # approx chars per mm
 
    header_row = [Paragraph(str(h), ParagraphStyle(
        "th", fontName="Helvetica-Bold", fontSize=8,
        textColor=WHITE, leading=11)) for h in headers]
 
    data_rows = []
    for row in rows:
        data_row = []
        for i, cell in enumerate(row):
            maxc = max(char_widths[i] - 2, 8)
            data_row.append(Paragraph(
                wrap(cell, maxc),
                ParagraphStyle("td", fontName="Helvetica", fontSize=8,
                               textColor=BLACK, leading=11)
            ))
        data_rows.append(data_row)
 
    if not data_rows:
        return p("No data found.", "small")
 
    t = Table([header_row] + data_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    return t
 
 
def generate_pdf(report, subject_name, subject_city, analyst=""):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"Identity Report — {subject_name}",
    )
 
    S = STYLES
    now = datetime.now().strftime("%d %b %Y, %H:%M")
    story = []
 
    # ── Header ────────────────────────────────────────────────────────────────
    header = Table(
        [[
            Paragraph("ETIL  Identity Research Report",
                      ParagraphStyle("brand", fontSize=13, textColor=WHITE,
                                     fontName="Helvetica-Bold")),
            Paragraph(
                f"<b>Subject:</b> {subject_name}<br/>"
                f"<b>Region:</b> {subject_city}<br/>"
                f"<b>Analyst:</b> {analyst or '—'}<br/>"
                f"<b>Date:</b> {now}",
                ParagraphStyle("meta", fontSize=8, textColor=WHITE,
                               fontName="Helvetica", alignment=TA_RIGHT,
                               leading=13))
        ]],
        colWidths=[100*mm, 74*mm]
    )
    header.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), BLUE),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (0, 0),   8*mm),
        ("RIGHTPADDING", (1, 0), (1, 0),   5*mm),
        ("TOPPADDING",   (0, 0), (-1, -1), 5*mm),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5*mm),
    ]))
    story.append(header)
    story.append(Spacer(1, 4*mm))
 
    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "CONFIDENTIAL — For internal compliance use only. Generated by AI from public sources. "
        "Human analyst review required before any decision. Do not distribute externally.",
        S["disc"]))
    story.append(Spacer(1, 4*mm))
 
    # ── Confidence Score ──────────────────────────────────────────────────────
    story.append(p("Identity Confidence", "h2"))
    score = int(report.get("confidence_score", 0))
    verdict = report.get("confidence_verdict", "Low")
    reasoning = report.get("confidence_reasoning", "")
    fg, bg = score_color(score)
 
    conf_table = Table(
        [[
            [Paragraph(str(score), ParagraphStyle(
                 "sn", fontSize=28, fontName="Helvetica-Bold",
                 textColor=fg, alignment=TA_CENTER, leading=32)),
             Paragraph("/ 100", ParagraphStyle(
                 "sl", fontSize=8, textColor=GRAY,
                 alignment=TA_CENTER))],
            [Paragraph(f"<b>{verdict} Confidence</b>",
                       ParagraphStyle("sv", fontSize=11, textColor=fg,
                                      fontName="Helvetica-Bold", leading=14,
                                      spaceAfter=3)),
             Paragraph(reasoning or "—",
                       ParagraphStyle("sr", fontSize=8.5, textColor=BLACK,
                                      leading=12))]
        ]],
        colWidths=[28*mm, 146*mm]
    )
    conf_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",           (0, 0), (-1, -1), 0.5, fg),
        ("LEFTPADDING",   (0, 0), (0, 0),   4*mm),
        ("LEFTPADDING",   (1, 0), (1, 0),   4*mm),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4*mm),
        ("TOPPADDING",    (0, 0), (-1, -1), 4*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
    ]))
    story.append(conf_table)
    story.append(Spacer(1, 4*mm))
 
    # ── Name Variations ───────────────────────────────────────────────────────
    variations = report.get("name_variations_searched", [])
    if variations:
        story.append(p("Name Variations Searched", "h2"))
        story.append(Paragraph(" · ".join(str(v) for v in variations), S["vars"]))
        story.append(Spacer(1, 4*mm))
 
    # ── Identity Matches ──────────────────────────────────────────────────────
    story.append(p("Identity Matches", "h2"))
    items = report.get("identity_matches", [])
    rows = [[m.get("name",""), m.get("description",""), m.get("confidence","").upper()]
            for m in items]
    story.append(make_table(
        ["Name", "Description", "Conf."],
        rows,
        [40*mm, 114*mm, 20*mm]
    ))
    story.append(Spacer(1, 4*mm))
 
    # ── Professional Profiles ─────────────────────────────────────────────────
    story.append(p("Professional Profiles", "h2"))
    items = report.get("professional_profiles", [])
    rows = [[p_.get("platform",""), p_.get("role",""),
             p_.get("company",""), p_.get("url_hint","")]
            for p_ in items]
    story.append(make_table(
        ["Platform", "Role", "Company", "URL"],
        rows,
        [28*mm, 42*mm, 42*mm, 62*mm]
    ))
    story.append(Spacer(1, 4*mm))
 
    # ── Business Records ──────────────────────────────────────────────────────
    story.append(p("Business Records", "h2"))
    items = report.get("business_records", [])
    rows = [[b.get("entity",""), b.get("role",""),
             b.get("status",""), b.get("source","")]
            for b in items]
    story.append(make_table(
        ["Entity", "Role", "Status", "Source"],
        rows,
        [50*mm, 36*mm, 28*mm, 60*mm]
    ))
    story.append(Spacer(1, 4*mm))
 
    # ── Media Mentions ────────────────────────────────────────────────────────
    story.append(p("Media Mentions", "h2"))
    items = report.get("media_mentions", [])
    rows = [[m.get("title",""), m.get("source",""), m.get("date",""),
             m.get("sentiment","").capitalize(), m.get("summary","")]
            for m in items]
    story.append(make_table(
        ["Title", "Source", "Date", "Sent.", "Summary"],
        rows,
        [44*mm, 24*mm, 18*mm, 14*mm, 74*mm]
    ))
    story.append(Spacer(1, 4*mm))
 
    # ── Social Media ──────────────────────────────────────────────────────────
    story.append(p("Social Media Presence", "h2"))
    items = report.get("social_media_presence", [])
    rows = [[s.get("platform",""), s.get("description","")]
            for s in items]
    story.append(make_table(
        ["Platform", "Description"],
        rows,
        [35*mm, 139*mm]
    ))
    story.append(Spacer(1, 4*mm))
 
    # ── Risk Flags ────────────────────────────────────────────────────────────
    story.append(p("Risk Flags", "h2"))
    flags = report.get("risk_flags", [])
    if not flags:
        story.append(Paragraph("✓ No risk flags identified.",
                                ParagraphStyle("ok", fontSize=9,
                                               textColor=GREEN,
                                               fontName="Helvetica-Bold")))
    else:
        for f in flags:
            fg2, bg2 = sev_color(f.get("severity", "low"))
            sev = f.get("severity", "low").upper()
            cat = f.get("category", "")
            desc = f.get("description", "")
            flag_row = Table(
                [[
                    Paragraph(f"[{sev}]",
                               ParagraphStyle("fs", fontSize=8,
                                              textColor=fg2,
                                              fontName="Helvetica-Bold")),
                    Paragraph(f"<b>{cat}</b> — {wrap(desc, 120)}",
                               ParagraphStyle("fd", fontSize=8.5,
                                              textColor=BLACK,
                                              leading=12))
                ]],
                colWidths=[20*mm, 154*mm]
            )
            flag_row.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), bg2),
                ("BOX",           (0, 0), (-1, -1), 0.4, fg2),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(flag_row)
            story.append(Spacer(1, 2))
 
    story.append(Spacer(1, 4*mm))
 
    # ── Sources ───────────────────────────────────────────────────────────────
    story.append(p("Sources Consulted", "h2"))
    items = report.get("sources", [])
    rows = [[s.get("name",""), s.get("url",""), s.get("type","")]
            for s in items]
    story.append(make_table(
        ["Name", "URL", "Type"],
        rows,
        [40*mm, 112*mm, 22*mm]
    ))
    story.append(Spacer(1, 6*mm))
 
    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.4, color=BORDER))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"Etil Identity Research Tool · {now} · Analyst: {analyst or '—'} · CONFIDENTIAL",
        S["foot"]
    ))
 
    doc.build(story)
    return buf.getvalue()
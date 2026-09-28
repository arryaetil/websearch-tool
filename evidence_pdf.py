"""Export the evidence-first draft without turning it into a risk decision."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def generate_evidence_pdf(report: dict, analyst: str = "") -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("Adverse media check: review draft", styles["Title"])]
    subject = report.get("subject", {})
    story.append(Paragraph(f"Subject: {escape(subject.get('name', ''))}", styles["Normal"]))
    story.append(Paragraph(f"City: {escape(subject.get('city', ''))}", styles["Normal"]))
    story.append(Paragraph(f"Employer clue: {escape(subject.get('employer', ''))}", styles["Normal"]))
    story.append(Paragraph(f"Analyst: {escape(analyst or 'Not specified')}", styles["Normal"]))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Requires human review before any decision.", styles["Heading2"]))
    story.append(Paragraph("Source assessments", styles["Heading2"]))
    for source in report.get("sources", []):
        story.append(Paragraph(escape(source.get("title") or source.get("url", "")), styles["Heading3"]))
        for label, value in (
            ("Identity", source.get("identity", "")),
            ("Reason", source.get("reason", "")),
            ("URL", source.get("url", "")),
            ("Retrieved", source.get("retrieved_at", "")),
        ):
            story.append(Paragraph(f"{label}: {escape(str(value))}", styles["Normal"]))
        for claim in source.get("claims", []):
            story.append(Paragraph(escape(claim.get("summary", "")), styles["Normal"]))
            story.append(Paragraph(f"Evidence: {escape(claim.get('quote', ''))}", styles["Normal"]))
        story.append(Spacer(1, 3 * mm))
    if not report.get("sources"):
        story.append(Paragraph("No readable sources found. Coverage is incomplete.", styles["Normal"]))
    doc.build(story)
    return buffer.getvalue()

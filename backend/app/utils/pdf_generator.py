import io
import os
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

logger = logging.getLogger("pdf_generator")

def draw_header_footer(canvas, doc):
    canvas.saveState()
    # Header Ribbon
    canvas.setFillColor(colors.HexColor("#60a5fa"))
    canvas.rect(0, 830, 297, 12, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#4f46e5"))
    canvas.rect(297, 830, 298, 12, fill=1, stroke=0)

    # Footer Ribbon
    canvas.setFillColor(colors.HexColor("#60a5fa"))
    p1 = canvas.beginPath()
    p1.moveTo(0, 0); p1.lineTo(200, 0); p1.lineTo(220, 15); p1.lineTo(0, 15); p1.close()
    canvas.drawPath(p1, stroke=0, fill=1)

    canvas.setFillColor(colors.HexColor("#4f46e5"))
    p2 = canvas.beginPath()
    p2.moveTo(200, 0); p2.lineTo(595.27, 0); p2.lineTo(595.27, 25); p2.lineTo(230, 25); p2.close()
    canvas.drawPath(p2, stroke=0, fill=1)

    # Logo and Branding
    logo_path = r"c:\Users\prabh\Desktop\MOM_AI_Assistant\B PNG.png"
    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            canvas.drawImage(logo, 30, 755, width=60, height=60, preserveAspectRatio=True, mask='auto')
            canvas.setStrokeColor(colors.HexColor("#1e293b"))
            canvas.setLineWidth(1.5)
            canvas.line(100, 760, 100, 805)
            canvas.setFillColor(colors.HexColor("#000000"))
            canvas.setFont("Helvetica-Bold", 24)
            canvas.drawString(110, 785, "Botivate")
            canvas.setFont("Helvetica-Oblique", 11)
            canvas.drawString(110, 770, "Powering Businesses")
            canvas.drawString(110, 757, "On Autopilot")
        except Exception as e:
            logger.warning(f"Could not draw logo: {e}")

    # Company Info (Right Aligned)
    canvas.setFillColor(colors.HexColor("#1e293b"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawRightString(565, 790, "BOTIVATE SERVICES LLP")
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(colors.HexColor("#4f46e5"))
    canvas.drawRightString(565, 775, "Shriram Business Park, Block-I ,")
    canvas.drawRightString(565, 762, "Office No- 224 , Vidhan Sabha Rd,")
    canvas.drawRightString(565, 749, "Raipur, Chhattisgarh 493111")

    # Divider Line
    canvas.setStrokeColor(colors.HexColor("#4f46e5"))
    canvas.setLineWidth(1.5)
    canvas.line(30, 735, 565, 735)

    # Footer Text
    canvas.setFillColor(colors.HexColor("#000000"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(30, 45, "HR Department / Intelligence Division")
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(30, 32, "Botivate Services LLP")

    canvas.restoreState()

def generate_any_pdf(title: str, subtitle: str, content: str) -> bytes:
    """Generate a Botivate-branded PDF for any text content."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=120, bottomMargin=120)

    styles = getSampleStyleSheet()
    h1_style = ParagraphStyle('BotivateH1', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#1e293b"), spaceAfter=12)
    h2_style = ParagraphStyle('BotivateH2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#334155"), spaceAfter=8, spaceBefore=12)
    normal_style = ParagraphStyle('BotivateNormal', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#475569"), leading=14, spaceAfter=6)

    elements = []
    elements.append(Paragraph(f"<b>{title.upper()}</b>", h1_style))
    if subtitle:
        elements.append(Paragraph(f"<i>{subtitle}</i>", normal_style))
    elements.append(Spacer(1, 20))

    # Process content paragraphs
    for line in content.split('\n'):
        if line.strip():
            # Basic bullet detection
            if line.strip().startswith('•') or line.strip().startswith('- '):
                elements.append(Paragraph(line.strip(), normal_style))
            elif line.strip().isupper() and len(line) < 50:
                 elements.append(Paragraph(f"<b>{line.strip()}</b>", h2_style))
            else:
                elements.append(Paragraph(line.strip(), normal_style))
        else:
            elements.append(Spacer(1, 10))

    doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

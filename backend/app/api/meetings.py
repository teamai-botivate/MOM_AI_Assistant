from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import os
import logging
from app.schemas.schemas import MeetingCreate, MeetingResponse, MeetingListResponse, MeetingMOMUpdate
from app.services.meeting_service import MeetingService
from app.notifications.notification_service import NotificationService
from app.models.models import AttendanceStatus


router = APIRouter()

# PDF endpoint
def draw_header_footer(canvas, doc):
    canvas.saveState()
    # PAGE DIMENSIONS
    # A4: 595.27 x 841.89
    
    # 1. Top Ribbon Vector
    # We will draw a blueish polygon at top left, and purple at top right
    canvas.setFillColor(colors.HexColor("#60a5fa")) # Light blue
    canvas.rect(0, 830, 297, 12, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#4f46e5")) # Indigo / Purple
    canvas.rect(297, 830, 298, 12, fill=1, stroke=0)
    
    # Bottom Ribbon Vector
    canvas.setFillColor(colors.HexColor("#60a5fa"))
    p1 = canvas.beginPath()
    p1.moveTo(0, 0)
    p1.lineTo(200, 0)
    p1.lineTo(220, 15)
    p1.lineTo(0, 15)
    p1.close()
    canvas.drawPath(p1, stroke=0, fill=1)
    
    canvas.setFillColor(colors.HexColor("#4f46e5"))
    p2 = canvas.beginPath()
    p2.moveTo(200, 0)
    p2.lineTo(595.27, 0)
    p2.lineTo(595.27, 25)
    p2.lineTo(230, 25)
    p2.close()
    canvas.drawPath(p2, stroke=0, fill=1)
    
    logo_path = r"c:\Users\prabh\Desktop\MOM_AI_Assistant\B PNG.png"
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        # Position logo at top left
        canvas.drawImage(logo, 30, 755, width=60, height=60, preserveAspectRatio=True, mask='auto')
        
        # Vertical logical separator line
        canvas.setStrokeColor(colors.HexColor("#1e293b"))
        canvas.setLineWidth(1.5)
        canvas.line(100, 760, 100, 805)

        # Draw Botivate text
        canvas.setFillColor(colors.HexColor("#000000"))
        canvas.setFont("Helvetica-Bold", 24)
        canvas.drawString(110, 785, "Botivate")
        
        canvas.setFont("Helvetica-Oblique", 11)
        canvas.drawString(110, 770, "Powering Businesses")
        canvas.drawString(110, 757, "On Autopilot")
    
    # Header Right Text
    canvas.setFillColor(colors.HexColor("#1e293b"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawRightString(565, 790, "BOTIVATE SERVICES LLP")
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(colors.HexColor("#4f46e5"))
    canvas.drawRightString(565, 775, "Shriram Business Park, Block-I ,")
    canvas.drawRightString(565, 762, "Office No- 224 , Vidhan Sabha Rd,")
    canvas.drawRightString(565, 749, "Raipur, Chhattisgarh 493111")
    
    # Header bottom border line
    canvas.setStrokeColor(colors.HexColor("#4f46e5"))
    canvas.setLineWidth(1.5)
    canvas.line(30, 735, 565, 735)

    # Footer Signature Area (draw on every page or last page ideally, but let's draw on all for template feel)
    # Footer Text
    canvas.setFillColor(colors.HexColor("#000000"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(30, 45, "HR Department")
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(30, 32, "Botivate Services LLP")
    
    canvas.restoreState()


def generate_meeting_pdf(meeting) -> tuple:
    """Generate a Botivate-branded MOM PDF in-memory. Returns (pdf_bytes, pdf_filename)."""
    import re as _re
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=40, leftMargin=40, 
        topMargin=120, bottomMargin=120
    )
    
    styles = getSampleStyleSheet()
    
    h1_style = ParagraphStyle(
        'BotivateH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'BotivateH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
        spaceBefore=12
    )
    normal_style = ParagraphStyle(
        'BotivateNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        leading=14,
        spaceAfter=6
    )
    
    table_style = TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#334155")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ])

    elements = []

    # Title & Subtitle
    elements.append(Paragraph(f"<b>MINUTES OF MEETING</b>", h1_style))
    elements.append(Paragraph(f"<b>Subject:</b> {meeting.title}", normal_style))
    elements.append(Spacer(1, 10))

    # Greeting
    elements.append(Paragraph(f"<b>Dear Team,</b>", normal_style))
    elements.append(Paragraph(
        f"Please find the details and minutes of the meeting <b>{meeting.title}</b> held on "
        f"<b>{meeting.date}</b> at <b>{meeting.time}</b> below:", 
        normal_style
    ))
    elements.append(Spacer(1, 10))

    # Basic Details (List style)
    org_name = meeting.organization or "Botivate Services LLP"
    elements.append(Paragraph(f"• <b>Organization:</b> {org_name}", normal_style))
    elements.append(Paragraph(f"• <b>Meeting Type:</b> {meeting.meeting_type or 'N/A'}", normal_style))
    elements.append(Paragraph(f"• <b>Meeting Mode:</b> {getattr(meeting, 'meeting_mode', 'N/A') or 'N/A'}", normal_style))
    elements.append(Paragraph(f"• <b>Venue/Location:</b> {meeting.venue or 'N/A'}", normal_style))
    elements.append(Paragraph(f"• <b>Hosted By:</b> {getattr(meeting, 'hosted_by', 'N/A') or 'N/A'}", normal_style))
    elements.append(Spacer(1, 10))

    # Next Meeting Details
    if meeting.next_meeting and (meeting.next_meeting.next_date or meeting.next_meeting.next_time):
        elements.append(Paragraph("<b>Schedule for Next Meeting</b>", h2_style))
        nd = meeting.next_meeting.next_date.strftime('%B %d, %Y') if hasattr(meeting.next_meeting.next_date, 'strftime') else str(meeting.next_meeting.next_date or 'TBD')
        nt = meeting.next_meeting.next_time.strftime('%I:%M %p') if hasattr(meeting.next_meeting.next_time, 'strftime') else str(meeting.next_meeting.next_time or 'TBD')
        elements.append(Paragraph(f"• <b>Date:</b> {nd}", normal_style))
        elements.append(Paragraph(f"• <b>Time:</b> {nt}", normal_style))
        elements.append(Spacer(1, 15))

    # Attendees
    elements.append(Paragraph("<b>Attendance</b>", h2_style))
    attendees_data = [["Name", "Email", "Status"]]
    for a in meeting.attendees:
        st = str(a.attendance_status).split('.')[-1].capitalize() if 'AttendanceStatus' in str(a.attendance_status) else str(a.attendance_status).capitalize()
        attendees_data.append([a.user_name, a.email or "N/A", st])
    if len(attendees_data) > 1:
        att_table = Table(attendees_data, colWidths=[180, 200, 100], hAlign='LEFT')
        att_table.setStyle(table_style)
        elements.append(att_table)
    else:
        elements.append(Paragraph("No attendees recorded.", normal_style))
    elements.append(Spacer(1, 10))

    # Agenda
    elements.append(Paragraph("<b>Agenda Items</b>", h2_style))
    if meeting.agenda_items:
        for idx, item in enumerate(meeting.agenda_items, 1):
            desc = f" - {item.description}" if item.description else ""
            elements.append(Paragraph(f"{idx}. {item.topic}{desc}", normal_style))
    else:
        elements.append(Paragraph("No agenda items.", normal_style))
    elements.append(Spacer(1, 10))

    # Discussion Summary
    elements.append(Paragraph("<b>Discussion Summary</b>", h2_style))
    if meeting.discussion and meeting.discussion.summary_text:
        for point in meeting.discussion.summary_text.split('\n'):
            if point.strip():
                elements.append(Paragraph(point.strip(), normal_style))
    else:
        elements.append(Paragraph("No discussion summary recorded.", normal_style))
    elements.append(Spacer(1, 10))

    # Action Items Table
    elements.append(Paragraph("<b>Action Items / Tasks</b>", h2_style))
    action_items_data = [["Task", "Responsible", "Deadline", "Status"]]
    for t in meeting.tasks:
        st = str(t.status).split('.')[-1].capitalize() if 'TaskStatus' in str(t.status) else str(t.status).capitalize()
        dl = t.deadline.strftime('%d-%m-%Y') if hasattr(t.deadline, 'strftime') else str(t.deadline or 'N/A')
        action_items_data.append([
            Paragraph(t.title, normal_style), 
            t.responsible_person or "N/A", 
            dl, 
            st
        ])
    if len(action_items_data) > 1:
        task_table = Table(action_items_data, colWidths=[200, 130, 80, 70], hAlign='LEFT')
        task_table.setStyle(table_style)
        elements.append(task_table)
    else:
        elements.append(Paragraph("No action items recorded.", normal_style))
    elements.append(Spacer(1, 15))

    # Next Meeting block moved to top

    # Build PDF
    doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    safe_title = _re.sub(r'[^a-zA-Z0-9_\-]', '_', meeting.title).strip('_')
    safe_date = str(meeting.date).replace('-', '') if meeting.date else 'NoDate'
    safe_time = str(meeting.time).replace(':', '') if meeting.time else 'NoTime'
    pdf_filename = f"MOM_{safe_title}_{safe_date}_{safe_time}.pdf"
    
    return pdf_bytes, pdf_filename


@router.get("/{meeting_id}/pdf", response_class=StreamingResponse)
async def download_meeting_pdf(meeting_id: int, db: AsyncSession = Depends(get_db)):
    try:
        meeting = await MeetingService.get_meeting(db, meeting_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error during meeting retrieval")
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    pdf_bytes, pdf_filename = generate_meeting_pdf(meeting)

    return StreamingResponse(
        io.BytesIO(pdf_bytes), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename={pdf_filename}"}
    )

# Meeting CRUD endpoints
@router.post("/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a meeting manually (Manual MOM creation)."""
    logger = logging.getLogger("meeting_creation")
    logger.info("Received meeting creation payload: %s", data.dict())
    try:
        meeting = await MeetingService.create_meeting(db, data, created_by=None)
        logger.info("Meeting created successfully: %s", meeting)
    except Exception as e:
        logger.error("Meeting creation failed: %s", str(e))
        raise

    # Reload with eager relationships to avoid lazy-load in async context
    meeting = await MeetingService.get_meeting(db, meeting.id)

    # Send notifications for the meeting invitation
    for attendee in meeting.attendees:
        if attendee.email:
            await NotificationService.notify_meeting_invitation(
                db, 
                email=attendee.email, 
                user_name=attendee.user_name, 
                meeting_title=meeting.title, 
                date=str(meeting.date) if meeting.date else "TBD", 
                time=str(meeting.time) if meeting.time else "TBD", 
                venue=meeting.venue or "TBD"
            )

    # Send notifications for created tasks
    for task in meeting.tasks:
        await NotificationService.notify_task_assigned(db, task, meeting.title)

    return meeting

@router.post("/{meeting_id}/mom", response_model=MeetingResponse)
async def add_mom_to_meeting(
    meeting_id: int,
    data: MeetingMOMUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Add MOM data (attendance, summary, tasks) to an existing scheduled meeting."""
    meeting = await MeetingService.add_mom_to_meeting(db, meeting_id, data)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Generate task HTML for summary
    task_html = ""
    if meeting.tasks:
        task_html = "<table style='border-collapse:collapse;width:100%;margin:16px 0;'><tr style='background:#f0f4f8;'><th style='padding:10px;text-align:left;'>Task</th><th style='padding:10px;text-align:left;'>Owner</th><th style='padding:10px;text-align:left;'>Deadline</th></tr>"
        for t in meeting.tasks:
            task_html += f"<tr><td style='padding:10px;border-bottom:1px solid #e0e0e0;'>{t.title}</td><td style='padding:10px;border-bottom:1px solid #e0e0e0;'>{t.responsible_person or 'None'}</td><td style='padding:10px;border-bottom:1px solid #e0e0e0;'>{t.deadline or 'None'}</td></tr>"
        task_html += "</table>"
    else:
        task_html = "<p>No tasks assigned.</p>"

    # Generate the MOM PDF to attach to emails
    pdf_data, pdf_name = generate_meeting_pdf(meeting)

    # Send MOM summary and task notifications (with PDF attachment)
    for attendee in meeting.attendees:
        if attendee.email:
            is_absent = (attendee.attendance_status != AttendanceStatus.PRESENT)
            await NotificationService.notify_meeting_summary(
                db,
                email=attendee.email,
                user_name=attendee.user_name,
                meeting_title=meeting.title,
                is_absent=is_absent,
                summary=meeting.discussion.summary_text if meeting.discussion else "",
                task_html=task_html,
                pdf_data=pdf_data,
                pdf_name=pdf_name,
                remarks=getattr(attendee, "remarks", None)
            )

    # Note: Task assignments specifically sent for NEW tasks. We just created these tasks above, so we send.
    for task in data.tasks:
        # Need the actual DB Task object to pass to notify_task_assigned, but we can just find it by title
        db_task = next((t for t in meeting.tasks if t.title == task.title), None)
        if db_task:
            await NotificationService.notify_task_assigned(db, db_task, meeting.title)

    return meeting


@router.get("/", response_model=list[MeetingListResponse])
async def list_meetings(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    """List meetings."""
    meetings = await MeetingService.list_meetings(db, skip=skip, limit=limit)
    # Ensure tasks are loaded and count is correct
    return [
        MeetingListResponse(
            id=m.id,
            title=m.title,
            organization=m.organization,
            date=m.date,
            time=m.time,
            venue=m.venue,
            created_at=m.created_at,
            task_count=len(m.tasks) if hasattr(m, 'tasks') and m.tasks is not None else 0,
        )
        for m in meetings
    ]

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    meeting = await MeetingService.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting

@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await MeetingService.delete_meeting(db, meeting_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"detail": "Meeting deleted"}

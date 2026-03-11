"""File upload and AI extraction endpoint – the heart of the MOM pipeline."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.session import get_db
from app.schemas.schemas import MeetingResponse, ExtractedMOM
from app.services.file_service import FileService
from app.services.meeting_service import MeetingService
from app.notifications.notification_service import NotificationService
from app.workflows.mom_workflow import get_mom_workflow

settings = get_settings()
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


@router.post("/mom", response_model=MeetingResponse)
async def upload_and_process_mom(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a MOM file (PDF/TXT), run through AI extraction pipeline, and save."""

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

    # Validate file size
    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

    # Save file
    file_path = await FileService.save_upload(content, file.filename)

    # Run LangGraph workflow
    try:
        workflow = get_mom_workflow()
        result = await workflow.ainvoke({"file_path": file_path})

        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])

        extracted_mom: ExtractedMOM = result.get("extracted_mom")
        if not extracted_mom:
            raise HTTPException(status_code=422, detail="AI extraction returned no data")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing pipeline failed: {str(e)}")

    # Save to database
    meeting = await MeetingService.create_from_extraction(
        db, extracted_mom, created_by=None, file_path=file_path
    )

    # Reload with all relationships before accessing them
    meeting = await MeetingService.get_meeting(db, meeting.id)

    # Notify task assignees
    for task in meeting.tasks:
        await NotificationService.notify_task_assigned(db, task, meeting.title)

    return meeting


@router.post("/extract-preview", response_model=ExtractedMOM)
async def preview_extraction(
    file: UploadFile = File(...),
):
    """Upload a file and preview AI extraction without saving."""

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    content = await file.read()
    file_path = await FileService.save_upload(content, file.filename)

    try:
        workflow = get_mom_workflow()
        result = await workflow.ainvoke({"file_path": file_path})

        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])

        extracted = result.get("extracted_mom")
        if not extracted:
            raise HTTPException(status_code=422, detail="Extraction returned no data")

        return extracted
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        # Clean up temp file for preview
        try:
            os.remove(file_path)
        except OSError:
            pass

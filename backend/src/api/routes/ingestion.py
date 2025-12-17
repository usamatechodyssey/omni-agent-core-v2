
import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# --- Security Imports ---
from backend.src.api.routes.deps import get_current_user
from backend.src.models.user import User

# --- Internal Services & DB Imports ---
from backend.src.services.ingestion.file_processor import process_file
from backend.src.services.ingestion.crawler import SmartCrawler 
from backend.src.services.ingestion.zip_processor import SmartZipProcessor
from backend.src.db.session import get_db, AsyncSessionLocal
from backend.src.models.ingestion import IngestionJob, JobStatus, IngestionType

# --- CONFIG ---
MAX_ZIP_SIZE_MB = 100
MAX_ZIP_SIZE_BYTES = MAX_ZIP_SIZE_MB * 1024 * 1024

router = APIRouter()
UPLOAD_DIRECTORY = "./uploaded_files"

# ==========================================
# FILE UPLOAD (Protected)
# ==========================================
@router.post("/ingest/upload")
async def upload_and_process_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user) # <--- 🔒 TALA LAGA DIYA
):
    # (Function logic same rahegi, bas ab current_user mil jayega)
    if not os.path.exists(UPLOAD_DIRECTORY):
        os.makedirs(UPLOAD_DIRECTORY)

    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        chunks_added = await process_file(file_path, session_id)
        if chunks_added <= 0:
            raise HTTPException(status_code=400, detail="Could not process file.")
        
        return {
            "message": "File processed successfully",
            "filename": file.filename,
            "chunks_added": chunks_added,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# ==========================================
# WEB CRAWLER (Protected)
# ==========================================
class WebIngestRequest(BaseModel):
    url: str
    session_id: str
    crawl_type: str = "single_page"

async def run_crawler_task(job_id, url, session_id, crawl_type, db_factory):
    async with db_factory() as db:
        crawler = SmartCrawler(job_id, url, session_id, crawl_type, db)
        await crawler.start()

@router.post("/ingest/url")
async def start_web_ingestion(
    request: WebIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- 🔒 TALA LAGA DIYA
):
    # (Function logic same rahegi)
    new_job = IngestionJob(
        session_id=request.session_id,
        ingestion_type=IngestionType.URL,
        source_name=request.url,
        status=JobStatus.PENDING
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    background_tasks.add_task(run_crawler_task, new_job.id, request.url, request.session_id, request.crawl_type, AsyncSessionLocal)
    return {"message": "Ingestion job started", "job_id": new_job.id}

@router.get("/ingest/status/{job_id}")
async def check_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- 🔒 TALA LAGA DIYA
):
    # (Function logic same rahegi)
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# ==========================================
# BULK ZIP UPLOAD (Protected)
# ==========================================
async def run_zip_task(job_id, zip_path, session_id, db_factory):
    async with db_factory() as db:
        processor = SmartZipProcessor(job_id, zip_path, session_id, db)
        await processor.start()

@router.post("/ingest/upload-zip")
async def upload_and_process_zip(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) # <--- 🔒 TALA LAGA DIYA
):
    # (Function logic same rahegi)
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed.")
    if file.size > MAX_ZIP_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {MAX_ZIP_SIZE_MB} MB.")

    zip_dir = os.path.join(UPLOAD_DIRECTORY, "zips")
    os.makedirs(zip_dir, exist_ok=True)
    file_path = os.path.join(zip_dir, f"job_{session_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_job = IngestionJob(
        session_id=session_id,
        ingestion_type=IngestionType.ZIP,
        source_name=file.filename,
        status=JobStatus.PENDING
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    background_tasks.add_task(run_zip_task, new_job.id, file_path, session_id, AsyncSessionLocal)
    return {"message": "Zip processing started", "job_id": new_job.id}
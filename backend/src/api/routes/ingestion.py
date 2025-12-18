import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# --- Security & User Context ---
from backend.src.api.routes.deps import get_current_user
from backend.src.models.user import User

# --- Internal Services ---
from backend.src.services.ingestion.file_processor import process_file
from backend.src.services.ingestion.crawler import SmartCrawler 
from backend.src.services.ingestion.zip_processor import SmartZipProcessor
from backend.src.db.session import get_db, AsyncSessionLocal
from backend.src.models.ingestion import IngestionJob, JobStatus, IngestionType

# --- CONFIG ---
MAX_ZIP_SIZE_MB = 100
MAX_ZIP_SIZE_BYTES = MAX_ZIP_SIZE_MB * 1024 * 1024
UPLOAD_DIRECTORY = "./uploaded_files"

router = APIRouter()

# ==========================================
# 1. INDIVIDUAL FILE UPLOAD (Secure ✅)
# ==========================================
@router.post("/ingest/upload")
async def upload_and_process_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db), # DB session add ki
    current_user: User = Depends(get_current_user) 
):
    if not os.path.exists(UPLOAD_DIRECTORY):
        os.makedirs(UPLOAD_DIRECTORY)

    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    try:
        # File temporary save karein
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 🚀 PASSING USER CONTEXT: process_file ab user_id aur db mang raha hai
        chunks_added = await process_file(
            file_path=file_path, 
            session_id=session_id, 
            user_id=str(current_user.id), 
            db=db
        )

        if chunks_added == -1: # Database not connected error
            raise HTTPException(status_code=400, detail="Database not connected. Please go to User Settings first.")
        elif chunks_added <= 0:
            raise HTTPException(status_code=400, detail="Could not extract content from file.")
        
        return {
            "status": "success",
            "filename": file.filename,
            "chunks": chunks_added,
            "owner_id": current_user.id
        }
    except HTTPException as he: raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path): os.remove(file_path)

# ==========================================
# 2. WEB CRAWLER (Secure Background Task ✅)
# ==========================================
class WebIngestRequest(BaseModel):
    url: str
    session_id: str
    crawl_type: str = "single_page"

# Helper to run crawler in background with User ID
async def run_crawler_task(job_id, url, session_id, crawl_type, db_factory, user_id):
    async with db_factory() as db:
        # 🚀 PASSING USER ID: Crawler ko bataya kis ka data hai
        crawler = SmartCrawler(job_id, url, session_id, crawl_type, db, user_id=user_id)
        await crawler.start()

@router.post("/ingest/url")
async def start_web_ingestion(
    request: WebIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_job = IngestionJob(
        session_id=request.session_id,
        ingestion_type=IngestionType.URL,
        source_name=request.url,
        status=JobStatus.PENDING
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # 🚀 BACKGROUND LINK: Pass user_id to the task
    background_tasks.add_task(
        run_crawler_task, 
        new_job.id, request.url, request.session_id, request.crawl_type, 
        AsyncSessionLocal, str(current_user.id)
    )
    return {"message": "Crawler started securely", "job_id": new_job.id}

# ==========================================
# 3. BULK ZIP UPLOAD (Secure Background Task ✅)
# ==========================================
async def run_zip_task(job_id, zip_path, session_id, db_factory, user_id):
    async with db_factory() as db:
        # 🚀 PASSING USER ID: Zip processor ab owner-aware hai
        processor = SmartZipProcessor(job_id, zip_path, session_id, db, user_id=user_id)
        await processor.start()

@router.post("/ingest/upload-zip")
async def upload_and_process_zip(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Invalid format. ZIP only.")

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

    # 🚀 BACKGROUND LINK: Pass user_id to the task
    background_tasks.add_task(
        run_zip_task, 
        new_job.id, file_path, session_id, 
        AsyncSessionLocal, str(current_user.id)
    )
    return {"message": "Secure Zip processing scheduled", "job_id": new_job.id}

# ==========================================
# 4. STATUS CHECKER (Secure ✅)
# ==========================================
@router.get("/ingest/status/{job_id}")
async def check_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only allow users to see their own session jobs? (Optional improvement)
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
import zipfile
import os
import shutil
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.src.models.ingestion import IngestionJob, JobStatus
from backend.src.models.integration import UserIntegration # SaaS Logic
from backend.src.services.ingestion.file_processor import process_file
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from qdrant_client.http import models

SUPPORTED_EXTENSIONS = ['.pdf', '.txt', '.md', '.docx', '.csv']
MAX_FILES_IN_ZIP = 500

class SmartZipProcessor:
    # 1. Init mein 'user_id' add kiya
    def __init__(self, job_id: int, zip_path: str, session_id: str, db: AsyncSession, user_id: str):
        self.job_id = job_id
        self.zip_path = zip_path
        self.session_id = session_id
        self.db = db
        self.user_id = user_id # Owner ID
        self.vector_store = None # Verification ke baad initialize hoga
        self.temp_dir = f"./temp_unzip_{job_id}"
        self.report = []

    async def log_status(self, status: str, processed=0, total=0, error=None):
        try:
            # SQL Alchemy 2.0 style query
            result = await self.db.execute(select(IngestionJob).where(IngestionJob.id == self.job_id))
            job = result.scalars().first()
            if job:
                job.status = status
                job.items_processed = processed
                job.total_items = total
                job.details = self.report
                if error:
                    job.error_message = str(error)
                await self.db.commit()
        except Exception as e:
            print(f"DB Log Error: {e}")

    # --- NEW: SaaS DATABASE VERIFICATION ---
    async def verify_and_connect_db(self) -> bool:
        """
        ZIP processing se pehle check karo ke user ka Qdrant Cloud connected hai ya nahi.
        """
        print(f"🔍 Verifying Database for ZIP Processing. User ID: {self.user_id}")
        try:
            stmt = select(UserIntegration).where(
                UserIntegration.user_id == str(self.user_id),
                UserIntegration.provider == "qdrant",
                UserIntegration.is_active == True
            )
            result = await self.db.execute(stmt)
            integration = result.scalars().first()

            if not integration:
                error_msg = "❌ No Qdrant Cloud connected. Cannot process ZIP."
                await self.log_status(JobStatus.FAILED, error=error_msg)
                return False

            # Extract Credentials
            creds = json.loads(integration.credentials) if isinstance(integration.credentials, str) else integration.credentials
            
            # Smart Adapter ko user ki chabiyan bhejien (No Fallback)
            self.vector_store = get_vector_store(credentials=creds)
            return True

        except Exception as e:
            print(f"❌ DB Verification Failed: {e}")
            return False

    async def clean_existing_data(self):
        """SaaS Logic: Sirf is session aur is user ka purana data delete karo"""
        print(f"INFO: Cleaning old data for session: {self.session_id}")
        try:
            self.vector_store.client.delete(
                collection_name=self.vector_store.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="metadata.session_id",
                                match=models.MatchValue(value=self.session_id)
                            ),
                            # SECURITY: Ensure we only delete THIS user's data
                            models.FieldCondition(
                                key="metadata.user_id",
                                match=models.MatchValue(value=str(self.user_id))
                            )
                        ]
                    )
                )
            )
        except Exception as e:
            print(f"Warning: Clean data failed: {e}")

    def inspect_zip(self) -> list:
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            file_list = zf.infolist()
            if len(file_list) > MAX_FILES_IN_ZIP:
                raise ValueError(f"Zip too large: {len(file_list)} files.")
            return [f for f in file_list if not f.is_dir()]

    def extract_zip(self):
        os.makedirs(self.temp_dir, exist_ok=True)
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            zf.extractall(self.temp_dir)

    def cleanup(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.zip_path):
            os.remove(self.zip_path)

    async def start(self):
        try:
            # 1. PEHLA KAAM: Database check
            db_ready = await self.verify_and_connect_db()
            if not db_ready: return

            files_to_process = self.inspect_zip()
            total_files = len(files_to_process)
            await self.log_status(JobStatus.PROCESSING, total=total_files)

            # 2. Atomic Clean
            await self.clean_existing_data()

            # 3. Extract
            self.extract_zip()

            # 4. Loop through files
            processed_count = 0
            for file_info in files_to_process:
                file_path = os.path.join(self.temp_dir, file_info.filename)
                
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    self.report.append({"file": file_info.filename, "status": "skipped", "reason": "unsupported_type"})
                    continue
                
                try:
                    # process_file (jo humne pehle update kiya tha) ko call karo
                    # Ab isko 'user_id' aur 'db' session bhi bhej rahe hain 🚀
                    chunks_added = await process_file(
                        file_path=file_path, 
                        session_id=self.session_id, 
                        user_id=self.user_id, 
                        db=self.db
                    )
                    
                    if chunks_added == -1: # No Database error from process_file
                        raise ValueError("Database connection lost or not configured.")
                    elif chunks_added > 0:
                        self.report.append({"file": file_info.filename, "status": "success", "chunks": chunks_added})
                    else:
                        raise ValueError("No content extracted")
                except Exception as e:
                    self.report.append({"file": file_info.filename, "status": "failed", "reason": str(e)})
                
                processed_count += 1
                await self.log_status(JobStatus.PROCESSING, processed=processed_count, total=total_files)
                await asyncio.sleep(0.05) 

            await self.log_status(JobStatus.COMPLETED, processed=processed_count, total=total_files)
            print(f"SUCCESS: Secure Zip ingestion complete.")

        except Exception as e:
            print(f"ERROR: Zip processing failed: {e}")
            await self.log_status(JobStatus.FAILED, error=str(e))
        finally:
            self.cleanup()
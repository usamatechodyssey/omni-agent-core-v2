import zipfile
import os
import shutil
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.models.ingestion import IngestionJob, JobStatus
from backend.src.services.ingestion.file_processor import process_file
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from qdrant_client.http import models

# --- CONFIGURATION ---
SUPPORTED_EXTENSIONS = ['.pdf', '.txt', '.md', '.docx', '.csv']
MAX_FILES_IN_ZIP = 500

class SmartZipProcessor:
    def __init__(self, job_id: int, zip_path: str, session_id: str, db: AsyncSession):
        self.job_id = job_id
        self.zip_path = zip_path
        self.session_id = session_id
        self.db = db
        self.vector_store = get_vector_store()
        self.temp_dir = f"./temp_unzip_{job_id}"
        self.report = []

    async def log_status(self, status: str, processed=0, total=0, error=None):
        """Database mein job status update karta hai"""
        try:
            job = await self.db.get(IngestionJob, self.job_id)
            if job:
                job.status = status
                job.items_processed = processed
                job.total_items = total
                job.details = self.report # Report bhi save karo
                if error:
                    job.error_message = str(error)
                await self.db.commit()
        except Exception as e:
            print(f"DB Log Error: {e}")

    async def clean_existing_data(self):
        """Update Logic: Is session ka purana data saaf karo"""
        print(f"INFO: Cleaning old data for session_id: {self.session_id}")
        try:
            self.vector_store.client.delete(
                collection_name=self.vector_store.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="metadata.session_id",
                                match=models.MatchValue(value=self.session_id)
                            )
                        ]
                    )
                )
            )
        except Exception as e:
            print(f"Warning: Clean data failed (maybe first upload): {e}")

    def inspect_zip(self) -> list:
        """Zip ko bina extract kiye check karta hai"""
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            file_list = zf.infolist()
            
            # Guardrail 1: File Count
            if len(file_list) > MAX_FILES_IN_ZIP:
                raise ValueError(f"Zip contains too many files ({len(file_list)}). Max allowed is {MAX_FILES_IN_ZIP}.")
            
            # Sirf "Files" return karo, folders nahi
            return [f for f in file_list if not f.is_dir()]

    def extract_zip(self):
        """Zip ko temp folder mein extract karta hai"""
        os.makedirs(self.temp_dir, exist_ok=True)
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            zf.extractall(self.temp_dir)

    def cleanup(self):
        """Temp files/folders delete karta hai"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.zip_path):
            os.remove(self.zip_path)

    async def start(self):
        """Main Processing Loop"""
        try:
            # Step 1: Inspect
            files_to_process = self.inspect_zip()
            total_files = len(files_to_process)
            await self.log_status(JobStatus.PROCESSING, total=total_files)

            # Step 2: Clean old data (Atomic Update)
            await self.clean_existing_data()

            # Step 3: Extract
            self.extract_zip()

            # Step 4: Process each file
            processed_count = 0
            for file_info in files_to_process:
                file_path = os.path.join(self.temp_dir, file_info.filename)
                
                # Guardrail 2: Supported Extension
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    self.report.append({"file": file_info.filename, "status": "skipped", "reason": "unsupported_type"})
                    continue
                
                # Process the file
                try:
                    # process_file (jo humne pehle banaya tha) ko call karo
                    chunks_added = await process_file(file_path, self.session_id)
                    if chunks_added > 0:
                        self.report.append({"file": file_info.filename, "status": "success", "chunks": chunks_added})
                    else:
                        raise ValueError("No content extracted")
                except Exception as e:
                    self.report.append({"file": file_info.filename, "status": "failed", "reason": str(e)})
                
                processed_count += 1
                await self.log_status(JobStatus.PROCESSING, processed=processed_count, total=total_files)
                await asyncio.sleep(0.1) # Thoda saans lene do

            await self.log_status(JobStatus.COMPLETED, processed=processed_count, total=total_files)
            print(f"SUCCESS: Zip processing finished. Processed {processed_count}/{total_files} files.")

        except Exception as e:
            print(f"ERROR: Zip processing failed: {e}")
            await self.log_status(JobStatus.FAILED, error=str(e))
        finally:
            self.cleanup()
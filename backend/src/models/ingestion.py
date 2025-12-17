from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON # <--- JSON import karein
from sqlalchemy.sql import func
import enum
from backend.src.db.base import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    
class IngestionType(str, enum.Enum):
    URL = "url"
    ZIP = "zip"
    FILE = "file" # (Future use ke liye)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    
    # --- NEW COLUMNS ---
    ingestion_type = Column(String, default=IngestionType.URL) # Taake pata chale ye URL hai ya Zip
    source_name = Column(String, nullable=False) # Ye URL ya Zip file ka naam hoga
    
    status = Column(String, default=JobStatus.PENDING)
    
    # Progress Tracking
    items_processed = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    
    # Detailed Logging
    details = Column(JSON, default=[]) # <--- Har file ka result yahan aayega
    
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 'url', 'crawl_type' waghaira columns hata diye taake table generic rahe

from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from backend.src.db.base import Base
from backend.src.utils.security import SecurityUtils

class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True) 
    
    provider = Column(String, nullable=False) # e.g., 'sanity', 'sql', 'mongodb'
    
    # Store encrypted credentials
    _credentials = Column("credentials", Text, nullable=False)
    
    # The Map (Technical Structure)
    schema_map = Column(JSON, default={})

    # --- NEW COLUMN: The semantic description of the data ---
    profile_description = Column(Text, nullable=True) 
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def credentials(self):
        return SecurityUtils.decrypt(self._credentials)

    @credentials.setter
    def credentials(self, value):
        self._credentials = SecurityUtils.encrypt(value)
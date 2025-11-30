# app/models/api_connection.py
from typing import Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from typing import Optional, Dict, Any 
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db_setup import Base
from pydantic import BaseModel


class ApiConnection(Base):
    __tablename__ = 'api_connections'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)  # Fixed to match user table name
    provider = Column(String(50), nullable=False)  # np. 'google_fit', 'strava', itp.

    # Access tokens
    access_token = Column(String)
    refresh_token = Column(String)
    token_expires_at = Column(DateTime)

    # Additional connection data (state, etc.)
    connection_data = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Define the relationship from this side
    user = relationship("User", back_populates="api_connections")


# Schematy Pydantic
class ApiConnectionCreate(BaseModel):
    provider: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    connection_data: Optional[Dict[str, Any]] = None


class ApiConnectionResponse(BaseModel):
    id: int
    provider: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

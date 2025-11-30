# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from database.db_setup import Base
from datetime import datetime
# Import your models or use fully qualified name
from app.models.transaction import Transaction 
from app.models.health import HeartRate, Sleep, Activity
from pydantic import BaseModel, EmailStr
from typing import Optional

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    # Relationships - use the imported class or fully qualified name
    transactions = relationship("Transaction", back_populates="user")
    api_connections = relationship("ApiConnection", back_populates="user")
    heart_rates = relationship('HeartRate', back_populates='user')
    sleep = relationship('Sleep', back_populates='user')
    activity = relationship('Activity', back_populates='user')


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

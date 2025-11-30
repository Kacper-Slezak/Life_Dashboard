from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from database.db_setup import Base

class HeartRate(Base):
    __tablename__ = 'heart_rate'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    bpm_value = Column(Integer, nullable=False)

    user = relationship('User', back_populates='heart_rates')


class Sleep(Base):
    __tablename__ = 'sleep'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    sleep_value = Column(Integer, nullable=False)

    user = relationship('User', back_populates='sleep')


class Activity(Base):
    __tablename__ = 'activity'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    activity_type = Column(String, nullable=False)
    duration = Column(Float, nullable=False)
    calories = Column(Integer, nullable=False)

    user = relationship('User', back_populates='activity')

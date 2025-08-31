"""
Database models for FocusFlow Enterprise
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="user")
    pomodoro_sessions = relationship("PomodoroSession", back_populates="user")
    time_entries = relationship("TimeEntry", back_populates="user")
    analytics = relationship("UserAnalytics", back_populates="user", uselist=False)

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="pending")  # pending, in_progress, completed, cancelled
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    estimated_pomodoros = Column(Integer, default=1)
    completed_pomodoros = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    pomodoro_sessions = relationship("PomodoroSession", back_populates="task")

class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    duration = Column(Integer, default=25)  # Duration in minutes
    focus_score = Column(Float, default=0.8)  # 0.0 to 1.0
    interrupted = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="pomodoro_sessions")
    task = relationship("Task", back_populates="pomodoro_sessions")

class TimeEntry(Base):
    __tablename__ = "time_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    duration = Column(Integer)  # Duration in minutes
    description = Column(Text)
    entry_type = Column(String(20), default="work")  # work, break, meeting, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="time_entries")

class UserAnalytics(Base):
    __tablename__ = "user_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_sessions = Column(Integer, default=0)
    total_focus_time = Column(Integer, default=0)  # Total minutes
    avg_focus_score = Column(Float, default=0.0)
    productivity_trend = Column(Float, default=0.0)  # -1.0 to 1.0
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional analytics fields
    weekly_sessions = Column(Integer, default=0)
    monthly_sessions = Column(Integer, default=0)
    best_focus_hour = Column(Integer, default=9)  # Hour of day (0-23)
    avg_session_duration = Column(Float, default=25.0)
    interruption_rate = Column(Float, default=0.1)  # Percentage of interrupted sessions
    
    # Relationships
    user = relationship("User", back_populates="analytics")
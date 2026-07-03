from sqlalchemy import Column, Float, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    experience_years = Column(Integer, nullable=True)
    education = Column(String, nullable=True)
    skills = Column(Text, nullable=True)
    resume_path = Column(String, nullable=True)
    profile_summary = Column(Text, nullable=True)

    sessions = relationship("InterviewSession", back_populates="candidate")
    
class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    role = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    overall_score = Column(Float, nullable=True)
    status = Column(String, default="in_progress")

    candidate = relationship("Candidate", back_populates="sessions")
    question_answers = relationship("QuestionAnswer", back_populates="session")

class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    evaluation = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    evaluation_timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="question_answers")

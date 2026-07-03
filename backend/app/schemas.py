from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    resume_path: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[str] = None
    profile_summary: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None


class CandidateResponse(CandidateCreate):
    id: int

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    candidate_id: int
    role: str


class SessionResponse(BaseModel):
    id: int
    candidate_id: int
    role: str
    start_time: datetime
    end_time: Optional[datetime] = None
    overall_score: Optional[float] = None
    status: str
    current_question: int = 1

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    question_number: int
    total_questions: int
    question_text: str
    session_id: int
    question_id: int


class AnswerSubmit(BaseModel):
    answer_text: str
    question_id: int


class AnswerResponse(BaseModel):
    question_id: int
    question_text: str
    answer_text: str
    score: float
    feedback: str
    is_last: bool
    next_question: Optional[QuestionResponse] = None
    source_chunks: List[str]


class QARecord(BaseModel):
    question: str
    answer: str
    score: float
    evaluation: str
    source_chunks: List[str]


class SessionSummary(BaseModel):
    session_id: int
    candidate_name: str
    role: str
    overall_score: float
    status: str
    total_questions: int
    questions: List[QARecord]
    insights: str
    completed_at: datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .config import settings
from .database import engine, Base, get_db
from . import models
from .schemas import CandidateCreate, Candidate, InterviewSessionCreate, InterviewSession

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Powered Candidate Screening System",
    description="Interactive system for evaluating candidates for technical roles",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the AI-Powered Candidate Screening System API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/candidates/", response_model=Candidate)
def create_candidate(candidate: CandidateCreate, db: Session = Depends(get_db)):
    db_candidate = models.Candidate(**candidate.model_dump())
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate


@app.get("/candidates/", response_model=List[Candidate])
def list_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    candidates = db.query(models.Candidate).offset(skip).limit(limit).all()
    return candidates


@app.post("/sessions/", response_model=InterviewSession)
def create_session(session: InterviewSessionCreate, db: Session = Depends(get_db)):
    db_session = models.InterviewSession(**session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


@app.get("/sessions/", response_model=List[InterviewSession])
def list_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sessions = db.query(models.InterviewSession).offset(skip).limit(limit).all()
    return sessions
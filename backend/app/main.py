import json
import re
from pathlib import Path
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .config import settings
from .database import engine, Base, get_db
from . import models
from .schemas import (
    CandidateCreate,
    CandidateResponse,
    SessionCreate,
    SessionResponse,
    QuestionResponse,
    AnswerSubmit,
    AnswerResponse,
    QARecord,
    SessionSummary,
    UserSignup,
    Token
)
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from .services.resume_parser import ResumeParserService
from .services.rag_engine import RAGEngine
from .services.interview_manager import InterviewManager

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Powered Candidate Screening System",
    description="Interactive system for evaluating candidates for technical roles",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

resume_parser = ResumeParserService()

# In-memory session store: session_id -> (rag_engine, manager, qa_history)
# qa_history items: {"db_id": int, "chunks": list, "score": float | None}
active_sessions: dict[int, tuple[RAGEngine, InterviewManager, list]] = {}

# Absolute uploads directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"


# ---------------------------------------------------------------------------
# Basic routes
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI-Powered Candidate Screening System API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Candidate CRUD
# ---------------------------------------------------------------------------

@app.post("/candidates/", response_model=CandidateResponse, status_code=201)
def create_candidate(candidate: CandidateCreate, db: Session = Depends(get_db)):
    db_candidate = models.Candidate(**candidate.model_dump())
    db.add(db_candidate)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Candidate with email '{candidate.email}' already exists",
        )
    db.refresh(db_candidate)
    return db_candidate


@app.get("/candidates/", response_model=List[CandidateResponse])
def list_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    candidates = db.query(models.Candidate).offset(skip).limit(limit).all()
    return candidates


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

@app.get("/sessions/history", response_model=List[SessionResponse])
def get_user_history(db: Session = Depends(get_db), current_user: models.Candidate = Depends(get_current_user)):
    sessions = db.query(models.InterviewSession).filter_by(candidate_id=current_user.id).order_by(models.InterviewSession.start_time.desc()).all()
    return [
        SessionResponse(
            id=s.id,
            candidate_id=s.candidate_id,
            role=s.role,
            start_time=s.start_time,
            end_time=s.end_time,
            overall_score=s.overall_score,
            status=s.status,
            current_question=5 if s.status == "completed" else 1,
        )
        for s in sessions
    ]


@app.post("/auth/signup", status_code=201, response_model=CandidateResponse)
def signup(user: UserSignup, db: Session = Depends(get_db)):
    existing_user = db.query(models.Candidate).filter(models.Candidate.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = get_password_hash(user.password)
    new_candidate = models.Candidate(
        name=user.name,
        email=user.email,
        hashed_password=hashed_pwd
    )
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)
    return new_candidate

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Candidate).filter(models.Candidate.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# ---------------------------------------------------------------------------
# Resume upload
# ---------------------------------------------------------------------------

@app.post("/upload-resume", status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Candidate = Depends(get_current_user)
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # sanitize filename to prevent path traversal
    raw_name = file.filename or "resume"
    safe_name = re.sub(r"[^\w\-.]", "_", raw_name)
    file_path = UPLOAD_DIR / safe_name

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    file_path.write_bytes(content)

    profile = await resume_parser.process_resume(str(file_path), safe_name)
    current_user.resume_path = str(file_path)
    current_user.skills = profile.get("skills", "")
    current_user.experience_years = profile.get("experience_years", 0)
    current_user.education = profile.get("education", "")
    current_user.profile_summary = profile.get("profile_summary", "")
    current_user.phone = profile.get("phone", current_user.phone)
    current_user.location = profile.get("location", current_user.location)

    db.commit()
    db.refresh(current_user)

    return {"candidate_id": current_user.id, "profile": profile}


# ---------------------------------------------------------------------------
# Interview flow
# ---------------------------------------------------------------------------

@app.post("/sessions/start", response_model=SessionResponse, status_code=201)
async def start_session(
    session_data: SessionCreate, 
    db: Session = Depends(get_db),
    current_user: models.Candidate = Depends(get_current_user)
):
    if session_data.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to start session for this candidate")
    candidate = db.query(models.Candidate).filter_by(id=session_data.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    db_session = models.InterviewSession(
        candidate_id=session_data.candidate_id,
        role=session_data.role,
        start_time=datetime.utcnow(),
        status="in_progress",
        difficulty=session_data.difficulty,
        question_count=session_data.question_count,
        time_limit=session_data.time_limit,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    rag = RAGEngine(role=session_data.role)
    manager = InterviewManager(
        rag_engine=rag, 
        db=db, 
        base_difficulty=session_data.difficulty, 
        question_count=session_data.question_count
    )
    active_sessions[db_session.id] = (rag, manager, [])

    return SessionResponse(
        id=db_session.id,
        candidate_id=db_session.candidate_id,
        role=db_session.role,
        start_time=db_session.start_time,
        status=db_session.status,
        current_question=1,
        difficulty=db_session.difficulty,
        question_count=db_session.question_count,
        time_limit=db_session.time_limit,
    )


@app.get("/sessions/{session_id}/question", response_model=QuestionResponse)
async def get_question(session_id: int, db: Session = Depends(get_db)):
    db_session = db.query(models.InterviewSession).filter_by(id=session_id).first()
    if not db_session:
        raise HTTPException(404, "Session not found")

    if db_session.status == "completed":
        raise HTTPException(400, "Session already completed")

    if session_id not in active_sessions:
        rag = RAGEngine(role=db_session.role)
        manager = InterviewManager(rag, db)
        active_sessions[session_id] = (rag, manager, [])

    rag, manager, qa_history = active_sessions[session_id]
    candidate = db.query(models.Candidate).filter_by(id=db_session.candidate_id).first()
    question_number = len(qa_history) + 1

    if question_number > 5:
        raise HTTPException(400, "Maximum 5 questions per session")

    question, chunks = await manager.generate_question(
        CandidateCreate(
            name=candidate.name,
            email=candidate.email,
            skills=candidate.skills,
            experience_years=candidate.experience_years,
            education=candidate.education,
        ),
        db_session,
        qa_history,
        question_number,
    )

    db_qa = models.QuestionAnswer(
        session_id=session_id,
        question=question,
        evaluation=json.dumps({"source_chunks": chunks}),
    )
    db.add(db_qa)
    db.commit()
    db.refresh(db_qa)

    # include score=None initially; will be set when answer is submitted
    qa_history.append({"db_id": db_qa.id, "chunks": chunks})

    return QuestionResponse(
        question_number=question_number,
        total_questions=5,
        question_text=question,
        session_id=session_id,
        question_id=db_qa.id,
    )


@app.post("/sessions/{session_id}/answer", response_model=AnswerResponse)
async def submit_answer(
    session_id: int,
    answer_data: AnswerSubmit,
    db: Session = Depends(get_db),
):
    if session_id not in active_sessions:
        raise HTTPException(400, "Session not active or server restarted")

    rag, manager, qa_history = active_sessions[session_id]
    db_qa = db.query(models.QuestionAnswer).filter_by(id=answer_data.question_id).first()
    if not db_qa:
        raise HTTPException(404, "Question not found")
    if db_qa.session_id != session_id:
        raise HTTPException(400, "Question does not belong to this session")
    if db_qa.answer is not None:
        raise HTTPException(400, "Answer already submitted for this question")

    # get the chunks that were used to generate this question
    chunk_info = next(
        (h for h in qa_history if h["db_id"] == answer_data.question_id), None
    )
    chunks = chunk_info["chunks"] if chunk_info else []

    evaluation = await manager.evaluate_answer(
        db_qa.question, answer_data.answer_text, chunks
    )
    score = evaluation.get("score", 50.0)

    db_qa.answer = answer_data.answer_text
    db_qa.score = score
    db_qa.evaluation = evaluation.get("feedback", "")
    db.commit()

    # update qa_history with score for difficulty adaptation
    if chunk_info is not None:
        chunk_info["score"] = score

    db_session = db.query(models.InterviewSession).filter_by(id=session_id).first()
    is_last = len(qa_history) >= db_session.question_count

    result = AnswerResponse(
        question_id=db_qa.id,
        question_text=db_qa.question,
        answer_text=answer_data.answer_text,
        score=score,
        feedback=evaluation.get("feedback", ""),
        is_last=is_last,
        source_chunks=[c.get("source", "") for c in chunks],
    )

    if is_last:
        db_session.end_time = datetime.utcnow()
        db_session.status = "completed"
        all_qa = db.query(models.QuestionAnswer).filter_by(session_id=session_id).all()
        scores = [qa.score for qa in all_qa if qa.score is not None]
        db_session.overall_score = sum(scores) / len(scores) if scores else 0
        db.commit()
        active_sessions.pop(session_id, None)

    return result


@app.get("/sessions/{session_id}/summary", response_model=SessionSummary)
async def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    db_session = db.query(models.InterviewSession).filter_by(id=session_id).first()
    if not db_session:
        raise HTTPException(404, "Session not found")

    candidate = db.query(models.Candidate).filter_by(id=db_session.candidate_id).first()
    qas = db.query(models.QuestionAnswer).filter_by(session_id=session_id).all()

    questions = []
    for qa in qas:
        source_chunks = []
        try:
            chunk_info = json.loads(qa.evaluation or "{}")
            if isinstance(chunk_info, dict):
                raw_chunks = chunk_info.get("source_chunks", [])
                source_chunks = [c.get("text", str(c)) if isinstance(c, dict) else str(c) for c in raw_chunks]
        except (json.JSONDecodeError, TypeError):
            pass
        questions.append(
            QARecord(
                question=qa.question or "",
                answer=qa.answer or "",
                score=qa.score or 0,
                evaluation=qa.evaluation or "",
                source_chunks=source_chunks,
            )
        )

    rag = RAGEngine(role=db_session.role)
    transcript = ""
    for idx, q in enumerate(questions, 1):
        transcript += f"Q{idx}: {q.question}\nA: {q.answer}\nScore: {q.score}/100\n\n"

    insights_prompt = (
        f"Analyze this {db_session.role} interview for {candidate.name}.\n"
        f"Overall score: {db_session.overall_score}/100.\n"
        f"Interview Transcript:\n{transcript}\n"
        f"Based on the transcript above, provide 2-3 brief insights about the candidate's strengths "
        f"and areas for improvement."
    )
    insights = await rag.generate_answer(insights_prompt, None)

    import re
    insights = re.sub(r'\n(?=\*\*Strengths)', '\n\n', insights)
    insights = re.sub(r'\n(?=\*\*Areas for Improvement)', '\n\n', insights)
    insights = re.sub(r'\n(?=\d+\. )', '\n\n', insights)

    return SessionSummary(
        session_id=session_id,
        candidate_name=candidate.name,
        role=db_session.role,
        overall_score=db_session.overall_score or 0,
        status=db_session.status,
        total_questions=len(qas),
        questions=questions,
        insights=insights,
        completed_at=db_session.end_time or datetime.utcnow(),
    )
